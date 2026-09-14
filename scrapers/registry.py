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