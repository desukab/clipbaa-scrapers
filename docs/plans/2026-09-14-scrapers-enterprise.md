# Scrapers Enterprise Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the `scrapers/` module into a layered, testable, configurable, observable pipeline (Approach B) with a pure-Python core and an optional live `scrapling[fetchers]` layer, preserving current scraping/matching behavior and producing a ranked products list.

**Architecture:** `core` (config, logging, metrics, io, errors, registry, schemas) + `sources` (4 marketplace modules + base spider, guarded scrapling imports) + `matching` (pure scoring/matcher/history) + `reporting` (json/csv/markdown/sheets/webhook) + a `cli` orchestrator with subcommands, console script `pipeline`, and pytest coverage. Core runtime has zero C/Rust dependencies so it installs and runs on this Termux/aarch64 host; live scraping requires `extras[fetchers]` and runs on a glibc host (e.g. proot-Distro Ubuntu).

**Tech Stack:** Python >=3.10, stdlib `logging`/`csv`/`argparse`/`urllib`, `python-dotenv`, optional `scrapling[fetchers]`, optional `gspread`, `pytest`.

**Spec:** `docs/superpowers/specs/2026-09-14-scrapers-enterprise-design.md`

## Global Constraints

- `requires-python = ">=3.10"`; package name `scrapers`; console entry point `pipeline = "scrapers.cli:main"`.
- Core runtime deps = `python-dotenv>=1.0` only. No C/Rust extension wheels on the core path.
- `scrapling` imported ONLY via guarded/suppressed `try/except ImportError` blocks; never unconditionally at package import time. Optional extras: `fetchers`, `sheets`, `dev`.
- Keep current behaviors verbatim: AutoThrottle, adaptive flags, blocked detection, retries, no silent fabrication. Live-mode mock fallback only when `--allow-mock-fallback` is set, and always labeled in logs + manifest (`mock-fallback` status).
- Preserve all output field names and CSV columns exactly (`amazon_title`, `deodap_sku`, `cost`, `amazon_price`, `absolute_margin_inr`, `margin_percentage`). Replace pandas CSV with stdlib `csv`.
- Bundled mock catalogs keep the exact same values as today (move, don't edit).
- Secrets (proxy credentials, `webhook_secret`) are never written to logs or the manifest.
- Run directories default to the current working directory (`OUTPUT_DIR`, default `data`).
- All tasks end with the touched pytest files passing, then a git commit.

---

### Task 0: Project skeleton + packaging

**Files:**
- Create: `scrapers/pyproject.toml`
- Create: `scrapers/scrapers/__init__.py`, `scrapers/scrapers/cli.py`, `scrapers/scrapers/config.py`, `scrapers/scrapers/logging_setup.py`, `scrapers/scrapers/metrics.py`, `scrapers/scrapers/errors.py`, `scrapers/scrapers/io.py`, `scrapers/scrapers/registry.py`, `scrapers/scrapers/schemas.py` (placeholder until Task 13) and subpackage dirs `scrapers/scrapers/matching/`, `scrapers/scrapers/sources/`, `scrapers/scrapers/reporting/` each with `__init__.py`
- Create: `scrapers/tests/__init__.py`, `scrapers/tests/conftest.py`, `scrapers/tests/test_package.py`
- Rewrite: `scrapers/requirements.txt`
- Delete (content ported in later tasks): `scrapers/pipeline.py`, `scrapers/base.py`, `scrapers/matcher.py`, `scrapers/parsing_utils.py`, `scrapers/amazon_movers_spider.py`, `scrapers/meesho_trending_spider.py`, `scrapers/flipkart_bestsellers_spider.py`, `scrapers/deodap_catalog_spider.py`, `scrapers/scrape_asins.py`, `scrapers/__init__.py`
- Move: `scrapers/seed_asins.json` → `scrapers/scrapers/sources/seed_asins.json`

**Interfaces:**
- Consumes: nothing.
- Produces: installable `scrapers` package importable as `scrapers.<module>`; `pipeline` console script; the new directory layout. Later tasks fill these files in.

- [ ] **Step 1: Create `scrapers/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "scrapers"
version = "1.0.0"
description = "Enterprise e-commerce market research pipeline (Amazon, Meesho, Flipkart, DeoDap)"
requires-python = ">=3.10"
dependencies = ["python-dotenv>=1.0"]

[project.optional-dependencies]
fetchers = ["scrapling[fetchers]>=0.4.15"]
sheets = ["gspread>=6"]
dev = ["pytest>=8", "flake8>=7"]

[project.scripts]
pipeline = "scrapers.cli:main"

[tool.setuptools.packages.find]
include = ["scrapers*"]
```

- [ ] **Step 2: Create the package skeleton**

Create empty init files (`# Scrapers package`) for `scrapers/scrapers/__init__.py`, `scrapers/scrapers/matching/__init__.py`, `scrapers/scrapers/sources/__init__.py`, `scrapers/scrapers/reporting/__init__.py`, `scrapers/tests/__init__.py`. Create a placeholder `scrapers/scrapers/cli.py`:

```python
def main(argv=None) -> int:
    return 0
```

and touch-place `scrapers/scrapers/schemas.py`:

```python
"""Placeholder; implemented in Task 13."""
```

Rewrite `scrapers/requirements.txt` to:

```
# Core runtime (pure Python): install this project instead
#   pip install -e .             (core / mock + matcher + reports)
#   pip install -e ".[fetchers]" (live scraping; needs a glibc host)
#   pip install -e ".[dev]"      (core + test tooling)
```

- [ ] **Step 3: Move seed data and delete old layout**

```bash
mkdir -p scrapers/scrapers/sources scrapers/scrapers/matching scrapers/scrapers/reporting scrapers/tests
git mv scrapers/seed_asins.json scrapers/scrapers/sources/seed_asins.json
git rm scrapers/pipeline.py scrapers/base.py scrapers/matcher.py scrapers/parsing_utils.py \
        scrapers/amazon_movers_spider.py scrapers/meesho_trending_spider.py \
        scrapers/flipkart_bestsellers_spider.py scrapers/deodap_catalog_spider.py \
        scrapers/scrape_asins.py scrapers/__init__.py
```

(Keep `scrapers/README.md`, `scrapers/FIND_ASINS.md`, `scrapers/requirements.txt`.)

- [ ] **Step 4: Write the package smoke test**

Create `scrapers/tests/conftest.py`:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

Create `scrapers/tests/test_package.py`:

```python
def test_package_importable():
    import scrapers
    assert scrapers.__name__ == "scrapers"


def test_cli_placeholder_runs():
    from scrapers.cli import main
    assert main([]) == 0
```

- [ ] **Step 5: Install editable and run the test**

```bash
python3 -m pip install -e "./scrapers[dev]"
python3 -m pytest scrapers/tests/test_package.py -q
pipeline
```

Expected: pytest passes (2 tests); `pipeline` prints nothing and exits 0.

- [ ] **Step 6: Commit**

```bash
git add scrapers
git commit -m "build(scrapers): scaffold installable package skeleton"
```

---

### Task 1: Errors

**Files:**
- Create: `scrapers/scrapers/errors.py`
- Test: `scrapers/tests/unit/test_errors.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `PipelineError(Exception)`, `ConfigError(PipelineError, ValueError)`, `DependencyError(PipelineError)`, `SourceError(PipelineError)` with `__init__(self, source: str, message: str)` storing `.source` and `.message`, `BlockedDetected(SourceError)`, `ParseError(SourceError)`, `ExportError(PipelineError)`.

- [ ] **Step 1: Write the failing test**

```python
import pytest

from scrapers.errors import (
    BlockedDetected,
    ConfigError,
    DependencyError,
    ExportError,
    ParseError,
    PipelineError,
    SourceError,
)


def test_hierarchy():
    assert issubclass(ConfigError, PipelineError)
    assert issubclass(ConfigError, ValueError)
    assert issubclass(DependencyError, PipelineError)
    assert issubclass(BlockedDetected, SourceError)
    assert issubclass(ParseError, SourceError)
    assert issubclass(ExportError, PipelineError)


def test_source_error_carries_source():
    err = SourceError("amazon", "boom")
    assert err.source == "amazon"
    assert err.message == "boom"
    assert "amazon" in str(err)


def test_config_error_is_value_error():
    with pytest.raises(ValueError):
        raise ConfigError("bad config")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_errors.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scrapers.errors'`.

- [ ] **Step 3: Implement `scrapers/scrapers/errors.py`**

```python
"""Typed exceptions and classification for the pipeline."""


class PipelineError(Exception):
    """Base class for all pipeline errors."""


class ConfigError(PipelineError, ValueError):
    """Invalid configuration supplied."""


class DependencyError(PipelineError):
    """A required optional dependency is missing (e.g. scrapling for live mode)."""


class SourceError(PipelineError):
    """A single marketplace source failed; carries the source name."""

    def __init__(self, source: str, message: str) -> None:
        super().__init__(f"[{source}] {message}")
        self.source = source
        self.message = message


class BlockedDetected(SourceError):
    """A source appears to be blocking or bot-walling us."""


class ParseError(SourceError):
    """Failed to parse a product page."""


class ExportError(PipelineError):
    """Failed to write or export results."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_errors.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/errors.py scrapers/tests/unit/test_errors.py
git commit -m "feat(scrapers): add typed error hierarchy"
```

---

### Task 2: Settings config

**Files:**
- Create: `scrapers/scrapers/config.py`
- Test: `scrapers/tests/unit/test_config.py`

**Interfaces:**
- Consumes: `ConfigError` (Task 1).
- Produces: `Settings` frozen dataclass with `from_env(env=None, env_file=None) -> Settings`, `to_dict(redact=True) -> dict`, helpers `parse_bool(value) -> bool`, `as_csv(value) -> tuple[str, ...]`; module constants `DEFAULT_AMAZON_BESTSELLERS_URLS`, `DEFAULT_AMAZON_NODE_CATEGORIES`, `DEFAULT_DEODAP_CATEGORIES`.

- [ ] **Step 1: Write the failing test**

```python
import pytest

from scrapers.config import DEFAULT_AMAZON_BESTSELLERS_URLS, Settings, as_csv, parse_bool
from scrapers.errors import ConfigError

ENV = {
    "LOG_LEVEL": "debug",
    "LOG_FORMAT": "json",
    "SCRAPLING_ADAPTIVE": "1",
    "SCRAPLING_ADAPTIVE_PERCENTAGE": "60",
    "SCRAPLING_PROXY": "http://user:pass@host:8080",
    "AMAZON_BESTSELLERS_URLS": "https://a.in/x, https://a.in/y",
    "AMAZON_NODE_CATEGORIES": '{"1381": "storage"}',
    "MIN_CONFIDENCE": "0.65",
    "MIN_ABSOLUTE_MARGIN": "150",
    "DEODAP_MAX_PAGES": "5",
    "WEBHOOK_SECRET": "hunter2",
}


def test_from_env_parses():
    s = Settings.from_env(env=ENV)
    assert s.log_level == "DEBUG"
    assert s.log_format == "json"
    assert s.adaptive is True
    assert s.adaptive_percentage == 60
    assert s.proxy_url == "http://user:pass@host:8080"
    assert s.amazon_bestsellers_urls == ("https://a.in/x", "https://a.in/y")
    assert s.amazon_node_categories == {"1381": "storage"}
    assert s.min_confidence == 0.65
    assert s.min_absolute_margin == 150.0
    assert s.deodap_max_pages == 5


def test_from_env_defaults():
    s = Settings.from_env(env={})
    assert s.log_level == "INFO"
    assert s.deodap_max_pages == 3
    assert s.amazon_bestsellers_urls == DEFAULT_AMAZON_BESTSELLERS_URLS


def test_helpers():
    assert parse_bool("True") is True
    assert parse_bool("no") is False
    assert parse_bool(None) is False
    assert as_csv("a, b, c") == ("a", "b", "c")
    assert as_csv(None) == ()


def test_validation_fails_fast():
    with pytest.raises(ConfigError, match="LOG_LEVEL"):
        Settings.from_env(env={"LOG_LEVEL": "shouty"})
    with pytest.raises(ConfigError, match="SCRAPLING_ADAPTIVE_PERCENTAGE"):
        Settings.from_env(env={"SCRAPLING_ADAPTIVE_PERCENTAGE": "300"})
    with pytest.raises(ConfigError, match="MIN_CONFIDENCE"):
        Settings.from_env(env={"MIN_CONFIDENCE": "1.5"})
    with pytest.raises(ConfigError, match="SCRAPLING_PROXY"):
        Settings.from_env(env={"SCRAPLING_PROXY": "not a url"})


def test_to_dict_redacts_secrets():
    s = Settings.from_env(env={"WEBHOOK_SECRET": "hunter2", "SCRAPLING_PROXY": "http://user:pass@host:8080"})
    d = s.to_dict(redact=True)
    assert d["webhook_secret"] == "***"
    assert "pass" not in d["proxy_url"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_config.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scrapers.config'`.

- [ ] **Step 3: Implement `scrapers/scrapers/config.py`**

```python
"""Central, validated pipeline settings, loaded from env / .env file."""
import json
import os
from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple, Any
from urllib.parse import urlparse

from scrapers.errors import ConfigError

DEFAULT_AMAZON_BESTSELLERS_URLS = (
    "https://www.amazon.in/bestsellers/kitchen",
    "https://www.amazon.in/gp/bestsellers/kitchen/1380510031",
    "https://www.amazon.in/gp/bestsellers/kitchen/1380374031",
    "https://www.amazon.in/gp/bestsellers/kitchen/1380181031",
    "https://www.amazon.in/gp/bestsellers/kitchen/1379989031",
)
DEFAULT_AMAZON_NODE_CATEGORIES = {
    "1380510031": "home-storage",
    "1380374031": "home-decor",
    "1380181031": "kitchen-tools",
    "1379989031": "kitchen-storage",
}
DEFAULT_DEODAP_CATEGORIES = (
    "kitchen-dining-items",
    "cookware-items",
    "home-storage-organisation-items",
    "home-decor-wall-art-items",
    "best-selling-products",
)
_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_LOG_FORMATS = {"console", "json"}


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def as_csv(value: Any) -> Tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(v.strip() for v in value.split(",") if v.strip())
    return tuple(v for v in value if v)


def _as_int(value, default: int) -> int:
    if not value:
        return default
    return int(value)


def _as_float(value, default: float) -> float:
    if not value:
        return default
    return float(value)


def _as_dict(value) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in AMAZON_NODE_CATEGORIES: {value!r}") from exc
    if not isinstance(parsed, dict):
        raise ConfigError(f"AMAZON_NODE_CATEGORIES must be a JSON object")
    return parsed


@dataclass(frozen=True)
class Settings:
    log_level: str = "INFO"
    log_format: str = "console"
    output_dir: str = "data"
    history_dir: Optional[str] = None
    allow_mock_fallback: bool = False

    adaptive: bool = False
    adaptive_percentage: int = 40
    crawldir: Optional[str] = None
    proxy_url: Optional[str] = None

    amazon_movers_url: str = "https://www.amazon.in/gp/movers-and-shakers"
    amazon_bestsellers_urls: Tuple[str, ...] = DEFAULT_AMAZON_BESTSELLERS_URLS
    amazon_node_categories: dict = field(default_factory=lambda: dict(DEFAULT_AMAZON_NODE_CATEGORIES))
    meesho_trending_url: str = "https://www.meesho.com/trending"
    flipkart_bestsellers_url: str = "https://www.flipkart.com/best-sellers"
    deodap_base_url: str = "https://deodap.in"
    deodap_categories: Tuple[str, ...] = DEFAULT_DEODAP_CATEGORIES
    deodap_max_pages: int = 3

    min_confidence: float = 0.5
    min_absolute_margin: float = 200.0
    min_margin_pct: float = 35.0
    min_ticket_price: float = 300.0
    max_sellers: int = 5
    max_fba_sellers: int = 2
    report_top_n: int = 25

    sheets_service_account: Optional[str] = None
    sheets_spreadsheet_id: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None

    def __post_init__(self) -> None:
        _validate(self)

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None, env_file: Optional[str] = None) -> "Settings":
        if env_file:
            try:
                from dotenv import load_dotenv

                load_dotenv(env_file)
            except ImportError:
                raise ConfigError("python-dotenv required to load --env-file") from None
        env = env if env is not None else os.environ

        def _env(name: str) -> Optional[str]:
            return env.get(name)

        return cls(
            log_level=(_env("LOG_LEVEL") or "INFO").strip().upper(),
            log_format=(_env("LOG_FORMAT") or "console").strip().lower(),
            output_dir=_env("OUTPUT_DIR") or "data",
            history_dir=_env("HISTORY_DIR") or None,
            allow_mock_fallback=parse_bool(_env("SCRAPLING_ALLOW_MOCK_FALLBACK")),
            adaptive=parse_bool(_env("SCRAPLING_ADAPTIVE")),
            adaptive_percentage=_as_int(_env("SCRAPLING_ADAPTIVE_PERCENTAGE"), 40),
            crawldir=_env("SCRAPLING_CRAWL_DIR") or None,
            proxy_url=_env("SCRAPLING_PROXY") or None,
            amazon_movers_url=_env("AMAZON_MOVERS_URL") or "https://www.amazon.in/gp/movers-and-shakers",
            amazon_bestsellers_urls=as_csv(_env("AMAZON_BESTSELLERS_URLS")) or DEFAULT_AMAZON_BESTSELLERS_URLS,
            amazon_node_categories=_as_dict(_env("AMAZON_NODE_CATEGORIES")) or DEFAULT_AMAZON_NODE_CATEGORIES,
            meesho_trending_url=_env("MEESHO_TRENDING_URL") or "https://www.meesho.com/trending",
            flipkart_bestsellers_url=_env("FLIPKART_BESTSELLERS_URL") or "https://www.flipkart.com/best-sellers",
            deodap_base_url=_env("DEODAP_BASE_URL") or "https://deodap.in",
            deodap_categories=as_csv(_env("DEODAP_CATEGORIES")) or DEFAULT_DEODAP_CATEGORIES,
            deodap_max_pages=_as_int(_env("DEODAP_MAX_PAGES"), 3),
            min_confidence=_as_float(_env("MIN_CONFIDENCE"), 0.5),
            min_absolute_margin=_as_float(_env("MIN_ABSOLUTE_MARGIN"), 200.0),
            min_margin_pct=_as_float(_env("MIN_MARGIN_PCT"), 35.0),
            min_ticket_price=_as_float(_env("MIN_TICKET_PRICE"), 300.0),
            max_sellers=_as_int(_env("MAX_SELLERS"), 5),
            max_fba_sellers=_as_int(_env("MAX_FBA_SELLERS"), 2),
            report_top_n=_as_int(_env("REPORT_TOP_N"), 25),
            sheets_service_account=_env("SHEETS_SERVICE_ACCOUNT") or None,
            sheets_spreadsheet_id=_env("SHEETS_SPREADSHEET_ID") or None,
            webhook_url=_env("WEBHOOK_URL") or None,
            webhook_secret=_env("WEBHOOK_SECRET") or None,
        )

    def to_dict(self, redact: bool = True) -> dict:
        data = {k: (list(v) if isinstance(v, tuple) else v) for k, v in self.__dict__.items()}
        if redact:
            if data.get("webhook_secret"):
                data["webhook_secret"] = "***"
            proxy = data.get("proxy_url")
            if proxy:
                parsed = urlparse(proxy)
                netloc = parsed.hostname or ""
                if parsed.port:
                    netloc = f"{netloc}:{parsed.port}"
                data["proxy_url"] = f"{parsed.scheme}://{netloc}"
        return data


def _validate(s: Settings) -> None:
    if s.log_level not in _LOG_LEVELS:
        raise ConfigError(f"LOG_LEVEL must be one of {sorted(_LOG_LEVELS)}, got {s.log_level!r}")
    if s.log_format not in _LOG_FORMATS:
        raise ConfigError(f"LOG_FORMAT must be one of {sorted(_LOG_FORMATS)}, got {s.log_format!r}")
    if not 0 <= s.adaptive_percentage <= 100:
        raise ConfigError(f"SCRAPLING_ADAPTIVE_PERCENTAGE must be 0-100, got {s.adaptive_percentage}")
    if s.deodap_max_pages < 1:
        raise ConfigError(f"DEODAP_MAX_PAGES must be >= 1, got {s.deodap_max_pages}")
    if not 0 < s.min_confidence <= 1:
        raise ConfigError(f"MIN_CONFIDENCE must be in (0,1], got {s.min_confidence}")
    if s.min_absolute_margin < 0:
        raise ConfigError(f"MIN_ABSOLUTE_MARGIN must be >= 0, got {s.min_absolute_margin}")
    if s.min_margin_pct < 0:
        raise ConfigError(f"MIN_MARGIN_PCT must be >= 0, got {s.min_margin_pct}")
    if s.min_ticket_price <= 0:
        raise ConfigError(f"MIN_TICKET_PRICE must be > 0, got {s.min_ticket_price}")
    if not s.amazon_bestsellers_urls:
        raise ConfigError("AMAZON_BESTSELLERS_URLS must not be empty")
    if s.proxy_url:
        parsed = urlparse(s.proxy_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigError(f"SCRAPLING_PROXY must be an http(s)://host:port URL, got {s.proxy_url!r}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_config.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/config.py scrapers/tests/unit/test_config.py
git commit -m "feat(scrapers): add validated Settings config"
```

---

### Task 3: Structured logging

**Files:**
- Create: `scrapers/scrapers/logging_setup.py`
- Test: `scrapers/tests/unit/test_logging_setup.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `setup_logging(level: str, fmt: str = "console") -> None`, `add_file_handler(path: str) -> None`, `redact_url(url: Optional[str]) -> str`. Exposes module-level `fmt_fn: dict[str, logging.Formatter]` with keys `"console"` and `"json"` so tests and `add_file_handler` can pick the formatter.

- [ ] **Step 1: Write the failing test**

```python
import io
import json
import logging

from scrapers.logging_setup import add_file_handler, redact_url, setup_logging


def test_redact_url_strips_credentials():
    assert redact_url("http://user:pass@host:8080") == "http://host:8080"
    assert redact_url("http://host:8080") == "http://host:8080"
    assert redact_url(None) == ""


def _capture(fmt):
    logger = logging.getLogger(f"capture-{fmt}")
    logger.handlers.clear()
    logger.propagate = False
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(setup_logging.fmt_fn[fmt])
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info("hello %s", "world", extra={"fields": {"source": "amazon"}})
    return stream.getvalue()


def test_console_format():
    out = _capture("console")
    assert "hello world" in out


def test_json_format():
    out = _capture("json")
    record = json.loads(out)
    assert record["message"] == "hello world"
    assert record["level"] == "INFO"
    assert record["source"] == "amazon"


def test_add_file_handler(tmp_path):
    logfile = tmp_path / "run.log"
    add_file_handler(str(logfile))
    logging.getLogger("file-adder").info("written")
    assert "written" in logfile.read_text()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_logging_setup.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scrapers.logging_setup'`.

- [ ] **Step 3: Implement `scrapers/scrapers/logging_setup.py`**

```python
"""Structured logging (console or JSON) with secret redaction."""
import json
import logging
import sys
from typing import Optional
from urllib.parse import urlparse


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


fmt_fn = {
    "console": logging.Formatter("%(asctime)s %(levelname)-7s [%(name)s] %(message)s", "%H:%M:%S"),
    "json": _JsonFormatter(),
}

_INSTALLED = False


def setup_logging(level: str, fmt: str = "console") -> None:
    global _INSTALLED
    root = logging.getLogger()
    root.setLevel(level.upper())
    if not _INSTALLED:
        root.addHandler(logging.StreamHandler(sys.stdout))
        _INSTALLED = True
    for handler in root.handlers:
        handler.setFormatter(fmt_fn.get(fmt, fmt_fn["console"]))


def add_file_handler(path: str) -> None:
    root = logging.getLogger()
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(fmt_fn["json"] if any(
        h.getFormatter().__class__.__name__ == "_JsonFormatter" for h in root.handlers)
        else fmt_fn["console"])
    handler.setLevel(root.level)
    root.addHandler(handler)


def redact_url(url: Optional[str]) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return f"{parsed.scheme}://{netloc}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_logging_setup.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/logging_setup.py scrapers/tests/unit/test_logging_setup.py
git commit -m "feat(scrapers): add structured logging with redaction"
```

---

### Task 4: Atomic IO

**Files:**
- Create: `scrapers/scrapers/io.py`
- Test: `scrapers/tests/unit/test_io.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `new_run_id() -> str` (UTC `%Y%m%dT%H%M%SZ`), `ensure_dir(path) -> None`, `atomic_write_text(path, text) -> None`, `atomic_write_json(path, data) -> None`, `load_json(path, default=None) -> Any`, `write_manifest(output_dir, run_id, manifest) -> Path`.

- [ ] **Step 1: Write the failing test**

```python
from scrapers.io import (
    atomic_write_json,
    atomic_write_text,
    ensure_dir,
    load_json,
    new_run_id,
    write_manifest,
)


def test_run_id_format():
    rid = new_run_id()
    assert len(rid) == len("20260914T123456Z")
    assert rid.endswith("Z")


def test_atomic_json_roundtrip(tmp_path):
    p = tmp_path / "a" / "b" / "data.json"
    atomic_write_json(p, {"x": [1, 2], "unicode": "₹"})
    data = load_json(p)
    assert data == {"x": [1, 2], "unicode": "₹"}
    assert not list(p.parent.glob(".tmp-*"))


def test_load_json_missing_returns_default(tmp_path):
    assert load_json(tmp_path / "nope.json", []) == []


def test_manifest_created(tmp_path):
    out = tmp_path / "data"
    path = write_manifest(str(out), "run-1", {"status": "ok"})
    assert path.exists()
    assert load_json(path)["status"] == "ok"


def test_failed_write_leaves_no_partial(tmp_path):
    p = tmp_path / "out.json"
    atomic_write_text(p, "ok")
    try:
        atomic_write_json(p, object())
    except Exception:
        pass
    with open(p, encoding="utf-8") as fh:
        assert fh.read() == "ok"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_io.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scrapers.io'`.

- [ ] **Step 3: Implement `scrapers/scrapers/io.py`**

```python
"""Atomic, crash-safe file IO and run manifest helpers."""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_dir(path) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def atomic_write_text(path, text: str) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".tmp-", suffix=".partial")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_json(path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def load_json(path, default: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def write_manifest(output_dir, run_id: str, manifest: dict) -> Path:
    path = Path(output_dir) / "runs" / run_id / "manifest.json"
    atomic_write_json(path, manifest)
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_io.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/io.py scrapers/tests/unit/test_io.py
git commit -m "feat(scrapers): add atomic IO and run manifests"
```

---

### Task 5: Run metrics

**Files:**
- Create: `scrapers/scrapers/metrics.py`
- Test: `scrapers/tests/unit/test_metrics.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `SourceMetrics` dataclass (fields `name, status="ok", requested=0, scraped=0, enriched=0, blocked=0, retried=0, failed=0, elapsed_ms=0`, method `to_dict() -> dict`) and `RunMetrics` dataclass (fields `mode="mock", started_at="", finished_at="", sources: list[SourceMetrics]`, methods `for_source(name) -> SourceMetrics`, `to_dict() -> dict`, `exit_code() -> int`).

`exit_code()`: `0` if every source `status in {"ok","mock"}`; `1` if any `mock-fallback`, `failed`, or `blocked` status but at least one healthy; `3` if no healthy status remains.

- [ ] **Step 1: Write the failing test**

```python
from scrapers.metrics import RunMetrics, SourceMetrics


def test_source_metrics_to_dict():
    sm = SourceMetrics(name="amazon", scraped=5, elapsed_ms=12)
    d = sm.to_dict()
    assert d["name"] == "amazon"
    assert d["scraped"] == 5
    assert d["elapsed_ms"] == 12
    assert d["status"] == "ok"


def test_run_metrics_tracks_sources():
    rm = RunMetrics(mode="live", started_at="t0")
    a = rm.for_source("amazon")
    a.scraped = 10
    b = rm.for_source("meesho")
    b.status = "mock-fallback"
    assert len(rm.sources) == 2
    d = rm.to_dict()
    assert d["mode"] == "live"
    assert d["sources"][0]["name"] == "amazon"


def test_exit_codes():
    ok = RunMetrics(sources=[SourceMetrics(name="a"), SourceMetrics(name="b")])
    assert ok.exit_code() == 0
    fall = RunMetrics(sources=[SourceMetrics(name="a", status="mock-fallback")])
    assert fall.exit_code() == 1
    failed = RunMetrics(sources=[SourceMetrics(name="a", status="failed"), SourceMetrics(name="b", status="ok")])
    assert failed.exit_code() == 1
    af = RunMetrics(sources=[SourceMetrics(name="a", status="failed"), SourceMetrics(name="b", status="blocked")])
    assert af.exit_code() == 3
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_metrics.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scrapers.metrics'`.

- [ ] **Step 3: Implement `scrapers/scrapers/metrics.py`**

```python
"""Per-source counters and run summaries."""
from dataclasses import dataclass, field
from typing import List


@dataclass
class SourceMetrics:
    name: str
    status: str = "ok"
    requested: int = 0
    scraped: int = 0
    enriched: int = 0
    blocked: int = 0
    retried: int = 0
    failed: int = 0
    elapsed_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "requested": self.requested,
            "scraped": self.scraped,
            "enriched": self.enriched,
            "blocked": self.blocked,
            "retried": self.retried,
            "failed": self.failed,
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass
class RunMetrics:
    mode: str = "mock"
    started_at: str = ""
    finished_at: str = ""
    sources: List[SourceMetrics] = field(default_factory=list)

    def for_source(self, name: str) -> SourceMetrics:
        for existing in self.sources:
            if existing.name == name:
                return existing
        metric = SourceMetrics(name=name)
        self.sources.append(metric)
        return metric

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "sources": [s.to_dict() for s in self.sources],
        }

    def exit_code(self) -> int:
        if not self.sources:
            return 0
        statuses = [s.status for s in self.sources]
        healthy = {"ok", "mock"}
        if all(st in healthy for st in statuses):
            return 0
        if any(st in {"failed", "mock-fallback", "blocked"} for st in statuses):
            if all(st not in healthy for st in statuses):
                return 3
            return 1
        return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_metrics.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/metrics.py scrapers/tests/unit/test_metrics.py
git commit -m "feat(scrapers): add run metrics and exit-code logic"
```

---

### Task 6: Source registry

**Files:**
- Create: `scrapers/scrapers/registry.py`
- Test: `scrapers/tests/unit/test_registry.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `SourceSpec` frozen dataclass (fields `name, title, output_file, default_max_products, live_capable, mock_items: tuple[dict, ...] = (), spider_cls: Optional[type] = None, spider_kwargs: Optional[Callable[[object], dict]] = None`); `register_source(spec) -> None`; `get_source(name) -> SourceSpec` (raises `KeyError` listing available names); `list_sources() -> tuple[SourceSpec, ...]`; `builtin_names() -> tuple[str, ...]`.

- [ ] **Step 1: Write the failing test**

```python
import pytest

import scrapers.registry as reg


def _reset():
    reg._SOURCES.clear()


def test_register_and_get():
    _reset()
    spec = reg.SourceSpec(
        name="amazon",
        title="Amazon",
        output_file="amazon_raw.json",
        default_max_products=5,
        live_capable=True,
        mock_items=(),
    )
    reg.register_source(spec)
    assert reg.get_source("amazon") is spec
    assert reg.builtin_names() == ("amazon",)


def test_duplicate_rejected():
    _reset()
    spec = reg.SourceSpec(name="amazon", title="A", output_file="a.json",
                          default_max_products=1, live_capable=True, mock_items=())
    reg.register_source(spec)
    with pytest.raises(ValueError):
        reg.register_source(spec)


def test_get_unknown_lists_names():
    _reset()
    reg.register_source(reg.SourceSpec(name="x", title="X", output_file="x.json",
                                       default_max_products=1, live_capable=True, mock_items=()))
    with pytest.raises(KeyError) as exc:
        reg.get_source("nope")
    assert "x" in str(exc.value)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_registry.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scrapers.registry'`.

- [ ] **Step 3: Implement `scrapers/scrapers/registry.py`**

```python
"""Source registry: one place that knows every marketplace source."""
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple, Type


@dataclass(frozen=True)
class SourceSpec:
    name: str
    title: str
    output_file: str
    default_max_products: int
    live_capable: bool
    mock_items: Tuple[dict, ...] = ()
    spider_cls: Optional[Type[Any]] = None
    spider_kwargs: Optional[Callable[[Any], dict]] = None

    def build_spider_kwargs(self, settings: Any) -> dict:
        if self.spider_kwargs is not None:
            return self.spider_kwargs(settings)
        return {"max_products": self.default_max_products, "crawldir": settings.crawldir}


_SOURCES: Dict[str, SourceSpec] = {}


def register_source(spec: SourceSpec) -> None:
    if spec.name in _SOURCES:
        raise ValueError(f"source already registered: {spec.name}")
    _SOURCES[spec.name] = spec


def get_source(name: str) -> SourceSpec:
    try:
        return _SOURCES[name]
    except KeyError:
        available = ", ".join(sorted(_SOURCES)) or "(none)"
        raise KeyError(f"unknown source {name!r}; available: {available}") from None


def list_sources() -> Tuple[SourceSpec, ...]:
    return tuple(_SOURCES.values())


def builtin_names() -> Tuple[str, ...]:
    return tuple(_SOURCES.keys())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_registry.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/registry.py scrapers/tests/unit/test_registry.py
git commit -m "feat(scrapers): add source registry"
```

---

### Task 7: Parsing utilities (ported)

**Files:**
- Create: `scrapers/scrapers/parsing_utils.py` (copy current `scrapers/parsing_utils.py` body verbatim, only the top import guarded)
- Test: `scrapers/tests/unit/test_parsing_utils.py`

**Interfaces:**
- Consumes: nothing.
- Produces: all existing helpers — `first_text`, `all_text`, `full_text`, `count_matches`, `has_any_text`, `breadcrumb_path`, `parse_price`, `parse_int`, `parse_optional_int`, `parse_rating`, `parse_weight_g`, `parse_dimensions_cm`, `parse_bsr`, `extract_product_id`, `short_text`. `TextNode` must be importable without `scrapling` installed.

- [ ] **Step 1: Write the failing test**

```python
from scrapers.parsing_utils import (
    extract_product_id,
    parse_bsr,
    parse_dimensions_cm,
    parse_int,
    parse_price,
    parse_rating,
    parse_weight_g,
)


def test_parse_price():
    assert parse_price("₹1,299.50") == 1299.5
    assert parse_price("Rs. 499") == 499.0
    assert parse_price("INR 99") == 99.0
    assert parse_price("no price here") is None
    assert parse_price(None) is None


def test_parse_int():
    assert parse_int("1,234 ratings", 0) == 1234
    assert parse_int("none", 7) == 7


def test_parse_rating():
    assert parse_rating("4.4 out of 5") == 4.4


def test_parse_weight_g():
    assert parse_weight_g("Item Weight: 220 g") == 220
    assert parse_weight_g("1.5 kg") == 1500


def test_parse_dimensions_cm():
    assert parse_dimensions_cm("18 x 6 x 4 cm") == "18x6x4"
    assert parse_dimensions_cm("42x3x2 cm") == "42x3x2"


def test_parse_bsr():
    assert parse_bsr("#1,250 in Kitchen") == (1250, "Kitchen")
    assert parse_bsr("nothing") == (None, None)


def test_extract_product_id():
    assert extract_product_id("https://www.amazon.in/dp/B09X7Y6Z5W?th=1", "/dp/") == "B09X7Y6Z5W"


def test_textnode_importable_without_scrapling():
    from scrapers.parsing_utils import TextNode
    assert TextNode is not None
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_parsing_utils.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scrapers.parsing_utils'`.

- [ ] **Step 3: Port the module with a guarded import**

Copy the body of the current `scrapers/parsing_utils.py` into `scrapers/scrapers/parsing_utils.py` unchanged, except replace the first lines with:

```python
import re
from typing import Any, List, Optional, Sequence, Tuple, Union

try:  # scrapling is only required for live runs
    from scrapling.parser import Selector, Selectors

    TextNode = Union[Selector, Selectors]
except ImportError:  # pragma: no cover
    TextNode = Any
```

Keep the remainder of the file byte-for-byte identical to the current version.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_parsing_utils.py -q`
Expected: PASS (pure parsers work with no `scrapling` installed).

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/parsing_utils.py scrapers/tests/unit/test_parsing_utils.py
git commit -m "refactor(scrapers): port parsing utils with guarded scrapling import"
```

---

### Task 8: Base spider + runner (ported)

**Files:**
- Create: `scrapers/scrapers/sources/base.py`
- Test: `scrapers/tests/unit/test_sources_base.py`

**Interfaces:**
- Consumes: Tasks 4, 7; `DependencyError` (Task 1).
- Produces: `SPIDERS_OK: bool`; `MarketplaceSpider` (same surface as today); `adaptive_flags() -> dict`; `run_spider(spider) -> list[dict]` (takes an already-constructed spider instance, raises `DependencyError` if `not SPIDERS_OK`, starts it and returns deduped items); `dedupe_items(items) -> list[dict]`; `write_items(items, path) -> list[dict]`; `load_items(path) -> list[dict]`; `ensure_output_paths(paths)`.

- [ ] **Step 1: Write the failing test**

```python
import pytest

from scrapers.errors import DependencyError
from scrapers.io import load_json
from scrapers.sources.base import (
    SPIDERS_OK,
    dedupe_items,
    ensure_output_paths,
    load_items,
    run_spider,
    write_items,
)


def test_dedupe_prefers_full_and_merges():
    items = [
        {"asin": "A1", "title": "t", "current_price": 100, "quality": "card"},
        {"asin": "A1", "title": "t", "current_price": 110, "seller_count": 3, "quality": "full"},
        {"asin": "A2", "title": "u", "current_price": 90, "quality": "full"},
    ]
    out = dedupe_items(items)
    by_asin = {i["asin"]: i for i in out}
    assert set(by_asin) == {"A1", "A2"}
    assert by_asin["A1"]["current_price"] == 110
    assert by_asin["A1"]["seller_count"] == 3


def test_write_load_items(tmp_path):
    path = tmp_path / "raw.json"
    write_items([{"a": 1}], str(path))
    assert load_items(str(path)) == [{"a": 1}]
    assert load_json(path) == [{"a": 1}]


def test_load_missing_returns_empty(tmp_path):
    assert load_items(str(tmp_path / "nope.json")) == []


def test_ensure_output_paths(tmp_path):
    p = str(tmp_path / "x" / "y.json")
    ensure_output_paths([p])
    assert (tmp_path / "x").exists()


def test_run_spider_requires_scrapling():
    if SPIDERS_OK:
        pytest.skip("scrapling present; dependency guard not applicable")
    with pytest.raises(DependencyError):
        run_spider(object())
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_sources_base.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scrapers.sources.base'`.

- [ ] **Step 3: Port `scrapers/scrapers/sources/base.py`**

Start from the current `scrapers/base.py`; apply these changes:

1. Header with guarded scrapling import:

```python
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

try:  # scrapling is only required for live runs
    from scrapling.spiders import Response, Spider
    from scrapling.fetchers import (
        AsyncDynamicSession,
        AsyncStealthySession,
        FetcherSession,
    )

    SPIDERS_OK = True
except ImportError:  # pragma: no cover
    Response = Any
    Spider = Any
    AsyncDynamicSession = Any
    AsyncStealthySession = Any
    FetcherSession = Any
    SPIDERS_OK = False

from scrapers.errors import DependencyError
from scrapers.io import atomic_write_json, load_json
from scrapers.parsing_utils import (
    all_text,
    count_matches,
    first_text,
    full_text,
    has_any_text,
)
```

2. `.py` constants, `adaptive_flags()`, `MarketplaceSpider`, `dedupe_items`, `load_items`, `ensure_output_paths` keep their current bodies. `load_items` becomes:

```python
def load_items(filepath: str) -> List[Dict[str, Any]]:
    return list(load_json(filepath, default=[]))
```

3. `write_items` becomes:

```python
def write_items(items: List[Dict[str, Any]], output_path: str) -> List[Dict[str, Any]]:
    atomic_write_json(output_path, items)
    print(f"  Saved {len(items)} items to {output_path}")
    return items
```

4. `run_spider` becomes (instance-based — the orchestrator constructs the spider):

```python
def run_spider(spider) -> List[Dict[str, Any]]:
    if not SPIDERS_OK:
        raise DependencyError(
            "Live scraping requires 'scrapling[fetchers]'. "
            "Install it on a glibc host (e.g. proot-Distro Ubuntu): "
            "pip install -e '.[fetchers]' && scrapling install"
        )
    name = getattr(spider, "name", "?")
    print(f"  Running {name} (adaptive={'on' if spider.flags['adaptive'] else 'off'})...")
    result = spider.start()
    items = dedupe_items([item for item in result.items])
    print(f"  {name}: scraped {len(items)} items")
    if not items:
        print(f"  [FAIL] {name} produced no items")
    return items
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_sources_base.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/sources/base.py scrapers/tests/unit/test_sources_base.py
git commit -m "refactor(scrapers): port base spider with guarded imports and atomic IO"
```

---

### Task 9: Port Amazon source

**Files:**
- Create: `scrapers/scrapers/sources/amazon.py` (port of `scrapers/amazon_movers_spider.py`)
- Test: `scrapers/tests/unit/test_sources_amazon.py`

**Interfaces:**
- Consumes: Task 8.
- Produces: `MoversProduct` dataclass, `MOCK_AMAZON_MOVERS` (unchanged values), `AmazonMoversSpider`, `SeedAsinsSpider`, `SEED_FILE` path, `mock_items() -> list[dict]`.

- [ ] **Step 1: Write the failing test**

```python
from scrapers.sources.amazon import (
    MOCK_AMAZON_MOVERS,
    AmazonMoversSpider,
    extract_asin,
    mock_items,
)


def test_mock_records_have_id_title_price_url():
    records = mock_items()
    assert len(records) >= 10
    for r in records:
        assert r["asin"]
        assert r["title"]
        assert r["current_price"] > 0
        assert r["product_url"].startswith("https://")


def test_mock_records_are_stable():
    records = mock_items()
    assert records[0]["asin"] == MOCK_AMAZON_MOVERS[0].asin
    assert records[0]["current_price"] == 199.0


def test_extract_asin():
    assert extract_asin("https://www.amazon.in/dp/B09X7Y6Z5W") == "B09X7Y6Z5W"
    assert extract_asin("https://www.amazon.in/dp/NO3NOPE") is None


def test_spider_configuration_surface():
    assert AmazonMoversSpider.name == "amazon_movers"
    assert AmazonMoversSpider.allowed_domains == {"amazon.in"}
    assert AmazonMoversSpider.adaptive_domain == "amazon.in"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_sources_amazon.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scrapers.sources.amazon'`.

- [ ] **Step 3: Port `scrapers/scrapers/sources/amazon.py`**

Copy `scrapers/amazon_movers_spider.py` into `scrapers/scrapers/sources/amazon.py` and apply ONLY these edits:

1. Import header:

```python
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

from scrapers.sources.base import MarketplaceSpider
from scrapers.parsing_utils import (
    extract_product_id,
    parse_bsr,
    parse_dimensions_cm,
    parse_int,
    parse_price,
    parse_rating,
    parse_weight_g,
)
```

(Remove the old `run_spider`/`write_items` imports; the orchestrator handles writing. Keep everything else inside the module unchanged.)

2. Replace the seed-file path resolution so it reads the new location:

```python
SEED_FILE = Path(__file__).parent / "seed_asins.json"
```

and change `load_seed_asins` to open `SEED_FILE`.

3. Add at the end of the module (before `__main__`):

```python
def mock_items() -> list:
    return [asdict(p) for p in MOCK_AMAZON_MOVERS]
```

4. Keep dataclass `MoversProduct`, `MOCK_AMAZON_MOVERS`, `MOVERS_URL`, `BESTSELLERS_URLS`, `NODE_CATEGORIES`, `category_for_url`, `extract_asin`, `AmazonMoversSpider`, `SeedAsinsSpider`, and the `__main__` argparse block byte-for-byte identical.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_sources_amazon.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/sources/amazon.py scrapers/tests/unit/test_sources_amazon.py
git commit -m "refactor(scrapers): port amazon source"
```

---

### Task 10: Port Meesho and Flipkart sources

**Files:**
- Create: `scrapers/scrapers/sources/meesho.py` (from `scrapers/meesho_trending_spider.py`), `scrapers/scrapers/sources/flipkart.py` (from `scrapers/flipkart_bestsellers_spider.py`)
- Test: `scrapers/tests/unit/test_sources_meesho_flipkart.py`

**Interfaces:**
- Consumes: Task 8.
- Produces: `MeeshoProduct`, `MOCK_MEESHO_TRENDING`, `MeeshoSpider`, `mock_items() -> list[dict]`; `FlipkartProduct`, `MOCK_FLIPKART_BESTSELLERS`, `FlipkartSpider`, `mock_items() -> list[dict]`.

- [ ] **Step 1: Write the failing test**

```python
from scrapers.sources.flipkart import MOCK_FLIPKART_BESTSELLERS, FlipkartSpider, mock_items as fk_mock
from scrapers.sources.meesho import MOCK_MEESHO_TRENDING, MeeshoSpider, mock_items as ms_mock


def test_meesho_mock_and_config():
    records = ms_mock()
    assert len(records) >= 6
    for r in records:
        assert r["product_id"]
        assert r["title"]
        assert r["current_price"] > 0
    assert MeeshoSpider.name == "meesho_trending"
    assert MeeshoSpider.allowed_domains == {"meesho.com"}
    assert records[0]["product_id"] == MOCK_MEESHO_TRENDING[0].product_id


def test_flipkart_mock_and_config():
    records = fk_mock()
    assert len(records) >= 5
    for r in records:
        assert r["product_id"]
        assert r["current_price"] > 0
        assert r["seller_count"] >= 1
    assert FlipkartSpider.name == "flipkart_bestsellers"
    assert FlipkartSpider.allowed_domains == {"flipkart.com"}
    assert records[0]["product_id"] == MOCK_FLIPKART_BESTSELLERS[0].product_id
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_sources_meesho_flipkart.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Port both modules**

For each file, copy the current content into the new path and apply the same pattern as Task 9:

- Header imports (meesho):

```python
import os
from dataclasses import asdict, dataclass
from typing import List, Optional

from scrapers.sources.base import MarketplaceSpider
from scrapers.parsing_utils import (
    extract_product_id,
    parse_int,
    parse_price,
    parse_rating,
    parse_weight_g,
)
```

- Header imports (flipkart): same, plus `import re` and `parse_dimensions_cm` (both already in the source file):

```python
import os
import re
from dataclasses import asdict, dataclass
from typing import List, Optional

from scrapers.sources.base import MarketplaceSpider
from scrapers.parsing_utils import (
    extract_product_id,
    parse_dimensions_cm,
    parse_int,
    parse_price,
    parse_rating,
    parse_weight_g,
)
```

- Add a `mock_items()` function at the end of each module (before `__main__`):

```python
def mock_items() -> list:
    return [asdict(p) for p in MOCK_MEESHO_TRENDING]
```

```python
def mock_items() -> list:
    return [asdict(p) for p in MOCK_FLIPKART_BESTSELLERS]
```

- Keep dataclasses, MOCK lists, env URL defaults, spider classes, and `__main__` blocks identical.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_sources_meesho_flipkart.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/sources/meesho.py scrapers/scrapers/sources/flipkart.py scrapers/tests/unit/test_sources_meesho_flipkart.py
git commit -m "refactor(scrapers): port meesho and flipkart sources"
```

---

### Task 11: Port DeoDap source

**Files:**
- Create: `scrapers/scrapers/sources/deodap.py` (from `scrapers/deodap_catalog_spider.py`)
- Test: `scrapers/tests/unit/test_sources_deodap.py`

**Interfaces:**
- Consumes: Task 8.
- Produces: `DeodapProduct`, `MOCK_DEODAP_CATALOG`, `DeodapSpider`, `resolve_categories`, `_parse_shopify_product`, `mock_items(categories=None) -> list[dict]`.

- [ ] **Step 1: Write the failing test**

```python
from scrapers.sources.deodap import DeodapSpider, MOCK_DEODAP_CATALOG, mock_items, resolve_categories


def test_mock_catalog_complete():
    records = mock_items()
    assert len(records) == len(MOCK_DEODAP_CATALOG)
    for r in records:
        assert r["sku"]
        assert r["title"]
        assert r["cost_price"] > 0
        assert r["white_label"] is True
        assert r["gst_compliant"] is True


def test_mock_items_category_filter():
    records = mock_items(categories=["kitchen-tools"])
    assert len(records) >= 2
    assert all(r["category"] == "kitchen-tools" for r in records)


def test_resolve_categories_default():
    cats = resolve_categories(None)
    assert "best-selling-products" in cats


def test_spider_surface():
    assert DeodapSpider.name == "deodap_catalog"
    assert DeodapSpider.allowed_domains == {"deodap.in"}
    assert DeodapSpider.max_products == 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_sources_deodap.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Port `scrapers/scrapers/sources/deodap.py`**

Copy the current `scrapers/deodap_catalog_spider.py` with these edits:

1. Import header:

```python
import os
import re
from dataclasses import asdict, dataclass
from typing import List, Optional

from scrapers.sources.base import MarketplaceSpider
from scrapers.parsing_utils import extract_product_id
```

2. Add (before `__main__`):

```python
def mock_items(categories: Optional[List[str]] = None) -> list:
    if categories:
        return [asdict(p) for p in MOCK_DEODAP_CATALOG if p.category in categories]
    return [asdict(p) for p in MOCK_DEODAP_CATALOG]
```

3. Keep `DeodapProduct`, `MOCK_DEODAP_CATALOG`, `BASE_URL`, `DEFAULT_CATEGORIES`, `ENV_CATEGORIES`, `ADAPTIVE_DOMAIN`, `MAX_COLLECTION_PAGES`, `resolve_categories`, `_parse_shopify_product`, `DeodapSpider`, and the `__main__` block identical.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_sources_deodap.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/sources/deodap.py scrapers/tests/unit/test_sources_deodap.py
git commit -m "refactor(scrapers): port deodap source"
```

---

### Task 12: Register built-in sources

**Files:**
- Modify: `scrapers/scrapers/sources/__init__.py`
- Test: `scrapers/tests/unit/test_sources_registry.py`

**Interfaces:**
- Consumes: Tasks 6, 9, 10, 11; `Settings`.
- Produces: importing `scrapers.sources` registers 4 sources `amazon`, `meesho`, `flipkart`, `deodap`. `list_sources()`, `get_source()`, `builtin_names()` work after import.

- [ ] **Step 1: Write the failing test**

```python
import scrapers.sources  # noqa: F401  (registration side effect)
from scrapers.registry import get_source, list_sources


def test_builtin_names_registered():
    names = {spec.name for spec in list_sources()}
    assert names == {"amazon", "meesho", "flipkart", "deodap"}


def test_specs_have_mock_items_and_outputs():
    amazon = get_source("amazon")
    assert amazon.output_file == "amazon_movers_raw.json"
    assert amazon.live_capable is True
    assert amazon.default_max_products == 50
    assert amazon.mock_items and amazon.mock_items[0]["asin"]
    assert get_source("meesho").output_file == "meesho_trending_raw.json"
    assert get_source("flipkart").output_file == "flipkart_bestsellers_raw.json"
    assert get_source("deodap").output_file == "deodap_catalog_raw.json"
    assert get_source("deodap").mock_items and get_source("deodap").mock_items[0]["sku"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_sources_registry.py -q`
Expected: FAIL (zero registered sources → `AssertionError`).

- [ ] **Step 3: Implement `scrapers/scrapers/sources/__init__.py`**

```python
"""Built-in marketplace sources; importing this module registers them."""
from typing import Any

from scrapers.registry import get_source, list_sources, register_source, SourceSpec
from scrapers.sources.amazon import AmazonMoversSpider, mock_items as amazon_mock
from scrapers.sources.deodap import DeodapSpider, mock_items as deodap_mock
from scrapers.sources.flipkart import FlipkartSpider, mock_items as flipkart_mock
from scrapers.sources.meesho import MeeshoSpider, mock_items as meesho_mock

__all__ = ["SourceSpec", "get_source", "list_sources", "register_source"]


def _deodap_kwargs(settings: Any) -> dict:
    return {
        "max_products": 0,
        "crawldir": settings.crawldir,
        "categories": list(settings.deodap_categories) or None,
    }


register_source(
    SourceSpec(
        name="amazon",
        title="Amazon India Movers & Shakers + Bestsellers",
        output_file="amazon_movers_raw.json",
        default_max_products=50,
        live_capable=True,
        mock_items=tuple(amazon_mock()),
        spider_cls=AmazonMoversSpider,
        spider_kwargs=lambda settings: {"max_products": 50, "crawldir": settings.crawldir},
    )
)
register_source(
    SourceSpec(
        name="meesho",
        title="Meesho Trending",
        output_file="meesho_trending_raw.json",
        default_max_products=30,
        live_capable=True,
        mock_items=tuple(meesho_mock()),
        spider_cls=MeeshoSpider,
        spider_kwargs=lambda settings: {"max_products": 30, "crawldir": settings.crawldir},
    )
)
register_source(
    SourceSpec(
        name="flipkart",
        title="Flipkart Bestsellers",
        output_file="flipkart_bestsellers_raw.json",
        default_max_products=25,
        live_capable=True,
        mock_items=tuple(flipkart_mock()),
        spider_cls=FlipkartSpider,
        spider_kwargs=lambda settings: {"max_products": 25, "crawldir": settings.crawldir},
    )
)
register_source(
    SourceSpec(
        name="deodap",
        title="DeoDap Wholesale Catalog",
        output_file="deodap_catalog_raw.json",
        default_max_products=0,
        live_capable=True,
        mock_items=tuple(deodap_mock()),
        spider_cls=DeodapSpider,
        spider_kwargs=_deodap_kwargs,
    )
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_sources_registry.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/sources/__init__.py scrapers/tests/unit/test_sources_registry.py
git commit -m "feat(scrapers): register built-in marketplace sources"
```

---

### Task 13: Normalized record schema + validation

**Files:**
- Create: `scrapers/scrapers/schemas.py`
- Test: `scrapers/tests/unit/test_schemas.py`

**Interfaces:**
- Consumes: `to_float` from `scrapers.matching.scoring` (Task 14) — if that creates an ordering hazard, inline a private `_to_float` here instead. Decision: define the private helper here to keep Tasks independent.
- Produces: `normalize_record(record: dict) -> dict` (coerces numeric fields, fills defaults) and `validate_record(record: dict) -> list[str]` (returns errors; empty list = valid). DeoDap records require `sku`, `title`, `cost_price > 0`, `product_url`; marketplace records require a marketplace id (`asin`/`product_id`/`sku`), `title`, `current_price > 0`, `product_url`.

- [ ] **Step 1: Write the failing test**

```python
from scrapers.schemas import normalize_record, validate_record


def _amz():
    return {
        "source": "amazon", "asin": "B1", "title": "T", "current_price": "199",
        "product_url": "https://a.in/dp/B1", "quality": "card",
    }


def _deodap():
    return {
        "source": "deodap", "sku": "S1", "title": "T", "cost_price": "65",
        "product_url": "https://d.in/p/1",
    }


def test_amazon_valid():
    assert validate_record(_amz()) == []


def test_deodap_valid():
    assert validate_record(_deodap()) == []


def test_missing_required_fields():
    bad = _amz()
    bad["current_price"] = 0
    errors = validate_record(bad)
    assert any("current_price" in e for e in errors)

    d_bad = _deodap()
    del d_bad["sku"]
    assert validate_record(d_bad)


def test_normalize_coerces_numerics():
    rec = normalize_record(_amz())
    assert rec["current_price"] == 199.0
    assert rec["review_count"] == 0


def test_unknown_source_uses_marketplace_rules():
    rec = {"source": "mystery", "title": "T", "current_price": 10, "product_url": "u"}
    assert validate_record(rec) == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_schemas.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scrapers.schemas'`.

- [ ] **Step 3: Implement `scrapers/scrapers/schemas.py`**

```python
"""Normalized ProductRecord schema: coercion + validation (stdlib only)."""
import re
from typing import List

_NUMERIC_FIELDS = (
    "current_price", "mrp", "cost_price", "discount_pct", "rating",
    "review_count", "seller_count", "fba_seller_count", "weight_g",
    "images_count", "movers_rank", "stock", "moq",
)


def _to_float(value) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _coerce(value, cast, default):
    if value is None or value == "" or value == []:
        return default
    try:
        return cast(value)
    except (TypeError, ValueError):
        return default


def normalize_record(record: dict) -> dict:
    out = dict(record)
    for field in _NUMERIC_FIELDS:
        if field in out:
            out[field] = _to_float(out[field])
    out.setdefault("quality", "full")
    out.setdefault("source", "unknown")
    out.setdefault("title", "")
    return out


def validate_record(record: dict) -> List[str]:
    record = normalize_record(record)
    errors: List[str] = []
    if not record.get("title"):
        errors.append("title is required")
    if not (record.get("product_url") or record.get("url")):
        errors.append("product_url is required")
    pid = record.get("asin") or record.get("product_id") or record.get("sku")
    if not pid:
        errors.append("marketplace id (asin/product_id/sku) is required")
    if record.get("source") == "deodap":
        if record.get("cost_price", 0.0) <= 0:
            errors.append("cost_price must be > 0")
    else:
        if record.get("current_price", 0.0) <= 0:
            errors.append("current_price must be > 0")
    return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_schemas.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/schemas.py scrapers/tests/unit/test_schemas.py
git commit -m "feat(scrapers): add normalized record schema and validation"
```

---

### Task 14: Matching — scoring (pure)

**Files:**
- Create: `scrapers/scrapers/matching/scoring.py`
- Test: `scrapers/tests/unit/test_matching_scoring.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `to_float`, `normalize_title`, `similarity`, `calculate_margin(marketplace_price, deodap_cost, weight_g) -> (net_margin, roi_pct)`, `competition_score(review_count) -> int`, `velocity_score(bsr_avg, bsr_current) -> float`, `opportunity_score(movers_rank, review_count, bsr_avg, bsr_current, roi) -> float`, `is_noise(title) -> bool`, `utility_bonus(title) -> int`, `eligible_deodap(dp, mp_price) -> bool`, constants `NOISE_PATTERNS`, `HIGH_UTILITY_KEYWORDS`.

- [ ] **Step 1: Write the failing test**

```python
import pytest

from scrapers.matching.scoring import (
    calculate_margin,
    competition_score,
    eligible_deodap,
    is_noise,
    normalize_title,
    opportunity_score,
    similarity,
    to_float,
    utility_bonus,
    velocity_score,
)


def test_margin_tier_1():
    net, roi = calculate_margin(199.0, 65.0, 180)
    expected_net = 199 - 29.85 - 5 - 16 - 3.78 - (65 * 1.18)
    assert net == pytest.approx(expected_net, abs=0.01)
    assert roi == pytest.approx((expected_net / (65 * 1.18)) * 100, abs=0.1)


def test_margin_fee_tiers():
    n2, r2 = calculate_margin(600.0, 200.0, 300)
    n3, r3 = calculate_margin(1200.0, 300.0, 600)
    assert n2 < n3
    assert r2 > 0 and r3 > 0


def test_competition_tiers():
    assert competition_score(5) == 80
    assert competition_score(30) == 100
    assert competition_score(60) == 60
    assert competition_score(500) == 20


def test_velocity():
    assert velocity_score(2000, 1000) == 50.0
    assert velocity_score(0, 1000) == 0


def test_opportunity():
    score = opportunity_score(1, 30, 2000, 1000, 100)
    assert score == pytest.approx(100 * 0.3 + 100 * 0.3 + 50 * 0.2 + 50 * 0.2, abs=0.01)


def test_similarity_normalized():
    a = "Silicone Stretch Lids Set of 12 - Reusable Food Covers"
    b = "Silicone Stretch Lids 12 Pcs - Reusable Food Covers"
    assert similarity(a, b) > 0.4


def test_noise_and_utility():
    assert is_noise("Kids Party Fancy Dress Costume Toy")
    assert not is_noise("Stainless Steel Kitchen Storage Container")
    assert utility_bonus("Airtight Stainless Steel Kitchen Storage Container") >= 2


def test_eligible_deodap():
    ok = {"white_label": True, "gst_compliant": True, "stock": 50, "weight_g": 300, "cost_price": 100}
    assert eligible_deodap(ok, 500)
    assert not eligible_deodap({**ok, "white_label": False}, 500)
    assert not eligible_deodap({**ok, "stock": 5}, 500)
    assert not eligible_deodap({**ok, "weight_g": 900}, 500)
    assert not eligible_deodap({**ok, "cost_price": 500}, 500)


def test_to_float_and_normalize():
    assert to_float("12.5") == 12.5
    assert to_float(None) == 0.0
    assert normalize_title("Silicone Lids Set of 12") == "silicone lids"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_matching_scoring.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scrapers/scrapers/matching/scoring.py`**

Port the pure pieces of the current `scrapers/matcher.py` verbatim (move, do not reimplement): `_to_float` → `to_float`, `NOISE_PATTERNS`, `HIGH_UTILITY_KEYWORDS`, `_normalize_title` → `normalize_title`, `_similarity` → `similarity`, `_calculate_margin` → `calculate_margin`, `_eligible_deodap` → `eligible_deodap`, `_is_noise` → `is_noise`, `_utility_bonus` → `utility_bonus`.

Add, extracted from the current `_score_match` logic:

```python
def competition_score(review_count: int) -> int:
    if 10 <= review_count <= 50:
        return 100
    if review_count < 10:
        return 80
    if review_count <= 100:
        return 60
    return 20


def velocity_score(bsr_avg: float, bsr_current: float) -> float:
    if bsr_avg <= 0:
        return 0.0
    return max(0.0, min(100.0, ((bsr_avg - bsr_current) / bsr_avg) * 100))


def opportunity_score(
    movers_rank: int,
    review_count: int,
    bsr_avg: float,
    bsr_current: float,
    roi: float,
) -> float:
    movers_score = max(0, 101 - (movers_rank or 999))
    comp_score = competition_score(review_count)
    vel = velocity_score(bsr_avg, bsr_current)
    roi_score = min(100.0, roi / 2)
    return movers_score * 0.30 + comp_score * 0.30 + vel * 0.20 + roi_score * 0.20
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_matching_scoring.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/matching/scoring.py scrapers/tests/unit/test_matching_scoring.py
git commit -m "refactor(scrapers): extract pure scoring module"
```

---

### Task 15: Matching — matcher + summary

**Files:**
- Create: `scrapers/scrapers/matching/matcher.py`
- Test: `scrapers/tests/unit/test_matching_matcher.py`

**Interfaces:**
- Consumes: Task 14 scoring functions; `Settings` (Task 2); `io.load_json` (Task 4).
- Produces: `MatchRecord` dataclass (same 30 fields as current `MatchedProduct`, same order), `MatchSummary` (`marketplace_total: int`, `candidates: list[MatchRecord]`, `winners: list[MatchRecord]`, `near_misses: list[MatchRecord]`, property `high_opportunity -> int`, method `to_dict() -> dict`), `DeodapMatcher(min_confidence=0.5)` with `load_catalog(path)`, `find_matches(products) -> list[MatchRecord]`, `filter_winners(candidates, **kwargs) -> list[MatchRecord]`, `run_matching(settings: Settings) -> MatchSummary` (no IO side effects besides reads; callers write outputs).

- [ ] **Step 1: Write the failing test**

```python
from scrapers.config import Settings
from scrapers.io import atomic_write_json
from scrapers.matching.matcher import DeodapMatcher, MatchSummary, run_matching

CATALOG = [
    {"sku": "SKU1", "title": "Silicone Stretch Lids Set of 12 Reusable Food Covers",
     "cost_price": 65.0, "mrp": 299.0, "moq": 10, "stock": 200, "weight_g": 180,
     "dimensions_cm": "25x20x5", "white_label": True, "gst_compliant": True,
     "images": [], "description": "", "product_url": "https://d.in/p/1"},
]

AMZ = [{"source": "amazon", "asin": "B1",
        "title": "Silicone Stretch Lids Set of 12 Reusable Food Covers",
        "current_price": 199.0, "mrp": 499.0, "review_count": 23, "rating": 4.2,
        "movers_rank": 3, "bsr_current": 1250, "bsr_30d_avg": 1500,
        "seller_count": 3, "fba_seller_count": 1, "product_url": "https://a.in/dp/B1"}]


def test_run_matching_empty_dir(tmp_path):
    summary = run_matching(Settings(output_dir=str(tmp_path)))
    assert isinstance(summary, MatchSummary)
    assert summary.marketplace_total == 0
    assert summary.winners == []


def test_run_matching_finds_candidate(tmp_path):
    atomic_write_json(tmp_path / "deodap_catalog_raw.json", CATALOG)
    atomic_write_json(tmp_path / "amazon_movers_raw.json", AMZ)
    settings = Settings(output_dir=str(tmp_path), min_confidence=0.4,
                        min_absolute_margin=0.0, min_margin_pct=0.0,
                        min_ticket_price=100.0)
    summary = run_matching(settings)
    assert summary.marketplace_total == 1
    assert len(summary.candidates) == 1
    c = summary.candidates[0]
    assert c.marketplace_asin == "B1"
    assert c.deodap_sku == "SKU1"
    assert c.match_confidence > 0.5
    assert summary.high_opportunity >= 0


def test_matcher_filters_by_confidence():
    m = DeodapMatcher(min_confidence=0.9)
    m.deodap_catalog = CATALOG
    matches = m.find_matches([dict(AMZ[0])])
    assert len(m.near_misses) >= 1 or matches == []
    assert all(x.match_confidence >= 0.9 for x in matches)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_matching_matcher.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scrapers/scrapers/matching/matcher.py`**

Port the current `scrapers/matcher.py` logic with the pure functions delegated to `scoring` and `MatchedProduct` renamed `MatchRecord` (same fields, same order). `DeodapMatcher._best_candidate`, `_score_match`, `find_matches`, `filter_winners`, `load_catalog` keep their current bodies but call `calculate_margin`, `opportunity_score`, `is_noise`, `utility_bonus`, `eligible_deodap`, `similarity`, `to_float` from `scrapers.matching.scoring`. Remove all file-write and `print` side effects. Keep `NEAR_MISS_FLOOR = 0.35` and `CSV_COLUMNS` here (reporting imports `CSV_COLUMNS` from here).

`load_catalog` must tolerate a missing file:

```python
def load_catalog(self, filepath: str) -> None:
    self.deodap_catalog = list(load_json(filepath, default=[]))
```

`filter_winners` keeps its current body and signature:

```python
def filter_winners(
    self,
    candidates,
    min_absolute_margin: float = 200.0,
    min_margin_pct: float = 35.0,
    min_ticket_price: float = 300.0,
    max_sellers: int = 5,
    max_fba_sellers: int = 2,
) -> list:
    winners = []
    for m in candidates:
        if m.marketplace_price < min_ticket_price:
            continue
        if m.absolute_margin_inr < min_absolute_margin:
            continue
        if m.margin_percentage < min_margin_pct:
            continue
        if m.seller_count > max_sellers:
            continue
        if m.fba_seller_count > max_fba_sellers:
            continue
        if is_noise(m.marketplace_title):
            continue
        winners.append(m)
    winners.sort(key=lambda m: (utility_bonus(m.marketplace_title), m.opportunity_score), reverse=True)
    return winners
```

Add the module-level runner:

```python
def load_marketplace_products(output_dir: str) -> list:
    products = []
    for filename, source in [
        ("amazon_movers_raw.json", "amazon"),
        ("meesho_trending_raw.json", "meesho"),
        ("flipkart_bestsellers_raw.json", "flipkart"),
    ]:
        path = os.path.join(output_dir, filename)
        batch = list(load_json(path, default=[]))
        for p in batch:
            p["source"] = p.get("source") or source
            if to_float(p.get("current_price")) > 0:
                products.append(p)
    return products


def run_matching(settings) -> MatchSummary:
    matcher = DeodapMatcher(min_confidence=settings.min_confidence)
    matcher.load_catalog(os.path.join(settings.output_dir, "deodap_catalog_raw.json"))
    products = load_marketplace_products(settings.output_dir)
    candidates = matcher.find_matches(products)
    winners = matcher.filter_winners(
        candidates,
        min_absolute_margin=settings.min_absolute_margin,
        min_margin_pct=settings.min_margin_pct,
        min_ticket_price=settings.min_ticket_price,
        max_sellers=settings.max_sellers,
        max_fba_sellers=settings.max_fba_sellers,
    )
    return MatchSummary(
        marketplace_total=len(products),
        candidates=candidates,
        winners=winners,
        near_misses=list(matcher.near_misses),
    )
```

`MatchSummary`:

```python
@dataclass
class MatchSummary:
    marketplace_total: int
    candidates: list
    winners: list
    near_misses: list

    @property
    def high_opportunity(self) -> int:
        return sum(1 for w in self.winners if w.opportunity_score >= 65)

    def to_dict(self) -> dict:
        return {
            "marketplace_total": self.marketplace_total,
            "candidates": [asdict(c) for c in self.candidates],
            "winners": [asdict(w) for w in self.winners],
            "near_misses": [asdict(n) for n in self.near_misses],
            "high_opportunity": self.high_opportunity,
        }
```

Import `os`, `asdict`, `load_json` at the top of the module.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_matching_matcher.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/matching/matcher.py scrapers/tests/unit/test_matching_matcher.py
git commit -m "refactor(scrapers): extract pure matcher with summary"
```

---

### Task 16: Price history + velocity + alerts

**Files:**
- Create: `scrapers/scrapers/matching/history.py`
- Test: `scrapers/tests/unit/test_matching_history.py`

**Interfaces:**
- Consumes: `Settings` (Task 2), `io` (Task 4).
- Produces: `history_path(settings: Settings) -> str`; `collect_raw(products: dict[str, list[dict]], run_ts: str) -> list[dict]` (rows have keys `source, key, ts, price, rating, review_count, stock`); `append_history(path, rows) -> None`; `read_lines(path) -> list[dict]`; `compute_velocity(rows, lookback_days=14) -> dict[str, float]`; `compute_alerts(rows, price_drop_pct=5.0, restock_threshold=20) -> list[dict]`.

- [ ] **Step 1: Write the failing test**

```python
import os

from scrapers.config import Settings
from scrapers.matching.history import (
    collect_raw,
    compute_alerts,
    compute_velocity,
    history_path,
)


def _rows():
    return [
        {"source": "amazon", "key": "B1", "ts": "20260901T000000Z", "price": 200.0,
         "rating": 4.0, "review_count": 10, "stock": None},
        {"source": "amazon", "key": "B1", "ts": "20260914T000000Z", "price": 150.0,
         "rating": 4.2, "review_count": 12, "stock": None},
    ]


def test_collect_raw():
    rows = collect_raw(
        {"amazon": [{"asin": "B1", "current_price": 150.0, "rating": 4.1, "review_count": 5}]},
        "ts1",
    )
    assert rows[0] == {"source": "amazon", "key": "B1", "ts": "ts1", "price": 150.0,
                       "rating": 4.1, "review_count": 5, "stock": None}


def test_velocity_drop():
    assert compute_velocity(_rows())["B1"] == pytest.approx(-25.0, abs=1e-6)


def test_price_drop_alert():
    drops = [a for a in compute_alerts(_rows(), price_drop_pct=5.0) if a["kind"] == "price_drop"]
    assert len(drops) == 1
    assert drops[0]["key"] == "B1"


def test_restock_alert():
    rows = [
        {"source": "deodap", "key": "S1", "ts": "t1", "price": 60.0, "stock": 0},
        {"source": "deodap", "key": "S1", "ts": "t2", "price": 60.0, "stock": 50},
    ]
    assert any(a["kind"] == "restock" for a in compute_alerts(rows, restock_threshold=20))


def test_history_path():
    s = Settings(output_dir="data", history_dir=None)
    assert history_path(s) == os.path.join("data", "products.jsonl")
    s2 = Settings(output_dir="data", history_dir="hist")
    assert history_path(s2) == os.path.join("hist", "products.jsonl")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_matching_history.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scrapers/scrapers/matching/history.py`**

```python
"""Append-only price history, velocity, and change alerts."""
import json
from pathlib import Path
from typing import Dict, List

from scrapers.config import Settings
from scrapers.io import atomic_write_text, ensure_dir


def history_path(settings: Settings) -> str:
    base = settings.history_dir or settings.output_dir
    return str(Path(base) / "products.jsonl")


def collect_raw(products: Dict[str, List[dict]], run_ts: str) -> List[dict]:
    rows = []
    for source, items in products.items():
        for it in items:
            key = it.get("asin") or it.get("product_id") or it.get("sku")
            if not key:
                continue
            price = it.get("cost_price") if source == "deodap" else it.get("current_price")
            rows.append({
                "source": source,
                "key": key,
                "ts": run_ts,
                "price": price,
                "rating": it.get("rating"),
                "review_count": it.get("review_count"),
                "stock": it.get("stock"),
            })
    return rows


def read_lines(path: str) -> List[dict]:
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    try:
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # tolerate corrupt history lines
    except OSError:
        return []
    return rows


def append_history(path: str, rows: List[dict]) -> None:
    if not rows:
        return
    ensure_dir(Path(path).parent)
    existing = read_lines(path)
    combined = existing + rows
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in combined)
    atomic_write_text(path, text)


def compute_velocity(rows: List[dict], lookback_days: int = 14) -> Dict[str, float]:
    by_key: Dict[str, List[dict]] = {}
    for r in rows:
        by_key.setdefault(r["key"], []).append(r)
    result: Dict[str, float] = {}
    for key, group in by_key.items():
        priced = [r for r in group if isinstance(r.get("price"), (int, float))]
        if len(priced) < 2:
            continue
        earliest, latest = priced[0], priced[-1]
        if not earliest.get("price"):
            continue
        change = (latest["price"] - earliest["price"]) / earliest["price"] * 100
        result[key] = round(change, 2)
    return result


def compute_alerts(
    rows: List[dict],
    price_drop_pct: float = 5.0,
    restock_threshold: int = 20,
) -> List[dict]:
    alerts: List[dict] = []
    by_key: Dict[str, List[dict]] = {}
    for r in rows:
        by_key.setdefault(r["key"], []).append(r)
    for key, group in by_key.items():
        priced = [r for r in group if isinstance(r.get("price"), (int, float))]
        if len(priced) >= 2:
            first, last = priced[0], priced[-1]
            if first.get("price") and last.get("price"):
                drop = (first["price"] - last["price"]) / first["price"] * 100
                if drop >= price_drop_pct:
                    alerts.append({"key": key, "kind": "price_drop", "pct": round(drop, 2),
                                   "from": first["price"], "to": last["price"]})
        stocks = [r for r in group if isinstance(r.get("stock"), int)]
        if len(stocks) >= 2:
            first_stock, last_stock = stocks[0]["stock"], stocks[-1]["stock"]
            if first_stock < restock_threshold and last_stock >= restock_threshold:
                alerts.append({"key": key, "kind": "restock", "from": first_stock, "to": last_stock})
    return alerts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_matching_history.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/matching/history.py scrapers/tests/unit/test_matching_history.py
git commit -m "feat(scrapers): add price history, velocity, and alerts"
```

---

### Task 17: Reporting writer (JSON/CSV/Markdown)

**Files:**
- Create: `scrapers/scrapers/reporting/writer.py`
- Test: `scrapers/tests/unit/test_reporting_writer.py`

**Interfaces:**
- Consumes: `MatchRecord`, `MatchSummary` (Task 15); `Settings`; `io`.
- Produces: `CSV_COLUMNS` (exact current list, imported from `scrapers.matching.matcher`), `write_json(path, data)`, `write_csv(path, rows, columns=CSV_COLUMNS)`, `write_winners_markdown(winners, path=None, top_n=25) -> str`, `write_near_misses(path, rows)`, `write_all_outputs(settings, summary) -> dict`.

- [ ] **Step 1: Write the failing test**

```python
import csv
from dataclasses import asdict

from scrapers.config import Settings
from scrapers.io import load_json
from scrapers.matching.matcher import MatchRecord, MatchSummary
from scrapers.reporting.writer import (
    CSV_COLUMNS,
    write_all_outputs,
    write_csv,
    write_winners_markdown,
)


def _make_match() -> MatchRecord:
    kwargs = {name: None for name in MatchRecord.__dataclass_fields__}
    kwargs.update({
        "marketplace": "amazon", "marketplace_asin": "B1",
        "marketplace_title": "Silicone Stretch Lids Set of 12",
        "marketplace_price": 199.0, "marketplace_reviews": 23,
        "deodap_sku": "SKU1", "deodap_title": "Silicone Stretch Lids",
        "deodap_cost": 65.0, "deodap_moq": 10, "deodap_stock": 200,
        "deodap_weight_g": 180, "deodap_white_label": True, "deodap_gst_compliant": True,
        "match_confidence": 0.8, "net_margin_inr": 60.0, "roi_pct": 80.0,
        "absolute_margin_inr": 134.0, "margin_percentage": 206.2, "opportunity_score": 75.0,
        "marketplace_rating": 4.2, "movers_rank": 3, "bsr_current": 1250,
        "seller_count": 3, "fba_seller_count": 1, "weight_g": 180,
    })
    return MatchRecord(**kwargs)


def test_csv_columns_unchanged():
    assert CSV_COLUMNS == [
        "amazon_title", "deodap_sku", "cost", "amazon_price",
        "absolute_margin_inr", "margin_percentage",
    ]


def test_write_csv(tmp_path):
    path = tmp_path / "out.csv"
    write_csv(str(path), [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}], columns=["a", "b"])
    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows == [["a", "b"], ["1", "x"], ["2", "y"]]


def test_markdown_has_header():
    md = write_winners_markdown([])
    assert "Rank" in md
    assert "Opportunity" in md


def test_write_all_outputs(tmp_path):
    s = Settings(output_dir=str(tmp_path / "data"))
    summary = MatchSummary(marketplace_total=1, candidates=[_make_match()],
                           winners=[_make_match()], near_misses=[])
    paths = write_all_outputs(s, summary)
    data = load_json(paths["matched_json"])
    assert data["marketplace_total"] == 1
    assert len(data["winners"]) == 1
    assert paths["matched_json"].endswith("matched_products.json")
    assert paths["markdown"].endswith("winners.md")
    assert (tmp_path / "data" / "matched_products.csv").exists()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_reporting_writer.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scrapers/scrapers/reporting/writer.py`**

```python
"""Result serializers: JSON, CSV (stdlib), and a markdown winners report."""
import csv
import os
from dataclasses import asdict
from typing import List, Optional

from scrapers.config import Settings
from scrapers.io import atomic_write_json, atomic_write_text, ensure_dir
from scrapers.matching.matcher import CSV_COLUMNS, MatchRecord, MatchSummary


def write_json(path: str, data) -> None:
    atomic_write_json(path, data)


def write_csv(path: str, rows: List[dict], columns: Optional[List[str]] = None) -> None:
    columns = columns or CSV_COLUMNS
    ensure_dir(os.path.dirname(os.path.abspath(path)))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([row.get(c, "") for c in columns])


def _winner_row(m: MatchRecord) -> dict:
    return {
        "amazon_title": m.marketplace_title,
        "deodap_sku": m.deodap_sku,
        "cost": m.deodap_cost,
        "amazon_price": m.marketplace_price,
        "absolute_margin_inr": m.absolute_margin_inr,
        "margin_percentage": m.margin_percentage,
    }


def write_winners_markdown(winners: List[MatchRecord], path: Optional[str] = None, top_n: int = 25) -> str:
    lines = [
        "# Matched Product Winners",
        "",
        "> Ranked opportunity report. Thresholds are config-driven (see run manifest).",
        "",
        "| # | Marketplace | Title | DeoDap SKU | Cost | Price | Margin INR | Margin % | Conf | Opp |",
        "|---|-------------|-------|------------|------|-------|-----------|----------|------|-----|",
    ]
    for i, m in enumerate(winners[:top_n], 1):
        lines.append(
            f"| {i} | {m.marketplace} | {m.marketplace_title[:60]} | {m.deodap_sku} "
            f"| ₹{m.deodap_cost} | ₹{m.marketplace_price} | ₹{m.absolute_margin_inr} "
            f"| {m.margin_percentage}% | {m.match_confidence:.0%} | {m.opportunity_score} |"
        )
    md = "\n".join(lines) + "\n"
    if path:
        atomic_write_text(path, md)
    return md


def write_near_misses(path: str, rows: List[dict]) -> None:
    write_json(path, rows)


def write_all_outputs(settings: Settings, summary: MatchSummary) -> dict:
    out = settings.output_dir
    ensure_dir(out)
    paths = {
        "matched_json": os.path.join(out, "matched_products.json"),
        "matched_csv": os.path.join(out, "matched_products.csv"),
        "markdown": os.path.join(out, "winners.md"),
        "near_matches": os.path.join(out, "near_matches.json"),
    }
    write_json(paths["matched_json"], summary.to_dict())
    write_csv(paths["matched_csv"], [_winner_row(w) for w in summary.winners])
    write_winners_markdown(summary.winners, path=paths["markdown"], top_n=settings.report_top_n)
    write_near_misses(paths["near_matches"], [asdict(n) for n in summary.near_misses])
    return paths
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest scrapers/tests/unit/test_reporting_writer.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/reporting/writer.py scrapers/tests/unit/test_reporting_writer.py
git commit -m "feat(scrapers): add csv/json/markdown output writer"
```

---

### Task 18: Optional exports — webhook + sheets

**Files:**
- Create: `scrapers/scrapers/reporting/webhook.py`, `scrapers/scrapers/reporting/sheets.py`
- Test: `scrapers/tests/unit/test_reporting_webhook.py`, `scrapers/tests/unit/test_reporting_sheets.py`

**Interfaces:**
- Consumes: `ExportError` (Task 1), `Settings`.
- Produces: `webhook.build_payload(summary: dict, top_winners: list[dict]) -> dict`; `webhook.sign_payload(body: bytes, secret: str) -> str`; `webhook.post_webhook(url, secret, payload) -> int`; `sheets.export_to_sheets(settings, winners_rows: list[dict]) -> None`.

- [ ] **Step 1: Write the failing test**

```python
import json
from unittest import mock

from scrapers.config import Settings
from scrapers.errors import ExportError
from scrapers.reporting import sheets, webhook


def test_sign_payload():
    sig = webhook.sign_payload(b"body", "secret")
    assert sig.startswith("sha256=")
    assert len(sig) == len("sha256=") + 64


def test_build_payload_limits_winners():
    payload = webhook.build_payload({"winners": 30}, [{"i": n} for n in range(50)])
    assert len(payload["winners"]) == 25


def test_post_webhook_sends_signed_request():
    class FakeResp:
        status = 200

    with mock.patch("urllib.request.urlopen", return_value=FakeResp()) as mocked:
        code = webhook.post_webhook("https://hook.example/x", "secret", {"a": 1})
    req = mocked.call_args[0][0]
    assert code == 200
    assert req.get_header("Content-Type") == "application/json"
    assert req.get_header("X-Pipeline-Signature").startswith("sha256=")
    assert json.loads(req.data) == {"a": 1}


def test_post_webhook_raises_on_failure():
    with mock.patch("urllib.request.urlopen", side_effect=ConnectionError("down")):
        try:
            webhook.post_webhook("https://hook.example/x", "s", {})
        except ExportError:
            pass
        else:
            raise AssertionError("expected ExportError")


def test_sheets_requires_config(tmp_path):
    s = Settings(output_dir=str(tmp_path))
    try:
        sheets.export_to_sheets(s, [])
    except ExportError as exc:
        assert "SHEETS_SERVICE_ACCOUNT" in str(exc)
    else:
        raise AssertionError("expected ExportError")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_reporting_webhook.py scrapers/tests/unit/test_reporting_sheets.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scrapers/scrapers/reporting/webhook.py`**

```python
"""Optional webhook summary push (HMAC-signed)."""
import hashlib
import hmac
import json
from urllib.request import Request, urlopen

from scrapers.errors import ExportError


def sign_payload(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def build_payload(summary: dict, top_winners: list) -> dict:
    return {"summary": summary, "winners": top_winners[:25]}


def post_webhook(url: str, secret: str, payload: dict) -> int:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Pipeline-Signature": sign_payload(body, secret),
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            return response.status
    except Exception as exc:
        raise ExportError(f"webhook POST to {url} failed: {exc}") from exc
```

- [ ] **Step 4: Implement `scrapers/scrapers/reporting/sheets.py`**

```python
"""Optional Google Sheets export of the winners list."""
from scrapers.errors import ExportError


def export_to_sheets(settings, winners_rows: list) -> None:
    if not (settings.sheets_service_account and settings.sheets_spreadsheet_id):
        raise ExportError("sheets export requires SHEETS_SERVICE_ACCOUNT and SHEETS_SPREADSHEET_ID")
    try:
        import gspread
    except ImportError as exc:
        raise ExportError("Google Sheets export requires: pip install -e '.[sheets]'") from exc
    try:
        gc = gspread.service_account(filename=settings.sheets_service_account)
        sheet = gc.open_by_key(settings.sheets_spreadsheet_id).sheet1
        sheet.clear()
        if winners_rows:
            header = list(winners_rows[0].keys())
            sheet.update([header] + [[r.get(c, "") for c in header] for r in winners_rows])
    except Exception as exc:
        raise ExportError(f"google sheets export failed: {exc}") from exc
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest scrapers/tests/unit/test_reporting_webhook.py scrapers/tests/unit/test_reporting_sheets.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scrapers/scrapers/reporting/webhook.py scrapers/scrapers/reporting/sheets.py \
        scrapers/tests/unit/test_reporting_webhook.py scrapers/tests/unit/test_reporting_sheets.py
git commit -m "feat(scrapers): add optional webhook and sheets exports"
```

---

### Task 19: CLI orchestrator

**Files:**
- Rewrite: `scrapers/scrapers/cli.py`
- Test: `scrapers/tests/unit/test_cli.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `main(argv: Optional[list] = None) -> int`; subcommands `run`, `match`, `history`, `export`, `list-sources`, `validate-config`, `scrape-asins`; `run_pipeline(settings, mode, allow_mock_fallback, max_products) -> int`.

Key behavior:
- `run --mock` writes each source's `mock_items` raw, runs matching, history, reports, manifest; returns `0`.
- `run --live` requires scrapling; missing → exit `4` (DependencyError). Source failures → `mock-fallback` if flag set (status recorded, exit `1`), else `failed` (exit `1` if some healthy else `3`).
- Records are validated through `validate_record` before writing; invalid ones are dropped and counted in logs/manifest.
- Unknown source → exit `2` (ConfigError).
- `pipeline run` output-dir override flag is a GLOBAL option placed before the subcommand: `pipeline --output-dir data run --mock`.

- [ ] **Step 1: Write the failing test**

```python
import os
from pathlib import Path

from scrapers.cli import main
from scrapers.io import load_json


def test_list_sources_ok(capsys):
    assert main(["list-sources"]) == 0
    out = capsys.readouterr().out
    assert "amazon" in out and "deodap" in out


def test_validate_config_ok():
    assert main(["validate-config"]) == 0


def test_validate_config_bad_env():
    os.environ["LOG_LEVEL"] = "shouty"
    try:
        assert main(["validate-config"]) == 2
    finally:
        del os.environ["LOG_LEVEL"]


def test_run_mock_e2e(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = str(tmp_path / "data")
    code = main(["--output-dir", out, "run", "--mock",
                 "--sources", "amazon,meesho,flipkart,deodap"])
    assert code == 0
    assert load_json(os.path.join(out, "amazon_movers_raw.json"))
    assert load_json(os.path.join(out, "deodap_catalog_raw.json"))
    assert os.path.exists(os.path.join(out, "matched_products.json"))
    assert os.path.exists(os.path.join(out, "winners.md"))
    runs = list((Path(out) / "runs").iterdir())
    assert len(runs) == 1
    manifest = load_json(runs[0] / "manifest.json")
    assert manifest["mode"] == "mock"
    assert manifest["settings"].get("webhook_secret") in (None, "***")


def test_run_unknown_source_exit2(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--output-dir", str(tmp_path / "d"), "run", "--mock", "--sources", "nope"]) == 2


def test_run_live_without_scrapling_exit4(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--output-dir", str(tmp_path / "d"), "run", "--live", "--sources", "amazon"]) == 4
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest scrapers/tests/unit/test_cli.py -q`
Expected: FAIL (placeholder `cli.py` has no subcommands).

- [ ] **Step 3: Implement `scrapers/scrapers/cli.py`**

```python
"""Pipeline CLI: run, match, history, export, list-sources, validate-config, scrape-asins."""
import argparse
import dataclasses
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

from scrapers import sources  # noqa: F401  (registers built-ins)
from scrapers.config import Settings
from scrapers.errors import ConfigError, DependencyError, PipelineError, SourceError
from scrapers.io import atomic_write_json, ensure_dir, load_json, new_run_id, write_manifest
from scrapers.logging_setup import add_file_handler, setup_logging
from scrapers.metrics import RunMetrics
from scrapers.registry import get_source, list_sources


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pipeline", description="Scrapling e-commerce pipeline")
    parser.add_argument("--env-file", default=None, help="Path to an .env file")
    parser.add_argument("--output-dir", default=None, help="Override OUTPUT_DIR")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Crawl all sources, match, and report")
    p_run.add_argument("--live", action="store_true")
    p_run.add_argument("--mock", action="store_true")
    p_run.add_argument("--sources", default=None, help="Comma-separated source names")
    p_run.add_argument("--max-products", type=int, default=None)
    p_run.add_argument("--allow-mock-fallback", action="store_true")
    p_run.set_defaults(func=_cmd_run)

    sub.add_parser("match", help="Run matching on existing raw data").set_defaults(func=_cmd_match)
    sub.add_parser("history", help="Show price history velocity/alerts").set_defaults(func=_cmd_history)
    sub.add_parser("list-sources", help="List registered sources").set_defaults(func=_cmd_list_sources)
    sub.add_parser("validate-config", help="Validate configuration and exit").set_defaults(func=_cmd_validate)

    p_export = sub.add_parser("export", help="Write reports and optional exports")
    p_export.add_argument("--sheets", action="store_true")
    p_export.add_argument("--webhook", action="store_true")
    p_export.set_defaults(func=_cmd_export)

    p_asins = sub.add_parser("scrape-asins", help="Scrape specific Amazon ASINs (live)")
    p_asins.add_argument("asins", nargs="+")
    p_asins.set_defaults(func=_cmd_scrape_asins)
    return parser


def _settings(args) -> Settings:
    settings = Settings.from_env(env_file=args.env_file)
    if getattr(args, "output_dir", None):
        settings = dataclasses.replace(settings, output_dir=args.output_dir)
    return settings


def _reshape_sources(settings: Settings) -> int:
    """Validate OUTPUT_DIR consistency; returns 0."""
    ensure_dir(settings.output_dir)
    return 0


def _cmd_list_sources(args) -> int:
    for spec in list_sources():
        print(f"{spec.name:<10} {spec.title}  ({len(spec.mock_items)} mock items, out={spec.output_file})")
    return 0


def _cmd_validate(args) -> int:
    try:
        settings = _settings(args)
    except ConfigError as exc:
        print(f"invalid configuration: {exc}", file=sys.stderr)
        return 2
    print(f"configuration OK (log_level={settings.log_level}, log_format={settings.log_format}, "
          f"output_dir={settings.output_dir})")
    return 0


def _resolve_sources(names: List[str]) -> list:
    specs = []
    known = {spec.name for spec in list_sources()}
    for name in names:
        if name not in known:
            raise ConfigError(f"unknown source {name!r}; available: {', '.join(sorted(known))}")
        specs.append(get_source(name))
    return specs


def _crawl_source(spec, settings, mode, allow_mock_fallback, max_products, log):
    from scrapers.sources import base as base_mod

    if mode == "mock":
        return "mock", list(spec.mock_items), None
    try:
        kwargs = spec.build_spider_kwargs(settings)
        if max_products is not None:
            kwargs["max_products"] = max_products
        spider = spec.spider_cls(**kwargs)
        items = base_mod.run_spider(spider)
        return "ok", items, None
    except DependencyError:
        raise
    except SourceError as exc:
        log.warning("source %s failed: %s", spec.name, exc)
        if allow_mock_fallback:
            return "mock-fallback", list(spec.mock_items), "fallback after failure"
        return "failed", [], str(exc)


def _validate_and_count(items: list, source: str) -> list:
    from scrapers.schemas import validate_record

    kept = []
    for item in items:
        record = dict(item)
        record.setdefault("source", source)
        errors = validate_record(record)
        if errors:
            logging.getLogger("scrapers.cli").warning(
                "dropped invalid %s record (%s): %s", source, record.get("asin") or record.get("product_id") or record.get("sku"), errors
            )
            continue
        kept.append(record)
    return kept


def run_pipeline(settings: Settings, mode: str, allow_mock_fallback: bool, max_products: Optional[int]) -> int:
    log = logging.getLogger("scrapers.cli")
    setup_logging(settings.log_level, settings.log_format)
    _reshape_sources(settings)
    run_id = new_run_id()
    log_dir = Path(settings.output_dir) / "runs" / run_id
    ensure_dir(log_dir)
    add_file_handler(str(log_dir / "run.log"))

    from scrapers.matching import history as history_mod
    from scrapers.matching.matcher import run_matching
    from scrapers.reporting.writer import write_all_outputs

    metrics = RunMetrics(mode=mode, started_at=run_id)
    raw_products: dict = {}
    total_invalid = 0

    for spec in _resolve_sources([s.name for s in list_sources()]):
        metric = metrics.for_source(spec.name)
        started = time.perf_counter()
        status, items, note = _crawl_source(spec, settings, mode, allow_mock_fallback, max_products, log)
        metric.status = status
        items = _validate_and_count(items, spec.name) if items else items
        if status == "failed":
            metric.failed = 1
        else:
            metric.scraped = len(items)
            metric.requested = len(items)
            path = os.path.join(settings.output_dir, spec.output_file)
            atomic_write_json(path, items)
            raw_products[spec.name] = items
            log.info("source %s done: status=%s items=%d%s", spec.name, status, len(items), f" ({note})" if note else "")
        metric.elapsed_ms = int((time.perf_counter() - started) * 1000)

    summary = run_matching(settings)
    writes = write_all_outputs(settings, summary)
    hist_path = history_mod.history_path(settings)
    rows = history_mod.collect_raw(raw_products, run_id)
    history_mod.append_history(hist_path, rows)
    all_rows = history_mod.read_lines(hist_path)
    velocity = history_mod.compute_velocity(all_rows)
    alerts = history_mod.compute_alerts(all_rows)

    metrics.finished_at = new_run_id()
    manifest = {
        "run_id": run_id,
        "mode": mode,
        "settings": settings.to_dict(redact=True),
        "metrics": metrics.to_dict(),
        "schema": {"invalid_records_dropped": total_invalid},
        "matching": {
            "marketplace_total": summary.marketplace_total,
            "candidates": len(summary.candidates),
            "winners": len(summary.winners),
            "near_misses": len(summary.near_misses),
            "high_opportunity": summary.high_opportunity,
        },
        "history": {"velocity": velocity, "alerts": alerts},
        "outputs": {key: str(value) for key, value in writes.items()},
        "history_file": hist_path,
    }
    manifest_path = write_manifest(settings.output_dir, run_id, manifest)
    _print_summary(summary, settings)
    log.info("pipeline run finished: run_dir=%s, manifest=%s, exit after mode=%s", run_id, manifest_path, mode)
    return 0 if mode == "mock" else metrics.exit_code()


def _print_summary(summary, settings):
    print("\n" + "=" * 70)
    print(f"MARKETPLACE PRODUCTS: {summary.marketplace_total}")
    print(f"SCORED CANDIDATES:    {len(summary.candidates)}")
    print(f"WINNERS:              {len(summary.winners)}")
    print(f"NEAR MISSES:          {len(summary.near_misses)}")
    print("=" * 70)
    winners = summary.winners
    listing = winners or sorted(summary.candidates, key=lambda m: m.opportunity_score, reverse=True)[:10]
    if not listing:
        print("No candidates matched. Adjust thresholds (MIN_CONFIDENCE, MIN_TICKET_PRICE, ...).")
        return
    for position, m in enumerate(listing, 1):
        tag = "" if m in winners else "  (below threshold)"
        print(
            f"{position:>2}. {m.marketplace_title[:52]:<52} | {m.deodap_sku:<12} | "
            f"₹{m.deodap_cost} -> ₹{m.marketplace_price} | ₹{m.absolute_margin_inr} | "
            f"{m.margin_percentage}% | conf {m.match_confidence:.0%} | opp {m.opportunity_score}{tag}"
        )


def _cmd_run(args) -> int:
    try:
        settings = _settings(args)
        mode = "mock" if args.mock else "live"
        return run_pipeline(settings, mode=mode, allow_mock_fallback=args.allow_mock_fallback,
                            max_products=args.max_products)
    except DependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except (ConfigError, PipelineError) as exc:
        print(f"pipeline error: {exc}", file=sys.stderr)
        return 2


def _cmd_match(args) -> int:
    from scrapers.matching.matcher import run_matching
    from scrapers.reporting.writer import write_all_outputs

    settings = _settings(args)
    setup_logging(settings.log_level, settings.log_format)
    summary = run_matching(settings)
    write_all_outputs(settings, summary)
    _print_summary(summary, settings)
    return 0


def _cmd_history(args) -> int:
    from scrapers.matching.history import compute_alerts, compute_velocity, history_path, read_lines

    settings = _settings(args)
    setup_logging(settings.log_level, settings.log_format)
    path = history_path(settings)
    if not os.path.exists(path):
        print("no history yet; run `pipeline run` first")
        return 0
    rows = read_lines(path)
    print(f"history file: {path} ({len(rows)} rows)")
    print(f"velocity: {compute_velocity(rows)}")
    print(f"alerts:   {compute_alerts(rows)}")
    return 0


def _cmd_export(args) -> int:
    from scrapers.matching.matcher import run_matching
    from scrapers.reporting.writer import write_all_outputs

    settings = _settings(args)
    setup_logging(settings.log_level, settings.log_format)
    summary = run_matching(settings)
    write_all_outputs(settings, summary)
    if args.sheets:
        from scrapers.reporting.sheets import export_to_sheets

        rows = [{
            "amazon_title": m.marketplace_title,
            "deodap_sku": m.deodap_sku,
            "cost": m.deodap_cost,
            "amazon_price": m.marketplace_price,
            "absolute_margin_inr": m.absolute_margin_inr,
            "margin_percentage": m.margin_percentage,
        } for m in summary.winners]
        export_to_sheets(settings, rows)
        print(f"sheets export complete ({len(summary.winners)} winners)")
    if args.webhook:
        from scrapers.reporting.webhook import build_payload, post_webhook

        if not settings.webhook_url or not settings.webhook_secret:
            print("webhook export requires WEBHOOK_URL and WEBHOOK_SECRET", file=sys.stderr)
            return 2
        payload = build_payload(summary.to_dict(), [m.__dict__ for m in summary.winners])
        code = post_webhook(settings.webhook_url, settings.webhook_secret, payload)
        print(f"webhook posted, status={code}")
    return 0


def _cmd_scrape_asins(args) -> int:
    from scrapers.sources.amazon import SEED_FILE, SeedAsinsSpider
    from scrapers.sources.base import run_spider

    settings = _settings(args)
    setup_logging(settings.log_level, settings.log_format)
    spider = SeedAsinsSpider(asins=args.asins, crawldir=settings.crawldir, max_products=0)
    items = run_spider(spider)
    atomic_write_json(os.path.join(settings.output_dir, "amazon_movers_raw.json"), items)
    seed = load_json(str(SEED_FILE), default={}) or {"amazon_movers": {"asins": []}}
    seed.setdefault("amazon_movers", {}).setdefault("asins", [])
    scraped = {str(i["asin"]) for i in items if i.get("asin")}
    seed["amazon_movers"]["asins"] = sorted(set(seed["amazon_movers"]["asins"]) | scraped)
    atomic_write_json(str(SEED_FILE), seed)
    print(f"scraped {len(items)} asins; seed file now has {len(seed['amazon_movers']['asins'])} asins")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return args.func(args)
    except DependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except (ConfigError, PipelineError) as exc:
        print(f"pipeline error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

Consistency notes for the implementer:
- `MatchRecord` is a dataclass, so `m in winners` equality works in `_print_summary`.
- `run_pipeline` iterates `list_sources()` (all 4) when `--sources` is absent because `run` does not parse `--sources` in the default path above — but `_cmd_run` should honor it. Add to `_cmd_run`:

```python
mode = "mock" if args.mock else "live"
names = [n.strip() for n in (args.sources or "").split(",") if n.strip()] if getattr(args, "sources", None) else None
from scrapers.registry import list_sources
specs = _resolve_sources(names) if names else list(list_sources())
```
and pass `specs` into `run_pipeline` (thread it through as a parameter `source_specs: list`). `run_pipeline` then iterates `source_specs` instead of all sources.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest scrapers/tests/unit/test_cli.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/scrapers/cli.py scrapers/tests/unit/test_cli.py
git commit -m "feat(scrapers): add CLI orchestrator with run/match/history/export"
```

---

### Task 20: Docs + full suite + E2E deliverable

**Files:**
- Modify: `scrapers/README.md`, `scrapers/FIND_ASINS.md`
- Create: `scrapers/.gitignore`
- Test: none new (verification + docs)

**Interfaces:**
- Consumes: everything.

- [ ] **Step 1: Rewrite `scrapers/README.md` quickstart**

```markdown
# Scrapers Pipeline (enterprise)

## Install
# core (mock + matching + reports) — pure Python, runs anywhere:
pip install -e .
# live scraping (needs a glibc host, e.g. proot-Distro Ubuntu / macOS):
pip install -e ".[fetchers]"
scrapling install
# dev tooling:
pip install -e ".[dev]"

## Run
pipeline --output-dir data run --mock              # offline E2E using bundled sample catalogs
pipeline run --live                                # live crawl all sources
pipeline run --live --sources amazon,deodap
pipeline run --live --allow-mock-fallback
pipeline match                                    # re-match from existing raw files
pipeline history                                  # price velocity + alerts
pipeline export --webhook --sheets                # pushes reports
pipeline list-sources
pipeline validate-config
pipeline scrape-asins B0XXXXXXXX B0YYYYYYYY       # live; updates seed_asins.json
python -m scrapers.cli run --mock                 # same CLI as a module

## Config
Every environment variable lives in `scrapers/scrapers/config.py`.
`pipeline validate-config` checks your current environment/.env.
Run logs + manifests: `OUTPUT_DIR/runs/<run_id>/`
Products: `OUTPUT_DIR/matched_products.json|.csv`, `winners.md`, `near_matches.json`
Price history + alerts: `OUTPUT_DIR/products.jsonl` (or HISTORY_DIR)
Live fallback: only with `--allow-mock-fallback`; each fallback source is labeled
`mock-fallback` in logs and the run manifest. Never silent.
```

- [ ] **Step 2: Update `scrapers/FIND_ASINS.md`**

Replace `/workspaces/clipbaa/scrapers/seed_asins.json` references with `scrapers/scrapers/sources/seed_asins.json` and replace `python -m scrapers.scrape_asins B0...` with `pipeline scrape-asins B0...`.

- [ ] **Step 3: Create `scrapers/.gitignore`**

```gitignore
data/
.scrapling/
__pycache__/
*.egg-info/
```

- [ ] **Step 4: Full test suite + lint**

```bash
python3 -m pytest scrapers/tests -q
python3 -m flake8 scrapers/scrapers --max-line-length=100
```

Expected: all tests pass; flake8 clean (unused imports and F/E errors introduced by us must be fixed; do not fix pre-existing style in ported files unless it is an error).

- [ ] **Step 5: Run the E2E deliverable**

```bash
pipeline --output-dir data run --mock
pipeline history
pipeline validate-config
```

Collect the printed winners/candidates list.

- [ ] **Step 6: Commit**

```bash
git add scrapers/README.md scrapers/FIND_ASINS.md scrapers/.gitignore
git commit -m "docs(scrapers): update README and ASIN guide for the CLI"
```

---

### Task 21: Hand the products list to the user

- [ ] **Step 1**: Confirm `pipeline --output-dir data run --mock` exited 0 and present in chat the ranked list printed by the CLI (winners, or top candidates flagged `(below threshold)`), plus paths of `matched_products.csv`, `winners.md`, `near_matches.json`, and the run manifest.
- [ ] **Step 2**: Note live steps for the proot-Distro host: clone repo there, `pip install -e ".[fetchers]" && scrapling install`, then `pipeline run --live`.