import os
from dataclasses import asdict, dataclass
from typing import List, Optional

from scrapers.sources.base import AsyncDynamicSession, MarketplaceSpider
from scrapers.parsing_utils import (
    extract_product_id,
    parse_int,
    parse_price,
    parse_rating,
    parse_weight_g,
)


@dataclass
class MeeshoProduct:
    product_id: str
    title: str
    category: str
    current_price: float
    mrp: Optional[float]
    discount_pct: Optional[int]
    review_count: int
    rating: Optional[float]
    order_count: int
    images_count: int
    weight_g: Optional[int]
    product_url: str
    supplier_id: Optional[str]


MOCK_MEESHO_TRENDING = [
    MeeshoProduct(
        product_id="MEESHO-KIT-001",
        title="Silicone Stretch Lids Set of 12 - Reusable Food Storage Covers",
        category="Kitchen & Dining > Storage",
        current_price=189.0,
        mrp=449.0,
        discount_pct=58,
        review_count=156,
        rating=4.3,
        order_count=2340,
        images_count=5,
        weight_g=180,
        product_url="https://www.meesho.com/product/silicone-stretch-lids",
        supplier_id="SUP-KIT-001"
    ),
    MeeshoProduct(
        product_id="MEESHO-KIT-002",
        title="Stainless Steel Garlic Press - Heavy Duty Kitchen Tool",
        category="Kitchen & Dining > Tools",
        current_price=229.0,
        mrp=499.0,
        discount_pct=54,
        review_count=89,
        rating=4.2,
        order_count=1120,
        images_count=4,
        weight_g=220,
        product_url="https://www.meesho.com/product/garlic-press",
        supplier_id="SUP-KIT-002"
    ),
    MeeshoProduct(
        product_id="MEESHO-OFF-001",
        title="Magnetic Cable Clips Organizer Set of 6 - Desk Cable Management",
        category="Electronics > Accessories",
        current_price=139.0,
        mrp=299.0,
        discount_pct=54,
        review_count=203,
        rating=4.4,
        order_count=3450,
        images_count=5,
        weight_g=60,
        product_url="https://www.meesho.com/product/magnetic-cable-clips",
        supplier_id="SUP-OFF-001"
    ),
    MeeshoProduct(
        product_id="MEESHO-BEA-001",
        title="Rose Quartz Gua Sha & Facial Roller Set - Natural Stone",
        category="Beauty & Personal Care > Tools",
        current_price=259.0,
        mrp=599.0,
        discount_pct=57,
        review_count=178,
        rating=4.5,
        order_count=2890,
        images_count=6,
        weight_g=150,
        product_url="https://www.meesho.com/product/rose-quartz-gua-sha",
        supplier_id="SUP-BEA-001"
    ),
    MeeshoProduct(
        product_id="MEESHO-TRV-001",
        title="Packing Cubes Travel Organizer Set of 6 - Lightweight Nylon",
        category="Travel > Luggage Accessories",
        current_price=269.0,
        mrp=599.0,
        discount_pct=55,
        review_count=134,
        rating=4.3,
        order_count=1780,
        images_count=5,
        weight_g=280,
        product_url="https://www.meesho.com/product/packing-cubes",
        supplier_id="SUP-TRV-001"
    ),
    MeeshoProduct(
        product_id="MEESHO-HOM-001",
        title="Adjustable Drawer Dividers Organizer Set of 4 - Expandable",
        category="Home & Kitchen > Organization",
        current_price=159.0,
        mrp=349.0,
        discount_pct=54,
        review_count=92,
        rating=4.2,
        order_count=1450,
        images_count=4,
        weight_g=200,
        product_url="https://www.meesho.com/product/drawer-dividers",
        supplier_id="SUP-HOM-001"
    ),
]


TRENDING_URL = os.environ.get("MEESHO_TRENDING_URL", "https://www.meesho.com/trending")
ADAPTIVE_DOMAIN = "meesho.com"


def extract_meesho_pid(url: str) -> Optional[str]:
    return extract_product_id(url, "/p/")


