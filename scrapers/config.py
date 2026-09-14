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
        raise ConfigError("AMAZON_NODE_CATEGORIES must be a JSON object")
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