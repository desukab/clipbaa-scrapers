# Clipbaa Scrapers — Market Research Pipeline

Enterprise e-commerce **opportunity research** across **Amazon.in**, **Meesho**,
**Flipkart**, and **DeoDap** (wholesale). It crawls each marketplace with
anti-bot-aware fetchers, cross-references marketplace offers against DeoDap
wholesale pricing, and ranks the products worth relisting — by absolute margin,
margin %, competition, and sales velocity.

Built to run **inside GitHub Codespaces** (glibc + Rust wheels available), so
the full live scraping stack — `scrapling[fetchers]` adaptive mode, Playwright,
Camoufox, stealth sessions — works out of the box. It also runs in pure mock
mode on any machine (including Termux) with no heavy dependencies.

---

## What it does

1. **Scrape** four marketplaces:
   - [`Amazon.in`](scrapers/scrapers/sources/amazon.py) — Movers & Shakers +
     Bestsellers (stealth `AsyncStealthySession`, adaptive selectors)
   - [`Meesho`](scrapers/scrapers/sources/meesho.py) — Trending (dynamic,
     real-browser `AsyncDynamicSession`)
   - [`Flipkart`](scrapers/scrapers/sources/flipkart.py) — Bestsellers (stealth)
   - [`DeoDap`](scrapers/scrapers/sources/deodap.py) — wholesale catalog /
     collection crawler (fast TLS fetcher)
2. **Normalize & validate** every record against per-source schemas.
3. **Match** marketplace items to DeoDap SKUs (title sim + category + fuzzy ID),
   then verify they clear **all** threshold rules (ticket price, absolute margin,
   margin %, seller/`FBA`-seller counts) with a confidence score.
4. **Correct for competition/velocity** via an opportunity-opportunity score and
   price-history velocity + alerts (price drops, restocks).
5. **Report** — ranked `winners.md`, `matched_products.csv/json`, `near_matches.json`,
   HMAC-signed webhook, and optional Google Sheets export.

Mock data is cross-consistent across sources (same product themes, distinct
IDs), so `--mock` exercises the full matcher end-to-end offline.

---

## Quick start (Codespaces)

Just create/launch a Codespace from this repo. The devcontainer:

- installs `pip install -e '.[dev,fetchers]'` (Rust wheels available on the
  Ubuntu image — no local compilation pain),
- runs `scrapling install` (Playwright/Camoufox browser binaries).

Then in the integrated terminal:

```bash
# 0) CONFIG — copy the template and edit (see .env.example for every variable)
cp .env.example .env

# 1) Self-check the installation + all CLI subcommands work
make validate && make list

# 2) Offline end-to-end test against cross-consistent sample data
make mock            # -> data/winners.md, data/matched_products.csv, ...
make history         # velocity + price-drop / restock alerts
make export          # regenerate reports from the last matched run

# 3) Live scrape (fetchers installed — real fetches over the network)
make live            # or: pipeline --live run --sources amazon,meesho

# 4) Tests
make test            # or: python -m pytest tests -q
```

> **Before the first live run** review `docs/plans`. Keep secrets in `.env`
> (gitignored) — the `.env.example` template documents every variable. Prefer
> `--mock` for CI/demos; a failed live crawl is reported, never silent-mocked.

---

## CLI reference

```text
pipeline [--env-file .env] [--output-dir data] <command>

run             Scrape → match → report (full pipeline)
                --live | --mock        fetch mode (default: mock)
                --sources a,b,c        subset of amazon,meesho,flipkart,deodap
                --max-products N       cap per source
                --allow-mock-fallback  permit mock data when a source fails
match           Re-run matching against already-collected raw data
history         Show match history, velocity, and price/restock alerts
list-sources    Show registered sources and their mock/live providers
validate-config Validate settings and exit
export          Write reports; --sheets (Google Sheets) or --webhook
scrape-asins    Fetch specific Amazon product pages
```

Exit codes: `0` ok · `2` bad config/usage · `4` live mode without `fetchers`/
`mock-fallback` not allowed · other non-zero = source/pipeline failure.

---

## Repository layout

```text
scrapers/          Python package (sources, matching, reporting, cli, config)
tests/             pytest suite (offline-safe, 88 tests)
docs/plans/        planning docs (decision log, structure, risks)
docs/specs/        design spec (Approach B, adaptive-selector loop)
Makefile           convenience targets (make mock/live/test/...)
.pyenv             — (not present; use the devcontainer Python)
.env.example       documented copy of every env var
```

---

## Configuration

See [`.env.example`](.env.example) — every variable the pipeline reads, with
defaults already baked into `scrapers/scrapers/config.py`. Core knobs:

| Env var | Default | Purpose |
|---------|---------|---------|
| `MIN_TICKET_PRICE` | 300 | skip low-ticket items |
| `MIN_ABSOLUTE_MARGIN` | 200 | min INR margin after landing costs |
| `MIN_MARGIN_PCT` | 35 | min % margin |
| `MAX_SELLERS` / `MAX_FBA_SELLERS` | 5 / 2 | competition caps on marketplace |
| `MIN_CONFIDENCE` | 0.5 | min match confidence |
| `REPORT_TOP_N` | 25 | winners shown per report |
| `SCRAPLING_ADAPTIVE=1` | off | auto-relocate DOM fingerprints on redesign |
| `SCRAPLING_ALLOW_MOCK_FALLBACK=0` | off | never silently fake a live crawl |

---

## Tests

```bash
pip install -e '.[dev]'    # if not already installed
python -m pytest tests -q
```