class MeeshoSpider(MarketplaceSpider):
    name = "meesho_trending"
    allowed_domains = {"meesho.com"}
    adaptive_domain = ADAPTIVE_DOMAIN
    concurrent_requests = 4
    concurrent_requests_per_domain = 4
    output_path = "data/meesho_trending_raw.json"

    def configure_sessions(self, manager):
        manager.add(
            "dynamic",
            AsyncDynamicSession(
                headless=True,
                network_idle=True,
                max_pages=self.concurrent_requests_per_domain,
                retries=2,
                retry_delay=3,
                **self.session_config(),
            ),
            default=True,
            lazy=True,
        )

    async def start_requests(self):
        yield Request(TRENDING_URL, callback=self.parse_trending)

    async def parse_trending(self, response: Response):
        seen: List[str] = []
        for link in response.css("a[href*='/p/']", "meesho-product-link", **self.flags):
            href = link.attrib.get("href", "")
            if not href:
                continue
            url = response.urljoin(href)
            product_id = extract_meesho_pid(url)
            if not product_id or product_id in seen:
                continue
            seen.append(product_id)
            yield Request(url, callback=self.parse_product, meta={"product_id": product_id})
            if len(seen) >= self.max_products:
                break

    async def parse(self, response: Response):
        async for item in self.parse_product(response):
            yield item

    async def parse_product(self, response: Response):
        meta = response.request.meta if response.request else {}
        product_id = meta.get("product_id") or extract_meesho_pid(response.url)
        if not product_id:
            self.logger.error("Cannot determine product id for %s", response.url)
            return
        try:
            product = self._parse_product(response, product_id, response.url)
        except Exception as exc:
            self.logger.error("Parse failed for %s: %s", product_id, exc)
            return
        yield asdict(product)

    def _parse_product(self, response: Response, product_id: str, url: str) -> MeeshoProduct:
        title = self._text(
            response,
            "meesho:title",
            'h1[data-testid="product-title"]',
            ".product-title",
            "h1",
        ) or f"Product {product_id}"
        current_price = parse_price(
            self._text(response, "meesho:price", '[data-testid="product-price"]', ".product-price", ".price")
        )
        mrp = parse_price(
            self._text(response, "meesho:mrp", '[data-testid="product-mrp"]', ".mrp", ".original-price")
        )
        discount_pct = None
        if mrp and current_price and mrp > current_price:
            discount_pct = int(round((1 - current_price / mrp) * 100))

        rating = parse_rating(
            self._text(response, "meesho:rating", '[data-testid="rating"]', ".rating-value")
        )
        review_count = parse_int(
            self._text(response, "meesho:reviews", '[data-testid="review-count"]', ".review-count")
        )
        order_count = parse_int(
            self._text(response, "meesho:orders", '[data-testid="order-count"]', ".order-count", ".sold-count")
        )

        images_count = self._count(response, ".product-image img, [data-testid='product-image'] img") or 1
        weight_g = parse_weight_g(
            self._text(response, "meesho:weight", '[data-testid="weight"]', ".weight")
        )

        supplier_id = None
        supplier_link = response.css("a[href*='/supplier/']", "meesho-supplier").first
        if supplier_link is not None:
            href = supplier_link.attrib.get("href", "")
            if "/supplier/" in href:
                candidate = href.split("/supplier/")[-1].split("?")[0].strip("/")
                if candidate:
                    supplier_id = candidate

        category = " > ".join(
            self._all(
                response,
                "meesho:breadcrumb",
                ".breadcrumb a",
                ".category-breadcrumb a",
                'nav[aria-label="breadcrumb"] a',
            )[-3:]
        ) or "Unknown"

        return MeeshoProduct(
            product_id=product_id,
            title=title.strip(),
            category=category,
            current_price=current_price or 0.0,
            mrp=mrp,
            discount_pct=discount_pct,
            review_count=review_count,
            rating=rating,
            order_count=order_count,
            images_count=images_count,
            weight_g=weight_g,
            product_url=url,
            supplier_id=supplier_id,
        )


def mock_items() -> list:
    return [asdict(p) for p in MOCK_MEESHO_TRENDING]


if __name__ == "__main__":
    from scrapers.sources.base import run_spider, write_items

    import argparse

    parser = argparse.ArgumentParser(description="Meesho Trending spider (use `pipeline run` instead)")
    parser.add_argument("--mock", action="store_true", help="Write bundled mock data")
    parser.add_argument("--limit", type=int, default=30, help="Max products")
    args = parser.parse_args()

    if args.mock:
        items = mock_items()[: args.limit]
        write_items(items, "data/meesho_trending_raw.json")
    else:
        spider = MeeshoSpider(max_products=args.limit)
        items = run_spider(spider)
        write_items(items, "data/meesho_trending_raw.json")