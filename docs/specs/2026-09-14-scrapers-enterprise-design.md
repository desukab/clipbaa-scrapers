# Scrapers Enterprise Hardening — Design

Date: 2026-09-14
Status: Draft (pending user review)
Approach: B — Layered reorg + source registry (user-approved, trimmed to existing 4 sources)

## Overview

Reorganize the `scrapers/` module from a flat, tightly-coupled set of scripts into a
layered, testable, configurable, observable pipeline. Scope is limited to the existing
four marketplaces plus the opportunity matcher. The source registry is designed so new
sources can be added later as one module + registration, but no new marketplaces are
implemented in this pass.

Rationale for the split: this development environment is Termux/aarch64 where PyPI
wheels for C/Rust dependencies do not exist, so `scrapling[fetchers]` cannot be
installed here (verified: `orjson`, a required dep, timed out building from source).
Therefore:

- **Core runtime**: pure-Python; runs on any Python >= 3.10 host, including this one.
- **Live-session layer**: optional `scrapling[fetchers]` extra, imported lazily only
  when a live crawl is requested. Runs on a standard Linux/macOS host.
- No silent mock fallback: live mode failures are reported loudly and, only when
  `--allow-mock-fallback` is set, sources degrade to bundled sample data with explicit
  labeling in logs/manifest.

## Goals (non-negotiable)

1. **Reliability & observability**: structured logging, per-source metrics, typed
   errors, run manifests, meaningful exit codes.
2. **Config & ops**: central validated `Settings` from env/`.env`, clean CLI, CI-friendly.
3. **Data quality**: one normalized, validated product record; atomic writes;
   schema-version stamped outputs; tolerant loaders.
4. **Testing**: pytest suite covering parsers, scoring, matcher, config, IO, CLI.
5. **Packaging**: `pyproject.toml`, console entry point, extras (`fetchers`, `sheets`,
   `dev`).
6. **Security & politeness**: no secrets in code or logs (proxy creds redacted),
   throttling/proxy config, per-domain delays preserved.

## Package layout

```
scrapers/
  pyproject.toml
  requirements.txt            # thin pointer to pyproject extras
  scrapers/
    __init__.py
    cli.py                    # argparse subcommands; conftest import-safe
    config.py                 # validated Settings (env/.env via python-dotenv)
    logging_setup.py          # structured logging (JSON/console), redaction
    metrics.py                # RunMetrics counters + timings per source
    errors.py                 # typed exceptions + classification
    io.py                     # atomic JSON write, safe paths, run manifest
    registry.py               # source registry (import-time registration)
    matching/
      __init__.py
      matcher.py              # pure matching/scoring (no IO/printing)
      scoring.py              # margin calc, opportunity score, filters/noise
      history.py              # price-history JSONL + velocity + alerts
    sources/
      __init__.py             # registers built-in sources
      base.py                 # MarketplaceSpider base (moved from base.py)
      amazon.py               # amazon_movers_spider equivalent (+ seed-ASIN mode)
      meesho.py
      flipkart.py
      deodap.py
      mocks.py                # bundled sample catalogs (existing MOCK_* data)
    reporting/
      __init__.py
      writer.py               # JSON/CSV/Markdown (stdlib csv; pandas dropped)
      sheets.py               # OPTIONAL gspread export (extras[sheets])
      webhook.py              # OPTIONAL HMAC-signed summary POST (extras[webhook])
  tests/
    conftest.py
    fixtures/                 # static HTML/JSON per source + mock catalog JSON
    unit/                     # test_*.py per module (see Testing)
```

## Config (`config.py`)

- `Settings` dataclass; populated from environment, then `.env` file if present
  (python-dotenv). Path to env file overridable via env/CLI flag.
- Validation performed at load; invalid values fail fast with the offending field
  named. Examples: proxy URL parse, boolean parsing, integer ranges, threshold ranges
  (0..1 confidence, margins >= 0).
- Env vars supported (existing preserved):
  - `SCRAPLING_ADAPTIVE`, `SCRAPLING_ADAPTIVE_PERCENTAGE`, `SCRAPLING_CRAWL_DIR`,
    `SCRAPLING_PROXY`
  - `AMAZON_MOVERS_URL`, `AMAZON_BESTSELLERS_URLS`, `AMAZON_NODE_CATEGORIES`
  - `MEESHO_TRENDING_URL`
  - `FLIPKART_BESTSELLERS_URL`
  - `DEODAP_BASE_URL`, `DEODAP_CATEGORIES`, `DEODAP_MAX_PAGES`
  - New: `LOG_LEVEL`, `LOG_FORMAT` (json|console), `OUTPUT_DIR`,
    `SCRAPLING_ALLOW_MOCK_FALLBACK`, `HISTORY_DIR`, `MIN_*` matcher thresholds,
    `SHEETS_SERVICE_ACCOUNT`, `SHEETS_SPREADSHEET_ID`, `WEBHOOK_URL`, `WEBHOOK_SECRET`.
