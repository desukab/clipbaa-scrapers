import os
import re
from dataclasses import asdict, dataclass
from typing import List, Optional

from scrapers.sources.base import AsyncStealthySession, MarketplaceSpider
from scrapers.parsing_utils import (
    extract_product_id,
    parse_dimensions_cm,
    parse_int,
    parse_price,
    parse_rating,
    parse_weight_g,
)


@dataclass
class FlipkartProduct:
    product_id: str
    title: str
    category: str
    current_price: float
    mrp: Optional[float]
    discount_pct: Optional[int]
    review_count: int
    rating: Optional[float]
    order_count: int
    seller_count: int
    fba_seller_count: int
    weight_g: Optional[int]
    dimensions_cm: Optional[str]
    images_count: int
    has_video: bool
    product_url: str


MOCK_FLIPKART_BESTSELLERS = [
    FlipkartProduct(
        product_id="FLIP-KIT-001",
        title="Silicone Stretch Lids 12 Pcs - Reusable Food Covers Microwave Safe",
        category="Kitchen & Dining > Food Storage",
        current_price=185.0,
        mrp=429.0,
        discount_pct=57,
        review_count=234,
        rating=4.4,
        order_count=5670,
        seller_count=8,
        fba_seller_count=3,
        weight_g=180,
        dimensions_cm="25x20x5",
        images_count=6,
        has_video=False,
        product_url="https://www.flipkart.com/p/silicone-stretch-lids"
    ),
    FlipkartProduct(
        product_id="FLIP-OFF-001",
        title="Magnetic Cable Organizer Clips - Set of 6 Strong Magnet Desk Clips",
        category="Electronics > Accessories > Cable Management",
        current_price=145.0,
        mrp=329.0,
        discount_pct=56,
        review_count=189,
        rating=4.3,
        order_count=4320,
        seller_count=6,
        fba_seller_count=2,
        weight_g=60,
        dimensions_cm="10x5x3",
        images_count=5,
        has_video=False,
        product_url="https://www.flipkart.com/p/magnetic-cable-clips"
    ),
    FlipkartProduct(
        product_id="FLIP-BEA-001",
        title="Rose Quartz Gua Sha Facial Tool - Natural Stone Massage Scraper",
        category="Beauty & Personal Care > Skin Care Tools",
        current_price=265.0,
        mrp=589.0,
        discount_pct=55,
        review_count=156,
        rating=4.5,
        order_count=3780,
        seller_count=5,
        fba_seller_count=2,
        weight_g=85,
        dimensions_cm="8x5x1",
        images_count=5,
        has_video=True,
        product_url="https://www.flipkart.com/p/rose-quartz-gua-sha"
    ),
    FlipkartProduct(
        product_id="FLIP-HOM-001",
        title="Drawer Dividers Organizer Set of 4 - Adjustable Expandable",
        category="Home & Furniture > Home Organization",
        current_price=165.0,
        mrp=379.0,
        discount_pct=56,
        review_count=112,
        rating=4.2,
        order_count=2890,
        seller_count=4,
        fba_seller_count=1,
        weight_g=200,
        dimensions_cm="30x10x5",
        images_count=4,
        has_video=False,
        product_url="https://www.flipkart.com/p/drawer-dividers"
    ),
    FlipkartProduct(
        product_id="FLIP-PET-001",
        title="Silicone Dog Lick Mat - Slow Feeder with Suction Cups",
        category="Pet Supplies > Dog Supplies > Feeding",
        current_price=155.0,
        mrp=329.0,
        discount_pct=53,
        review_count=98,
        rating=4.4,
        order_count=2150,
        seller_count=3,
        fba_seller_count=1,
        weight_g=85,
        dimensions_cm="20x20x1",
        images_count=4,
        has_video=False,
        product_url="https://www.flipkart.com/p/silicone-lick-mat"
    ),
]


BESTSELLERS_URL = os.environ.get("FLIPKART_BESTSELLERS_URL", "https://www.flipkart.com/best-sellers")
ADAPTIVE_DOMAIN = "flipkart.com"


def extract_flipkart_pid(url: str) -> Optional[str]:
    product_id = extract_product_id(url, "/p/")
    if product_id:
        return product_id
    match = re.search(r"/p/([a-z0-9]+)", url)
    if match:
        return match.group(1)
    return None


