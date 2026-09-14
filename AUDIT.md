# AUDIT — CLIbaa Scrapers → Clipbaa Scrapers (Enterprise Port)

**Repo:** `desukab/clipbaa-scrapers` (public, `main`)
**Audited commit(s):** `70eb4d9` (initial port), `c60f9306` (amazon live NameError fix — verified on GitHub main)
**Audit scope:** full source tree (`scrapers/*`, `scrapers/sources/*`,
`scrapers/matching/*`, `scrapers/reporting/*`), tests (`tests/unit/*`, 88 passing),
README/Makefile/pyproject/.env.example/.gitignore/.devcontainer.
**Method:** read-only inspection; no production behavior modified for this audit
(except the already-pushed amazon import fix, which was required before the live
run could work at all).

---

## A. Current Architecture

Single Python package `scrapers/` (repo root), glibc/Codespaces-first, Termux-offline-safe.

```
scrapers/
  cli.py            — argparse entry: run / match / history / export /
                      list-sources / validate-config / scrape-asins
  config.py         — Settings dataclass, validated from env/.env (frozen)
  errors.py         — ConfigError / DependencyError / PipelineError / SourceError / BlockedDetected
  metrics.py        — RunMetrics + per-source counters
  schemas.py        — normalize_record / validate_record (title, id, price gates)
  parsing_utils.py  — first_text/full_text/has_any_text/count_matches/full_items/text helpers
  registry.py       — SourceSpec registry: name, live_capable, mock_items, spider_cls, output_file
  io.py             — atomic_write_json/text, load_json, manifest, run_id
  logging_setup.py  — setup_logging, add_file_handler, JSON/console formatters
  sources/
    __init__.py     — imports submodules so built-in sources self-register
    base.py         — MarketplaceSpider + scrapling guarded fetchers
                      (AsyncStealthySession/AsyncDynamicSession/FetcherSession),
                      SPIDERS_OK flag, run_spider/run_matching/write_items helpers
    amazon.py       — AmazonMoversSpider + AmazonMoversSeedSpider (stealth)
    flipkart.py     — FlipkartBestsellersSpider (stealth)
    meesho.py       — MeeshoTrendingSpider (real-browser dynamic)
    deodap.py       — DeoDap catalog crawl + white-label eligibility (plain fetcher)
  matching/
    matcher.py      — DeodapMatcher, MatchRecord/MatchSummary, near-misses,
                      filter_winners with min margin/ticket/seller caps
    scoring.py      — margin/ROI math (referral+closing+shipping+GST), similarity
                      (jaccard 60% + SequenceMatcher 40%), competition_score,
                      velocity_score, opportunity_score, NOISE_PATTERNS, utility_bonus
    history.py      — price-history append + velocity/alerts
  reporting/
    writer.py       — winners.md, matched_products.csv/json, near_misses.json, atomic writes
    sheets.py       — optional Google Sheets export (service account)
    webhook.py      — HMAC-SHA256 signed POST payload
  daily.py         — scheduled orchestration wrapper (run/export history)
tests/unit/*       — 88 offline-safe pytest cases (mock everywhere)
```

Design decisions already present and good:
- **Fetchers are optional and guarded.** `sources/base.py` imports scrapling inside
  `try/except ImportError`; on glibc-less hosts the session classes fall back to
  `Any` and `SPIDERS_OK=False`, so mock mode + the whole test suite run offline.
  Live requires `pip install -e '.[fetchers]'` + `scrapling install`; the CLI exits
  with a clear `DependencyError` (code 4) rather than silently faking data.
- **Mock-fallback is never silent.** `SCRAPLING_ALLOW_MOCK_FALLBACK` defaults off;
  `--live` without fetchers and without `--allow-mock-fallback` fails loudly. Mock
  is an explicit `--mock` mode, and `make mock` is a first-class e2e demo path.
- **Atomic writes everywhere** (temp+rename+fsync), per-run manifest, run_id logs.
- **One record schema** validated at ingest and re-validated per source.

## B. Current Data Flow

```
live mode:  spider.configure_sessions() --scrapling--> spider.start()
            real HTTP fetches (stealth/dynamic/fetcher per marketplace)
mock mode:  spec.mock_items (bundled sample data)
                  |
                  v
            raw items (per-source JSON: *_raw.json)
                  |  _validate_and_count: validate_record
                  |  + dedupe (prefer "full" quality)          [invalid dropped w/ warning]
                  v
        marketplace products list (all sources merged)
                  |  DeodapMatcher (title similarity + margin eligibility)
                  v
   match candidates  --(min absolute margin / margin% / ticket / sellers / FBA caps)-->
   winners  +  near_misses  +  opportunity_score  +  net_margin/ROI
                  |
                  v
   reporting/writer → winners.md, matched_products.csv/json, near_misses.json
   (optional: Google Sheets, signed webhook)
                  |
                  v
   matching/history → append history rows → velocity + alerts
                  |
                  v
   summary + metrics + manifest (JSON), summary table → stdout
```