- `Settings` is immutable after construction; spiders receive only the values they need
  via constructor kwargs (`max_products`, URLs, categories, adaptive flags).

## Logging (`logging_setup.py`)

- stdlib `logging`, no framework dependency.
- `setup_logging(settings)` configures root logger with a structured formatter.
  `LOG_FORMAT=json` emits single-line JSON (`ts, level, logger, message,
  source?, asin/pid?, duration_ms?`); `console` emits aligned human-readable lines.
- Proxy credentials are never logged: proxy is parsed and only the host/port scheme are
  printed.
- Per-run log file written under `OUTPUT_DIR/runs/<run_id>/run.log`.

## Metrics & run manifest (`metrics.py`, `io.py`)

- `RunMetrics` per source: `requested`, `scraped`, `enriched`, `blocked`, `retried`,
  `failed`, `deduped_added`, `elapsed_ms`. Global counters and elapsed total.
- On completion, a manifest is written:
  `OUTPUT_DIR/runs/<run_id>/manifest.json` containing: timestamp, run id, mode
  (live/mock), per-source sections (status: ok/failed/blocked/mock-fallback, counts,
  elapsed), matcher summary (candidates, winners, near-misses, opportunity >=65 count),
  export statuses, git commit (if available and requested), and the resolved
  settings minus secrets.
- Exit codes: `0` clean success (including explicit `--mock` runs); `1` live run where
  one or more sources failed and/or propagated to mock fallback; `2` configuration or
  startup error; `3` all sources failed in a live run; `4` missing optional dependency
  when a live run is requested (e.g., scrapling not installed).

## Errors (`errors.py`)

- `PipelineError(Exception)` base; subclasses: `ConfigError`, `SourceError` (carries
  source name), `BlockedDetected`, `ParseError` (carries url/asin), `ExportError`.
- A crawler adapter converts spider/parse exceptions + blocked detection into typed
  errors and records them in metrics; never crashes the whole run for one source.

## Normalized schema & validation

- `ProductRecord`: one normalized dict schema for all sources. Fields (all existing
  keys preserved as-is): `source`, `quality` ("card"|"full"), marketplace id
  (`asin`|`product_id`|`sku`), `title`, `category`, `current_price`, `mrp`,
  `discount_pct`, `rating`, `review_count`, `seller_count`, `fba_seller_count`,
  `weight_g`, `dimensions_cm`, `images_count`, `has_video`, `amazon_choice`,
  `best_seller_badge`, `product_url`, plus source-specific extras in `extra` dict.
- `validate_record(record) -> list[str]`: returns validation errors; ride-or-die on
  required fields (`title`, `current_price`, marketplace id, `url`); coerces/normalizes
  types (int/float/None). Pure stdlib validators (no msgspec — no wheel on target ABI).
- `MatchRecord` retains the current `MatchedProduct` field set so CSV/JSON consumers
  are unchanged.

## Sources (`sources/`)

- `MarketplaceSpider` base moved to `sources/base.py` (from `base.py`), preserving
  AutoThrottle, adaptive flags, blocked detection, retry, dedupe, `run_spider`,
  `write_items`, `load_items`, `ensure_output_paths`.
- `registry.py`: `register_source(name, spec)` + `get_source(name)`; spec carries the
  spider class, bundled mock items, default max_products, and output filename.
  `sources/__init__.py` imports each marketplace module to trigger registration.
- Each marketplace module preserves its existing parsing logic verbatim (raw behavior
  is trusted and already live-tested); only exports/entry-points change.
- Amazon: movers + bestsellers category list made config-driven
  (`AMAZON_BESTSELLERS_URLS` existed; add `AMAZON_NODE_CATEGORIES` override), seed-ASIN
  mode retained.
- DeoDap: `DEODAP_MAX_PAGES` already env-driven; default category list retained.
- Bundled mock catalogs moved to `sources/mocks.py` unchanged in value.

## Matching (`matching/`)

- Matcher split: `scoring.py` = `_calculate_margin`, opportunity score, competition
  tiers, velocity, ROI, eligibility, noise/utility filters (pure functions, no IO).
- `matcher.py` = pipeline: load catalog, load marketplace products, run match, produce
  `MatchRecord`s + near-misses; thresholds from `Settings` (defaults = current
  constants, preserving current behavior).
