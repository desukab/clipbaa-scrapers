"""Built-in marketplace sources; importing this module registers them."""
from typing import Any

from scrapers.registry import get_source, list_sources, register_source, SourceSpec
from scrapers.sources.amazon import AmazonMoversSpider, mock_items as amazon_mock
from scrapers.sources.deodap import DeodapSpider, mock_items as deodap_mock
from scrapers.sources.flipkart import FlipkartSpider, mock_items as flipkart_mock
from scrapers.sources.meesho import MeeshoSpider, mock_items as meesho_mock

__all__ = ["SourceSpec", "get_source", "list_sources", "register_source", "register_builtins"]


def _deodap_kwargs(settings: Any) -> dict:
    return {
        "max_products": 0,
        "crawldir": settings.crawldir,
        "categories": list(settings.deodap_categories) or None,
    }


def register_builtins() -> None:
    from scrapers.registry import _SOURCES

    _SOURCES.clear()
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


register_builtins()