Exit codes: `0` mock ok · pipeline error `2` · live-without-fetchers `4`
(DependencyError) · source failure with mock fallback also reported as ok/failed.

## C. Current Strengths

1. **Whole pipeline works offline and is testable without scrapling** — huge for
   CI and for the Codespaces mock path.
2. **Correct anti-silence stance**: explicit mock vs live, no fabricated success.
3. **Regis-tried source spec abstraction** (`SourceSpec` / `registry.list_sources`)
   makes adding Flipkart/Meesho/DeoDap mechanical; each source declares its own
   mock items, output file, and session wiring.
4. **Margin model already reflects marketplace economics** (referral %, closing
   fee, weight-tier shipping, 18% GST on fees, landed-cost GST on DeoDap cost) —
   not a naive price−cost diff.
5. **Normalization + validation + dedupe at ingest** with deterministic drop
   reasons and counts.
6. **History engine** (velocity + alerts) and a separate `make history` path.
7. **Clean playbook**: Makefile targets (mock/live/match/history/export/
   validate/lint/test/install-fetchers), `.env.example` documented, `.gitignore`
   excludes `data/`, `.env`, caches.
8. **88 passing unit tests** covering matcher, scoring, sources (mock), sheets,
   webhook, writer, schemas, metrics, config, parsing_utils, history.

## D. Critical Bugs

1. **[FIXED & pushed — c60f9306]** `scrapers/sources/amazon.py:342` called
   `AsyncStealthySession(...)` without importing it from `base.py`; in live mode
   (Codespaces, scrapling present) this raised
   `NameError: name 'AsyncStealthySession' is not defined`, which scrapling's
   `Spider.__init__` wrapped as a confusing `SessionConfigurationError`. Fixed by
   importing the class from `scrapers.sources.base`. Fliipkart/Meesho/DeoDap
   already imported their sessions from base.
   **Action for the book:** the Codespace must `git pull origin main` (or re-open)
   before `make live`; no other code change was needed.
2. No other confirmed critical (crash-on-happy-path) bug found in the audited tree.

## E. High-Priority Bugs / Risks

1. **Live failure masking:** any error inside `configure_sessions` surfaces as
   scrapling's `SessionConfigurationError`, hiding the real `NameError`/DNS/stealth
   problem. Wrap session construction so failures raise our own, actionable
   `DependencyError`/`SourceError` with the underlying cause. (See P.)
2. **Browser/session lifecycle:** `run_spider` relies on scrapling's default
   teardown; there is no explicit `finally`-style guard in our `_crawl_source` for
   browser/context/page cleanup on exception paths. Add a context-manager wrapper +
   a test that asserts no leaked resources (see P / section on resource mgmt).
3. **No retries/backoff on transient fetch failures** beyond scrapling's internal
   defaults; if live Amazon/Flipkart throttles, we currently only report
   `status=failed` and (optionally) fall back to mock. No exponential backoff,
   jitter, or per-source max-retry policy in our layer.
4. **Matching is title-similarity-only.** No product id / SKU / brand / model /
   dimensions identity, no staged matching, no pack-size conflict detection
   (e.g. 3-piece vs 5-piece rack). This is the single biggest correctness risk for
   output quality. (See K.)
5. **Margins lack a configurable cost stack** — packaging, returns reserve,
   advertising, payment-collection, tax-on-tax, category-specific fees are not
   modeled; ROI and "break-even price" not exposed. (See L.)

## F. Medium-Priority Improvements

1. Add structured `RetryConfig` (max retries, backoff base, jitter, per-source).
2. Add per-source failure classification (`rate_limited`, `blocked`, `timeout`,
   `parse_error`, `deprecated_selector`) and route to our error taxonomy.
3. Add a data-quality report + quality gate (PASS/DEGRADED) at end of crawl, with
   counts: parsed, valid, dropped, dupes, missing price/seller/weight.
4. Add caching (TTL-aware) of product pages / catalog / history to avoid
   re-fetching identical data.
5. Canonical `Product` / `WholesaleProduct` schema (see s7/s8) so sources converge
   on one shape; the current `dict[str, Any]` flow is workable but undocumented.
6. Structured logging of every significant event (ts, level, source, operation,
   status, duration, item-id) in a consistent JSON envelope.

## G. Low-Priority Improvements

