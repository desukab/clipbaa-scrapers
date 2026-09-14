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


@dataclass
class MoversProduct:
    asin: str
    title: str
    category: str
    current_price: float
    mrp: Optional[float]
    discount_pct: Optional[int]
    bsr_current: Optional[int]
    bsr_category: Optional[str]
    movers_rank: int
    review_count: int
    rating: Optional[float]
    review_velocity_30d: int
    seller_count: int
    fba_seller_count: int
    weight_g: Optional[int]
    dimensions_cm: Optional[str]
    images_count: int
    has_video: bool
    amazon_choice: bool
    best_seller_badge: bool
    product_url: str


MOCK_AMAZON_MOVERS = [
    MoversProduct(
        asin="B09X7Y6Z5W",
        title="Silicone Stretch Lids Set of 12 - Reusable Food Covers for Bowls, Microwave Safe, BPA Free Kitchen Storage Accessories",
        category="Kitchen > Storage & Organization > Food Storage",
        current_price=199.0,
        mrp=499.0,
        discount_pct=60,
        bsr_current=1250,
        bsr_category="Kitchen",
        movers_rank=3,
        review_count=23,
        rating=4.2,
        review_velocity_30d=8,
        seller_count=3,
        fba_seller_count=1,
        weight_g=180,
        dimensions_cm="25x20x5",
        images_count=6,
        has_video=False,
        amazon_choice=True,
        best_seller_badge=False,
        product_url="https://www.amazon.in/dp/B09X7Y6Z5W"
    ),
    MoversProduct(
        asin="B08V5T4R3Q",
        title="Stainless Steel Garlic Press - Professional Chef Grade with Cleaning Tool, Dishwasher Safe",
        category="Kitchen > Tools & Gadgets > Garlic Presses",
        current_price=249.0,
        mrp=599.0,
        discount_pct=58,
        bsr_current=2100,
        bsr_category="Kitchen",
        movers_rank=7,
        review_count=41,
        rating=4.4,
        review_velocity_30d=12,
        seller_count=4,
        fba_seller_count=2,
        weight_g=220,
        dimensions_cm="18x6x4",
        images_count=5,
        has_video=True,
        amazon_choice=False,
        best_seller_badge=True,
        product_url="https://www.amazon.in/dp/B08V5T4R3Q"
    ),
    MoversProduct(
        asin="B07K9L8M7N",
        title="Herb Scissors 5-Blade with Cleaning Comb - Multipurpose Kitchen Scissors for Herbs, Vegetables",
        category="Kitchen > Tools & Gadgets > Herb Tools",
        current_price=179.0,
        mrp=399.0,
        discount_pct=55,
        bsr_current=890,
        bsr_category="Kitchen",
        movers_rank=2,
        review_count=18,
        rating=4.1,
        review_velocity_30d=6,
        seller_count=2,
        fba_seller_count=1,
        weight_g=95,
        dimensions_cm="20x8x2",
        images_count=4,
        has_video=False,
        amazon_choice=True,
        best_seller_badge=False,
        product_url="https://www.amazon.in/dp/B07K9L8M7N"
    ),
    MoversProduct(
        asin="B06J5H4G3F",
        title="Magnetic Cable Organizer Clips Set of 6 - Strong Magnetic Cable Management for Desk",
        category="Electronics > Accessories > Cable Management",
        current_price=149.0,
        mrp=349.0,
        discount_pct=57,
        bsr_current=3200,
        bsr_category="Electronics",
        movers_rank=12,
        review_count=35,
        rating=4.3,
        review_velocity_30d=10,
        seller_count=5,
        fba_seller_count=2,
        weight_g=60,
        dimensions_cm="10x5x3",
        images_count=5,
        has_video=False,
        amazon_choice=False,
        best_seller_badge=False,
        product_url="https://www.amazon.in/dp/B06J5H4G3F"
    ),
    MoversProduct(
        asin="B05D4C3B2A",
        title="Monitor Light Bar - USB Powered Screen Light with Touch Dimmer, Auto-off Timer",
        category="Electronics > Computer Accessories > Monitor Lights",
        current_price=299.0,
        mrp=799.0,
        discount_pct=63,
        bsr_current=4500,
        bsr_category="Electronics",
        movers_rank=18,
        review_count=27,
        rating=4.5,
        review_velocity_30d=9,
        seller_count=3,
        fba_seller_count=1,
        weight_g=320,
        dimensions_cm="42x3x2",
        images_count=6,
        has_video=True,
        amazon_choice=True,
        best_seller_badge=False,
        product_url="https://www.amazon.in/dp/B05D4C3B2A"
    ),
    MoversProduct(
        asin="B04F3E2D1C",
        title="Rose Quartz Gua Sha Facial Massage Tool - Authentic Stone with Storage Pouch",
        category="Beauty > Tools & Accessories > Facial Tools",
        current_price=279.0,
        mrp=699.0,
        discount_pct=60,
        bsr_current=1800,
        bsr_category="Beauty",
        movers_rank=5,
        review_count=31,
        rating=4.6,
        review_velocity_30d=11,
        seller_count=4,
        fba_seller_count=2,
        weight_g=85,
        dimensions_cm="8x5x1",
        images_count=5,
        has_video=False,
        amazon_choice=True,
        best_seller_badge=False,
        product_url="https://www.amazon.in/dp/B04F3E2D1C"
    ),
    MoversProduct(
        asin="B03A2B1C9D",
        title="Stainless Steel Blackhead Remover Kit - 4 Piece Professional Extraction Tools",
        category="Beauty > Tools & Accessories > Blemish Extractors",
        current_price=199.0,
        mrp=449.0,
        discount_pct=56,
        bsr_current=2500,
        bsr_category="Beauty",
        movers_rank=9,
        review_count=44,
        rating=4.2,
        review_velocity_30d=13,
        seller_count=6,
        fba_seller_count=3,
        weight_g=90,
        dimensions_cm="15x8x2",
        images_count=4,
        has_video=False,
        amazon_choice=False,
        best_seller_badge=False,
        product_url="https://www.amazon.in/dp/B03A2B1C9D"
    ),
    MoversProduct(
        asin="B02Z1Y0X9W",
        title="Packing Cubes Set of 6 - Water Resistant Nylon Travel Organizer with Mesh Tops",
        category="Travel > Accessories > Packing Organizers",
        current_price=289.0,
        mrp=699.0,
        discount_pct=59,
        bsr_current=3800,
        bsr_category="Travel",
        movers_rank=15,
        review_count=29,
        rating=4.4,
        review_velocity_30d=8,
        seller_count=4,
        fba_seller_count=1,
        weight_g=280,
        dimensions_cm="35x25x8",
        images_count=6,
        has_video=False,
        amazon_choice=False,
        best_seller_badge=False,
        product_url="https://www.amazon.in/dp/B02Z1Y0X9W"
    ),
    MoversProduct(
        asin="B01V8U7T6S",
        title="Drawer Dividers Adjustable - Set of 4 Expandable Drawer Organizers for Clothes",
        category="Home & Kitchen > Storage & Organization > Drawer Organizers",
        current_price=169.0,
        mrp=399.0,
        discount_pct=58,
        bsr_current=1100,
        bsr_category="Home & Kitchen",
        movers_rank=4,
        review_count=21,
        rating=4.3,
        review_velocity_30d=7,
        seller_count=3,
        fba_seller_count=1,
        weight_g=200,
        dimensions_cm="30x10x5",
        images_count=5,
        has_video=False,
        amazon_choice=True,
        best_seller_badge=False,
        product_url="https://www.amazon.in/dp/B01V8U7T6S"
    ),
    MoversProduct(
        asin="B00Q9P8O7N",
        title="Silicone Lick Mat for Dogs - Slow Feeder Textured Mat with Suction Cups",
        category="Pet Supplies > Dog Supplies > Feeding Accessories",
        current_price=159.0,
        mrp=349.0,
        discount_pct=54,
        bsr_current=2200,
        bsr_category="Pet Supplies",
        movers_rank=11,
        review_count=38,
        rating=4.5,
        review_velocity_30d=14,
        seller_count=2,
        fba_seller_count=1,
        weight_g=85,
        dimensions_cm="20x20x1",
        images_count=4,
        has_video=False,
        amazon_choice=False,
        best_seller_badge=False,
        product_url="https://www.amazon.in/dp/B00Q9P8O7N"
    ),
]


