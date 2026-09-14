import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

try:  # scrapling is only required for live runs
    from scrapling.spiders import Request, Response, Spider
    from scrapling.fetchers import (
        AsyncDynamicSession,
        AsyncStealthySession,
        FetcherSession,
    )

    SPIDERS_OK = True
except ImportError:  # pragma: no cover
    Request = Any
    Response = Any
    Spider = Any
    AsyncDynamicSession = Any
    AsyncStealthySession = Any
    FetcherSession = Any
    SPIDERS_OK = False

__all__ = [
    "Request",
    "Response",
    "Spider",
    "AsyncDynamicSession",
    "AsyncStealthySession",
    "FetcherSession",
]

from scrapers.errors import DependencyError
from scrapers.io import atomic_write_json, load_json
from scrapers.parsing_utils import (
    all_text,
    count_matches,
    first_text,
    full_text,
    has_any_text,
)

DATA_DIR = Path("data")
ADAPTIVE_ENV = "SCRAPLING_ADAPTIVE"
CRAWL_DIR_ENV = "SCRAPLING_CRAWL_DIR"
PROXY_ENV = "SCRAPLING_PROXY"

BLOCKED_STATUS_CODES = {401, 403, 407, 429, 444, 500, 502, 503, 504}
BOT_SIGNATURES = (
    "captcha",
    "unusual traffic",
    "verify you are human",
    "robot check",
    "to discuss automated access",
    "mobile apps and access to our site",
)
BOT_CHALLENGE_SELECTORS = (
    ".g-recaptcha",
    "#captcha",
    "form[action*='captcha']",
    "script[src*='recaptcha']",
    "script[src*='hcaptcha']",
    "iframe[src*='captcha']",
    "iframe[src*='hcaptcha']",
    "img[src*='captcha']",
    "div[data-sitekey]",
)


def adaptive_flags() -> Dict[str, bool]:
    value = os.environ.get(ADAPTIVE_ENV, "").strip().lower()
    enabled = value in {"1", "true", "yes", "on"}
    percentage = int(os.environ.get("SCRAPLING_ADAPTIVE_PERCENTAGE", "40"))
    return {"adaptive": enabled, "auto_save": not enabled, "percentage": percentage}


class MarketplaceSpider(Spider):
    name = "marketplace"
    allowed_domains = set()
    concurrent_requests = 5
    concurrent_requests_per_domain = 0
    download_delay = 1.0
    max_blocked_retries = 3
    autothrottle_enabled = True
    autothrottle_start_delay = 3.0
    autothrottle_max_delay = 30.0

    output_path = "data/raw.json"
    adaptive_domain = ""
    max_products = 50
    enrich = True

    def __init__(
        self,
        crawldir: Optional[str] = None,
        interval: float = 300.0,
        max_products: Optional[int] = None,
    ) -> None:
        if max_products is not None:
            self.max_products = max_products
        super().__init__(crawldir=crawldir, interval=interval)
        self.flags = adaptive_flags()
        self.accepted = 0

    def session_config(self) -> Dict[str, Any]:
        config: Dict[str, Any] = {
            "selector_config": {"adaptive": True, "adaptive_domain": self.adaptive_domain}
        }
        proxy = os.environ.get(PROXY_ENV)
        if proxy:
            config["proxy"] = proxy
        return config

    async def is_blocked(self, response: Response) -> bool:
        if response.status in BLOCKED_STATUS_CODES:
            return True
        for selector in BOT_CHALLENGE_SELECTORS:
            if response.css(selector):
                return True
        title_el = response.css("title").first
        if title_el is not None:
            title = (title_el.text or "").lower()
            if any(sig in title for sig in BOT_SIGNATURES):
                return True
        return False

    async def on_scraped_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not item:
            return None
        self.accepted += 1
        return item

    async def parse(self, response: Response):
        yield None

    def _text(
        self,
        doc: Any,
        identifier: str,
        *selectors: str,
        default: Optional[str] = None,
    ) -> Optional[str]:
        return first_text(doc, selectors, identifier, **self.flags, default=default)

    def _all(self, doc: Any, identifier: str, *selectors: str) -> List[str]:
        return all_text(doc, selectors, identifier, **self.flags)

    def _count(self, doc: Any, selector: str, default: int = 0) -> int:
        return count_matches(doc, selector, default)

    def _body(
        self,
        doc: Any,
        identifier: str,
        *selectors: str,
        default: Optional[str] = None,
    ) -> Optional[str]:
        return full_text(doc, selectors, identifier, **self.flags, default=default)

    def _badge(
        self,
        doc: Any,
        identifier: str,
        selector: str,
        *needles: str,
    ) -> bool:
        return has_any_text(doc, selector, needles, identifier, **self.flags)


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


def dedupe_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep one item per product id, preferring enriched ('full') over list-level ('card') items."""
    best: Dict[str, Dict[str, Any]] = {}
    for item in items:
        pid = item.get("asin") or item.get("product_id") or item.get("sku") or item.get("url")
        if not pid:
            best.setdefault(id(item), item)
            continue
        current = best.get(pid)
        if current is None:
            best[pid] = item
            continue
        if item.get("quality") == "full" and current.get("quality") != "full":
            best[pid] = item
        elif item.get("quality") == "full" and current.get("quality") == "full":
            merged = {**current, **{k: v for k, v in item.items() if v not in (None, "", [], 0)}}
            best[pid] = merged
    return list(best.values())


def write_items(items: List[Dict[str, Any]], output_path: str) -> List[Dict[str, Any]]:
    atomic_write_json(output_path, items)
    print(f"  Saved {len(items)} items to {output_path}")
    return items


def load_items(filepath: str) -> List[Dict[str, Any]]:
    return list(load_json(filepath, default=[]))


def ensure_output_paths(paths: Sequence[str]) -> None:
    for output_path in paths:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)