1. Docs: README refers to `scrapers/scrapers/cli.py` nested layout in a couple of
   places vs the actual flat `scrapers/cli.py` — tidy doc paths.
2. `.env.example` section headers are free-form; group env vars by feature for
   readability, and keep `SCRAPLING_*` prefix for adaptive/stealth knobs.
3. `make export` docstring/gate consistency for sheets/webhook error paths.
4. Consider a `--dry-run --validate-config` already there; add `--list-thresholds`
   to print effective matching/economics thresholds.

## H. Security Concerns

1. **Secrets policy looks correct:** `.env` is gitignored; `.env.example` ships
   placeholders only; settings `to_dict(redact=True)` strips webhook_secret/proxy
   creds in manifests. Confirm no accidental committed tokens: repository lazy-check
   of history and `data/`, `.env`, `*.pem`, `service-account.json`, `cookies*`
   patterns in `.gitignore`. (Re-verify after every merge.)
2. **No auth-bearing URLs/cookies** are logged: logging only records source status
   and counts, not headers or item fields with PII. Keep it that way when adding
   structured logging.
3. **Webhook HMAC** is already signed (HMAC-SHA256 + secret) — good. Ensure the
   secret lives in `.env`, never in code or files.
4. When we add Google Sheets auth, only `SHEETS_SERVICE_ACCOUNT` path should be
   read from env; never embed the JSON or its private key in the repo (incl. keys
   in `data/`, which is gitignored).

## I. Scalability Concerns

1. Fixed concurrency (`concurrent_requests=5`, FBA caps) — fine for single-host
   research runs; no distributed worker, queue, or progress checkpoint.
2. `max_products` caps per source prevent unbounded crawls; good.
3. History file grows unboundedly per run (append-only lines). Add history pruning
   / TTL (e.g. keep 90–365 days) to bound memory and file size.
4. Sheets/webhook exports are synchronous single-shot; for large winner sets add
   chunking/timeouts as they scale.

## J. Data-Quality Concerns

1. Ingest validation drops records without `title`/`url`/price and without
   marketplace id — good — **but** non-numeric/missing numeric fields silently
   coerce to 0.0. This can create phantom zero-price winners unless the matcher
   re-checks price>0 (it does: `to_float(mp.get("current_price"))`, skips `<=0`;
   `eligible_deodap` checks cost>0 && stock>=20). Keep those gates; add an explicit
   `price_is_zero` → drop reason.
2. Marketplace title noise is filtered by `is_noise`/`NOISE_PATTERNS`
   (toys/party/costume/stationery) and boosted by `utility_bonus` kitchenthese;
   this is heuristic — document and keep configurable.
3. Demand signals (BSR, movers rank, review count) are *inferred* from observable
   marketplace data, never unit sales — should be labeled `demand_signal`, not
   "units sold", and confidence tracked.

## K. Matching Weaknesses

1. Single lexical similarity (jaccard 60% / SequenceMatcher 40%) across the whole
   DeoDap catalog for every marketplace product — O(N*M), no index, no staged
   narrowing, and no **why-it-matched** evidence breakdown.
2. No product identity fields: brand, model number, dimensions, weight, color,
   material, pack size, SKU are not used in matching. "3-piece" vs "5-piece" can
   collapse to one winner (pack-size conflict unsolved).
3. Confidence threshold single scalar; near-miss floor single constant
   (`NEAR_MISS_FLOOR=0.35`); no match reason/evidence object on the record.
4. No explicit REJECT tier (e.g. low confidence due to missing identity data)
   beyond the near-miss bucket.

## L. Profitability-Model Weaknesses

1. Fee stack is partial: referral%, closing fee (flat by bucket), weight-tier
   shipping, 18% GST on (closing+shipping). Missing: packaging, returns reserve,
   advertising, payment-collection, tax-on-tax nuances, category/fulfillment-model
   (FBA vs FBM) fee differences beyond the FBA-seller cap filter.
2. No **break-even price** output; net margin and ROI are computed (see
   `scoring.calculate_margin`), but the report doesn't say "sell at ₹X to cover
   costs".
3. Thresholds (min_absolute_margin 200, min_margin_pct 35, min_ticket 300,
   max_sellers 5, max_fba_sellers 2) are env-tunable but not exposed as a
   documented cost model; assumptions (returns %, ad %, packing %) are implicit.
4. ROI uses landed cost as base but isn't documented as `(net_margin / landed)`
   with explicit definition in docs — add a formula reference.

## M. Demand-Model Weaknesses

1. Demand is *approximated* by movers rank (amazon movers-and-shakers), review
   count, BSR avg/current, and velocity from history. That's a defensible OBSERVED
   proxy but must be labeled `demand_signal` (score + confidence), not unit sales.