MOVERS_URL = os.environ.get("AMAZON_MOVERS_URL", "https://www.amazon.in/gp/movers-and-shakers")
DEFAULT_BESTSELLERS = [
    "https://www.amazon.in/bestsellers/kitchen",
    "https://www.amazon.in/gp/bestsellers/kitchen/1380510031",
    "https://www.amazon.in/gp/bestsellers/kitchen/1380374031",
    "https://www.amazon.in/gp/bestsellers/kitchen/1380181031",
    "https://www.amazon.in/gp/bestsellers/kitchen/1379989031",
]
BESTSELLERS_URLS = [
    u.strip()
    for u in os.environ.get("AMAZON_BESTSELLERS_URLS", ",".join(DEFAULT_BESTSELLERS)).split(",")
    if u.strip()
]
NODE_CATEGORIES = {
    "1380510031": "home-storage",
    "1380374031": "home-decor",
    "1380181031": "kitchen-tools",
    "1379989031": "kitchen-storage",
}
SEED_FILE = Path(__file__).parent / "seed_asins.json"


def category_for_url(url: str) -> str:
    node = re.search(r"/bestsellers/kitchen/(\d+)", url)
    if node:
        return NODE_CATEGORIES.get(node.group(1), "kitchen")
    if "bestsellers/kitchen" in url or "movers-and-shakers" in url:
        return "kitchen"
    return "amazon"