- No printing inside; diagnostics returned as a summary object the CLI/report layer prints.

## Analysis: price history (`matching/history.py`)

- Append-only JSONL store at `OUTPUT_DIR/history/products.jsonl`: one line per
  (source, marketplace id, crawled_at, price, rating, review_count, stock for
  DeoDap). Filename under `HISTORY_DIR` override.
- `compute_velocity(product, lookback_days=14)`: % price change over window → stored
  per run.
- Alerts surfaced to report/manifest: `price_dropped_pct`, `restocked` (DeoDap stock
  rose above threshold), `price_spike`. Best-effort, non-fatal on history corruption.

## Reporting (`reporting/`)

- `writer.py`:
  - `matched_products.json` + `matched_products.csv` (same columns as today, written
    with stdlib `csv` — pandas removed), in `OUTPUT_DIR`.
  - `winners.md`: human-readable ranked report (rank, title, sku, cost→price,
    margin ₹/%, confidence, opportunity, velocity, alerts, top-N configurable).
  - near-misses to `near_matches.json` (as today).
- `sheets.py` (optional): push winners to a Google Sheet using `extras[sheets]`
  (`gspread`); enabled only if service-account + spreadsheet id configured AND sheet
  export requested.
- `webhook.py` (optional): POST summary manifest subset to `WEBHOOK_URL`, HMAC-SHA256
  signed with `WEBHOOK_SECRET` (`X-Pipeline-Signature` header); payload contains counts
  and top winners, never secrets or env. Disabled by default.

## CLI (`cli.py`)

Subcommands (all readable, all non-interactive, CI-friendly):

- `pipeline run [--live|--mock] [--sources a,b] [--max-products N] [--allow-mock-fallback]`
- `pipeline match [threshold overrides]`
- `pipeline history [--product ID] [--alerts]`
- `pipeline export [--sheets] [--webhook] [--report]`
- `pipeline list-sources`
- `pipeline validate-config`

Entry point: console script `pipeline` and `python -m scrapers.cli`.

## Packaging (`pyproject.toml`)

- setuptools; name `scrapers`, version `1.0.0`, `requires-python = ">=3.10"`.
- Runtime deps: `python-dotenv>=1.0`. (lxml/cssselect already runtime deps of scrapling;
  only needed for live parsing.)
- Extras:
  - `fetchers`: `scrapling[fetchers]>=0.4.15`
  - `sheets`: `gspread>=6` (for Google Sheets export)
  - `dev`: `pytest>=8`, `flake8>=7`
- `requirements.txt` kept as a thin convenience file installing
  `.[all]`-style deps for the README quickstart.
- `[project.scripts] pipeline = "scrapers.cli:main"`.

## Testing (pytest)

- `tests/fixtures/`: static HTML fragments per marketplace parser (Amazon card +
  product, Meesho, Flipkart, DeoDap Shopify JSON) and golden mock catalogs.
- Unit tests:
  - parsing utils (price/int/rating/weight/dimensions/bsr/id extraction), known-value
    inputs.
  - each marketplace parser mapping (golden JSON in → expected fields out).
  - scoring: known-value margin table (fee tiers, GST, shipping), opportunity tiers.
  - matcher: mock catalog → expected winners/near-misses; dedupe behavior.
  - config validation (valid + each invalid case fails fast).
  - history: append + velocity + alerts; corruption tolerated.
  - io: atomic writes (no partial file on failure), safe-path rejections.
  - cli: list-sources, validate-config, run --mock exit codes.
- External-only behaviors (browser sessions, live parsers) are tested via the spider
  parse methods with canned `Response`-like DOM objects where feasible; live network
  paths are marked `@pytest.mark.live` and skipped by default.

## Run & deliverables

- In this environment: `pip install -e .[dev]` (core is pure-Python), run pytest,
  then `pipeline run --mock` for all 4 sources → `pipeline match`
  → `pipeline export --report` → `pipeline history --alerts`.
- Deliverables handed to the user: ranked winners list (title, sku, cost→price, margin,
  confidence, opportunity) printed in chat + file paths for
  `matched_products.json/.csv`, `winners.md`, `near_matches.json`, run manifests.
- Live commands for a real Linux/macOS host documented in README:
  `pip install -e ".[fetchers]" && scrapling install && pipeline run --live`.

## Deferred (explicitly out of scope)

- New marketplace sources (Snapdeal/JioMart) — registry ready for future addition.
- Pydantic/msgspec schemas (no wheel on target ABI) — stdlib validators instead.
- Event-driven queue / database persistence.
- Live-scrape verification in this environment (impossible on Termux; see rationale).