class FlipkartSpider(MarketplaceSpider):
    name = "flipkart_bestsellers"
    allowed_domains = {"flipkart.com"}
    adaptive_domain = ADAPTIVE_DOMAIN
    concurrent_requests = 4
    concurrent_requests_per_domain = 4
    output_path = "data/flipkart_bestsellers_raw.json"

    def configure_sessions(self, manager):
        manager.add(
            "stealth",
            AsyncStealthySession(
                headless=True,
                network_idle=True,
                solve_cloudflare=True,
                max_pages=self.concurrent_requests_per_domain,
                retries=2,
                retry_delay=3,
                **self.session_config(),
            ),
            default=True,
            lazy=True,
        )

    async def start_requests(self):
        yield Request(BESTSELLERS_URL, callback=self.parse_bestsellers)

    async def parse_bestsellers(self, response: Response):
        seen: List[str] = []
        for link in response.css("a[href*='/p/']", "flipkart-product-link", **self.flags):
            href = link.attrib.get("href", "")
            if not href:
                continue
            url = response.urljoin(href)
            product_id = extract_flipkart_pid(url)
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
        product_id = meta.get("product_id") or extract_flipkart_pid(response.url)
        if not product_id:
            self.logger.error("Cannot determine product id for %s", response.url)
            return
        try:
            product = self._parse_product(response, product_id, response.url)
        except Exception as exc:
            self.logger.error("Parse failed for %s: %s", product_id, exc)
            return
        yield asdict(product)

    def _parse_product(self, response: Response, product_id: str, url: str) -> FlipkartProduct:
        title = self._text(response, "flipkart:title", "h1.x-product-title, .product-title, h1") or f"Product {product_id}"
        current_price = parse_price(
            self._text(response, "flipkart:price", '[data-testid="price"]', ".x-price-primary", ".price")
        )
        mrp = parse_price(
            self._text(response, "flipkart:mrp", '[data-testid="mrp"]', ".x-price-mrp", ".mrp")
        )
        discount_pct = None
        if mrp and current_price and mrp > current_price:
            discount_pct = int(round((1 - current_price / mrp) * 100))

        rating = parse_rating(
            self._text(response, "flipkart:rating", '[data-testid="rating"]', ".x-rating", ".rating")
        )
        review_count = parse_int(
            self._text(response, "flipkart:reviews", '[data-testid="review-count"]', ".review-count")
        )
        order_count = parse_int(
            self._text(response, "flipkart:orders", '[data-testid="order-count"]', ".order-count", ".sold")
        )

        images_count = self._count(response, ".product-image img, [data-testid='product-image'] img") or 1
        has_video = bool(response.css(".video-container, [data-testid='video']"))

        weight_g = parse_weight_g(
            self._text(response, "flipkart:weight", '[data-testid="weight"]', ".weight", ".product-weight")
        )
        dimensions_cm = parse_dimensions_cm(
            self._text(response, "flipkart:dimensions", '[data-testid="dimensions"]', ".dimensions")
        )

        seller_count = max(1, self._count(response, ".seller-list .seller, [data-testid='seller']"))
        seller_text = self._body(response, "flipkart:sellers", ".seller-list", '[data-testid="seller-info"]') or ""
        fba_seller_count = 1 if re.search(r"Flipkart Assured|Fulfilled by", seller_text, re.IGNORECASE) else 0

        category = " > ".join(
            self._all(response, "flipkart:breadcrumb", ".breadcrumb a, .category-breadcrumb a", '[data-testid="breadcrumb"] a')[-3:]
        ) or "Unknown"

        return FlipkartProduct(
            product_id=product_id,
            title=title.strip(),
            category=category,
            current_price=current_price or 0.0,
            mrp=mrp,
            discount_pct=discount_pct,
            review_count=review_count,
            rating=rating,
            order_count=order_count,
            seller_count=seller_count,
            fba_seller_count=fba_seller_count,
            weight_g=weight_g,
            dimensions_cm=dimensions_cm,
            images_count=images_count,
            has_video=has_video,
            product_url=url,
        )


def mock_items() -> list:
    return [asdict(p) for p in MOCK_FLIPKART_BESTSELLERS]


if __name__ == "__main__":
    from scrapers.sources.base import run_spider, write_items

    import argparse

    parser = argparse.ArgumentParser(description="Flipkart Bestsellers spider (use `pipeline run` instead)")
    parser.add_argument("--mock", action="store_true", help="Write bundled mock data")
    parser.add_argument("--limit", type=int, default=25, help="Max products")
    args = parser.parse_args()

    if args.mock:
        items = mock_items()[: args.limit]
        write_items(items, "data/flipkart_bestsellers_raw.json")
    else:
        spider = FlipkartSpider(max_products=args.limit)
        items = run_spider(spider)
        write_items(items, "data/flipkart_bestsellers_raw.json")