2. No demand *velocity* over time except BSR history (velocity score in
   `scoring`); no review-velocity or star-ratio trend.
3. `bsr_30d_avg` is *derived* as `bsr_current*2` when absent — synthetic fallback
   that can mislead; prefer `INSUFFICIENT_DATA` instead of fabricating an average.

## N. Testing Weaknesses

1. Excellent offline coverage of matcher/scoring/sources/reporting (88 tests),
   mock-safe by design.
2. **No live/integration test** (couldn't be run in Termux; CodeSpaces-only). Add a
   `LIVE_OK`-gated integration test that runs one small amazon crawl when
   scrapling+fetchers installed, asserting a valid raw item or an explicit
   blocked/failed status (never silent mock).
3. No property/fuzz tests for title similarity, no golden-file tests for report
   formatting (winners.md/CSV/JSON), no test bus for near-miss threshold routing,
   no test for the new session-import fix (guarded path only tests fallback=Any).
4. No concurrency/resource-leak tests (browser leak detection).

## O. Deployment Weaknesses

1. Devcontainer `.devcontainer/devcontainer.json` installs fetchers + scrapling —
   good for Codespaces. No GitHub Actions CI (lint+tests+optional live gate) yet.
2. `Makefile` requires `scrapling install` for live; docs should call the
   `make install-fetchers` precondition loudly (README already does).
3. Termux (no glibc/python-wheels) can only run `make mock` offline — documented;
   live runs are Codespaces/Ubuntu-only by design. Ensure `.env.example` notes this.
4. Secrets wiring for sheets/webhook documented in `.env.example`; add a
   `make validate-config` smoke after env changes (exists).

## P. Recommended Target Architecture

Adopt a layered pipeline (keeps all current modules; adds explicit boundaries):

```
SOURCE LAYER       scrapers/sources/*    [done]
                      \
FETCHER LAYER      scrapers/sources/base (session mgr) -> owns stealth/dynamic/fetcher,
                      Proxy/ProxyURL, bounded concurrency, retries/backoff   [harden]
FETCHER -> PARSER  scrapers/parsing_utils: raw->field extraction                [strengthen]
NORMALIZATION      scrapers/schemas canonical Product/WholesaleProduct + per-source mapping
PRODUCT IDENTITY   NEW scrapers/identity.py: fingerprint (brand,model,sku,GTIN,pack,dims)
MATCHING ENGINE    staged: exact id -> strong attrs -> title sim -> fuzzy -> evidence     [K]
ECONOMICS ENGINE   NEW scrapers/economics.py: full fee stack + break-even + assumptions
DEMAND SIGNAL      velocity over history + review/velocity + OBSERVED vs INFERRED label
COMPETITION ENGINE  seller/FBA-review/rating concentration -> LOW/MED/HIGH/EXTREME
RISK ENGINE         match volatility, source reliability, return/margin risk -> risk_score
OPPORTUNITY SCORE  component-weighted, explainable, configurable         [scoring.grow]
DATA QUALITY GATE  stats + PASS/DEGRADED, gate publishing                 [NEW]
PERSISTENCE/HISORY history TTL + pruning; manifests; alerts
REPORTING          wins returns + risk + quality + confidence; sheets/webhook/dashboard
```

Prioritized implementation waves (each independently shippable):
1. **Wave A — Live hardening** (unblocks `make live` reliably end-to-end): session
   construction via our helpers raising `DependencyError`/`SourceError`, explicit
   teardown context manager, `RetryConfig` with backoff, per-source failure
   classification. Tests: guarded-path + mock + one live gate.
2. **Wave B — Data-quality gate + canonical schemas** (Product identity marks,
   quality report, PASS/DEGRADED gate).
3. **Wave C — Matching upgrade** (staged matcher, why-matched evidence, pack-size
   conflict detection, confidence tiers incl. REJECT).
4. **Wave D — Economics engine** (full configurable fee stack, break-even, ROI
   formula docs, assumption inventory).
5. **Wave E — Demand/Competition/Risk** (explicit signal engines with
   INSUFFICIENT_DATA instead of fabrications).
6. **Wave F — Engineering**: structured logging envelope, caching, history TTL,
   sheets chunking, CI (Actions: lint + tests). 

---

## Immediate actions taken
- Verified GitHub `main` HEAD = `c60f9306` and `amazon.py:8` now imports
  `AsyncStealthySession` (fix pushed). Codespace needs only `git pull origin main`.
- This audit (read-only) produced no other code change.

## Suggested next step
Ask the maintainer: start **Wave A** (live hardening) since it is the smallest
reliable step that makes `make live` trustworthy, then B → C in order of
opportunity-quality impact.