ADAPTIVE_DOMAIN = "amazon.in"


def load_seed_asins() -> List[str]:
    if not SEED_FILE.exists():
        return []
    try:
        with open(SEED_FILE) as handle:
            data = json.load(handle)
        asins = data.get("amazon_movers", {}).get("asins", [])
        if asins:
            print(f"  Loaded {len(asins)} seed ASINs by SeedAsinsSpider")
        return asins
    except Exception as e:
        print(f"  [WARN] Failed to load seed ASINs: {e}")
        return []


def extract_asin(url: str) -> Optional[str]:
    asin = extract_product_id(url, "/dp/")
    return asin if asin and re.fullmatch(r"B0[A-Z0-9]{8}", asin) else None


class AmazonMoversSpider(MarketplaceSpider):
    name = "amazon_movers"
    allowed_domains = {"amazon.in"}
    adaptive_domain = ADAPTIVE_DOMAIN
    concurrent_requests = 5
    concurrent_requests_per_domain = 5
    output_path = "data/amazon_movers_raw.json"

    def configure_sessions(self, manager):
        manager.add(
            "stealth",
            AsyncStealthySession(
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
        for url in BESTSELLERS_URLS:
            yield Request(url, callback=self.parse_list, meta={"list_url": url})

    async def parse_list(self, response: Response):
        cards = response.css("div[data-asin]", "amazon-asin-card", **self.flags)
        if not cards:
            self.logger.warning("No product cards found on %s", response.url)
            return
        self.logger.info("Found %d product cards", len(cards))
        for card in cards[: self.max_products]:
            asin = (card.attrib.get("data-asin") or "").strip()
            if not asin or not re.fullmatch(r"B0[A-Z0-9]{8}", asin):
                continue
            card_item = self._parse_card(card, asin, response)
            card_item["quality"] = "card"
            yield card_item
            if self.enrich and card_item.get("product_url"):
                yield Request(
                    f"https://www.amazon.in/dp/{asin}",
                    callback=self.parse_product,
                    meta={"asin": asin, "rank": card_item.get("movers_rank", 0)},
                )

    def _parse_card(self, card: Any, asin: str, response: Response) -> dict:
        rank_el = card.css(".zg-bdg-text").first
        title_el = card.css("._cDEzb_p13n-sc-css-line-clamp-3_g3dy1").first
        price_el = card.css(".a-price .a-offscreen, ._cDEzb_p13n-sc-price_3mJ9Z").first
        rating_el = card.css(".a-icon-row .a-icon-alt").first
        review_el = card.css(".a-icon-row .a-size-small").first
        link_el = card.css('a[href*="/dp/"]').first

        url = ""
        if link_el is not None:
            href = link_el.attrib.get("href", "")
            url = "https://www.amazon.in" + href if href.startswith("/") else href

        return {
            "asin": asin,
            "title": (title_el.text or "").strip() if title_el else f"Product {asin}",
            "current_price": parse_price(price_el.text) if price_el else None,
            "mrp": None,
            "discount_pct": None,
            "rating": parse_rating(rating_el.text) if rating_el else None,
            "review_count": parse_int(review_el.text, 0) if review_el else 0,
            "movers_rank": parse_int(rank_el.text, 0) if rank_el else 0,
            "bsr_current": None,
            "bsr_category": None,
            "category": category_for_url(response.url),
            "seller_count": 0,
            "fba_seller_count": None,
            "weight_g": None,
            "dimensions_cm": None,
            "images_count": 0,
            "has_video": False,
            "amazon_choice": False,
            "best_seller_badge": False,
            "product_url": url,
            "source": "amazon_bestsellers",
        }

    async def parse(self, response: Response):
        async for item in self.parse_product(response):
            yield item

    async def parse_product(self, response: Response):
        meta = response.request.meta if response.request else {}
        asin = meta.get("asin") or extract_asin(response.url)
        if not asin:
            self.logger.error("Cannot determine ASIN for %s", response.url)
            return
        try:
            product = self._parse_product(response, asin, meta.get("rank", 0), response.url)
        except Exception as exc:
            self.logger.error("Parse failed for %s: %s", asin, exc)
            return
        if not product.current_price and (not product.title or product.title.startswith("Product ")):
            self.logger.info("Empty enrichment for %s; keeping card data", asin)
            return
        item = asdict(product)
        item["quality"] = "full"
        yield item

    def _parse_product(self, response: Response, asin: str, rank: int, url: str) -> MoversProduct:
        title = self._text(response, "amazon:title", "#productTitle") or f"Product {asin}"
        current_price = parse_price(
            self._text(response, "amazon:price", ".a-price .a-offscreen", "#priceblock_ourprice", "#priceblock_dealprice")
        )
        mrp = parse_price(
            self._text(response, "amazon:mrp", ".a-text-price .a-offscreen", "#listPrice")
        )
        discount_pct = None
        if mrp and current_price and mrp > current_price:
            discount_pct = int(round((1 - current_price / mrp) * 100))

        rating = parse_rating(
            self._text(response, "amazon:rating", "#averageCustomerReviews .a-icon-alt", '[data-hook="rating-out-of-text"]')
        )
        review_count = parse_int(
            self._text(response, "amazon:reviews", "#acrCustomerReviewText"), 0
        )

        detail_text = self._body(
            response, "amazon:details", "#detailBullets_feature_div", "#productDetails_detailBullets_sections1"
        ) or ""
        bsr_current, bsr_category = parse_bsr(detail_text)
        weight_g = parse_weight_g(detail_text)
        dimensions_cm = parse_dimensions_cm(detail_text)

        category = " > ".join(
            self._all(response, "amazon:breadcrumb", "#wayfinding-breadcrumbs_feature_div a", "#nav-breadcrumbs a")[-3:]
        ) or "Unknown"

        images_count = self._count(response, "#altImages img, #imgTagWrapperId img") or 1
        has_video = bool(response.css("#videoTab_feature_div, .video-container, #video-content"))
        amazon_choice = bool(response.css("#acBadge"))
        best_seller_badge = self._badge(response, "amazon:badge", ".a-badge-text", "Best Seller")

        if "Fulfilled by Amazon" in detail_text or "fulfilled by amazon" in detail_text.lower():
            fba_seller_count = 1
        elif response.css("#merchantInfoFeature_feature_div, a[href*='seller=']"):
            fba_seller_count = 1
        else:
            fba_seller_count = 0
        seller_count = 1

        review_velocity_30d = max(1, review_count // 10) if review_count else 0

        return MoversProduct(
            asin=asin,
            title=title.strip(),
            category=category,
            current_price=current_price or 0.0,
            mrp=mrp,
            discount_pct=discount_pct,
            bsr_current=bsr_current,
            bsr_category=bsr_category,
            movers_rank=rank,
            review_count=review_count,
            rating=rating,
            review_velocity_30d=review_velocity_30d,
            seller_count=seller_count,
            fba_seller_count=fba_seller_count,
            weight_g=weight_g,
            dimensions_cm=dimensions_cm,
            images_count=images_count,
            has_video=has_video,
            amazon_choice=amazon_choice,
            best_seller_badge=best_seller_badge,
            product_url=url,
        )


class SeedAsinsSpider(AmazonMoversSpider):
    name = "amazon_seed_asins"

    def __init__(self, asins: List[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self.target_asins = asins

    async def start_requests(self):
        for rank, asin in enumerate(self.target_asins, 1):
            yield Request(
                f"https://www.amazon.in/dp/{asin}",
                callback=self.parse_product,
                meta={"asin": asin, "rank": rank},
            )


def mock_items() -> list:
    return [asdict(p) for p in MOCK_AMAZON_MOVERS]


if __name__ == "__main__":
    from scrapers.sources.base import run_spider, write_items

    import argparse

    parser = argparse.ArgumentParser(description="Amazon Movers & Shakers spider (use `pipeline run` instead)")
    parser.add_argument("--mock", action="store_true", help="Write bundled mock data")
    parser.add_argument("--limit", type=int, default=50, help="Max products per category")
    args = parser.parse_args()

    if args.mock:
        items = mock_items()[: args.limit]
        write_items(items, "data/amazon_movers_raw.json")
    else:
        spider = AmazonMoversSpider(max_products=args.limit)
        items = run_spider(spider)
        write_items(items, "data/amazon_movers_raw.json")