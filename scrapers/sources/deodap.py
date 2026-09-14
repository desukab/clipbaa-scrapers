import os
import re
from dataclasses import asdict, dataclass
from typing import List, Optional

from scrapers.parsing_utils import extract_product_id
from scrapers.sources.base import FetcherSession, MarketplaceSpider


@dataclass
class DeodapProduct:
    sku: str
    title: str
    category: str
    cost_price: float
    mrp: float
    moq: int
    stock: int
    weight_g: int
    dimensions_cm: str
    white_label: bool
    gst_compliant: bool
    images: List[str]
    description: str
    product_url: str


MOCK_DEODAP_CATALOG = [
    DeodapProduct(
        sku="DEODAP-KIT-001",
        title="Silicone Stretch Lids Set of 12 - Reusable Food Covers",
        category="kitchen-tools",
        cost_price=65.0,
        mrp=299.0,
        moq=10,
        stock=200,
        weight_g=180,
        dimensions_cm="25x20x5",
        white_label=True,
        gst_compliant=True,
        images=[],
        description="Set of 12 silicone stretch lids in various sizes. BPA free, microwave safe.",
        product_url="https://deodap.com/product/silicone-stretch-lids",
    ),
    DeodapProduct(
        sku="DEODAP-KIT-002",
        title="Stainless Steel Garlic Press - Professional Chef Grade",
        category="kitchen-tools",
        cost_price=85.0,
        mrp=349.0,
        moq=10,
        stock=150,
        weight_g=220,
        dimensions_cm="18x6x4",
        white_label=True,
        gst_compliant=True,
        images=[],
        description="Heavy duty garlic press with cleaning tool. Dishwasher safe.",
        product_url="https://deodap.com/product/garlic-press",
    ),
    DeodapProduct(
        sku="DEODAP-KIT-003",
        title="Herb Scissors 5-Blade with Cleaning Comb",
        category="kitchen-tools",
        cost_price=55.0,
        mrp=249.0,
        moq=15,
        stock=300,
        weight_g=95,
        dimensions_cm="20x8x2",
        white_label=True,
        gst_compliant=True,
        images=[],
        description="5-blade herb scissors for fast chopping. Includes cleaning comb.",
        product_url="https://deodap.com/product/herb-scissors",
    ),
    DeodapProduct(
        sku="DEODAP-OFF-001",
        title="Magnetic Cable Organizer Clips Set of 6",
        category="office-accessories",
        cost_price=45.0,
        mrp=199.0,
        moq=20,
        stock=500,
        weight_g=60,
        dimensions_cm="10x5x3",
        white_label=True,
        gst_compliant=True,
        images=[],
        description="Strong magnetic cable clips for desk organization. Holds 6 cables.",
        product_url="https://deodap.com/product/magnetic-cable-clips",
    ),
    DeodapProduct(
        sku="DEODAP-OFF-002",
        title="Monitor Light Bar - USB Powered Screen Light",
        category="office-accessories",
        cost_price=180.0,
        mrp=699.0,
        moq=5,
        stock=80,
        weight_g=320,
        dimensions_cm="42x3x2",
        white_label=True,
        gst_compliant=True,
        images=[],
        description="Asymmetric screen light bar. Touch dimmer, auto-off timer.",
        product_url="https://deodap.com/product/monitor-light-bar",
    ),
    DeodapProduct(
        sku="DEODAP-OFF-003",
        title="Foldable Phone Stand - Adjustable Angle Aluminum",
        category="office-accessories",
        cost_price=75.0,
        mrp=299.0,
        moq=10,
        stock=250,
        weight_g=150,
        dimensions_cm="12x10x2",
        white_label=True,
        gst_compliant=True,
        images=[],
        description="Multi-angle aluminum phone stand. Folds flat for travel.",
        product_url="https://deodap.com/product/foldable-phone-stand",
    ),
    DeodapProduct(
        sku="DEODAP-BEA-001",
        title="Rose Quartz Gua Sha Facial Massage Tool",
        category="beauty-tools",
        cost_price=95.0,
        mrp=399.0,
        moq=10,
        stock=180,
        weight_g=85,
        dimensions_cm="8x5x1",
        white_label=True,
        gst_compliant=True,
        images=[],
        description="Authentic rose quartz gua sha. Includes storage pouch.",
        product_url="https://deodap.com/product/rose-quartz-gua-sha",
    ),
    DeodapProduct(
        sku="DEODAP-BEA-002",
        title="Stainless Steel Blackhead Remover Kit - 4 Pieces",
        category="beauty-tools",
        cost_price=55.0,
        mrp=249.0,
        moq=15,
        stock=400,
        weight_g=90,
        dimensions_cm="15x8x2",
        white_label=True,
        gst_compliant=True,
        images=[],
        description="Professional extraction tools. Sterilized, anti-slip grip.",
        product_url="https://deodap.com/product/blackhead-remover-kit",
    ),
    DeodapProduct(
        sku="DEODAP-BEA-003",
        title="Facial Ice Roller - Stainless Steel Head",
        category="beauty-tools",
        cost_price=110.0,
        mrp=449.0,
        moq=8,
        stock=120,
        weight_g=180,
        dimensions_cm="16x6x6",
        white_label=True,
        gst_compliant=True,
        images=[],
        description="Double-ended ice roller. Detachable head for freezer storage.",
        product_url="https://deodap.com/product/facial-ice-roller",
    ),
    DeodapProduct(
        sku="DEODAP-TRV-001",
        title="Packing Cubes Set of 6 - Water Resistant Nylon",
        category="travel-accessories",
        cost_price=125.0,
        mrp=499.0,
        moq=10,
        stock=160,
        weight_g=280,
        dimensions_cm="35x25x8",
        white_label=True,
        gst_compliant=True,
        images=[],
        description="6-piece packing cube set. Mesh tops, double zippers.",
        product_url="https://deodap.com/product/packing-cubes",
    ),
    DeodapProduct(
        sku="DEODAP-TRV-002",
        title="Collapsible Silicone Water Bottle - 500ml",
        category="travel-accessories",
        cost_price=85.0,
        mrp=349.0,
        moq=12,
        stock=220,
        weight_g=145,
        dimensions_cm="22x8x8",
        white_label=True,
        gst_compliant=True,
        images=[],
        description="Foldable silicone bottle. Leak-proof, BPA free.",
        product_url="https://deodap.com/product/collapsible-water-bottle",
    ),
    DeodapProduct(
        sku="DEODAP-HOM-001",
        title="Drawer Dividers Adjustable - Set of 4",
        category="home-organization",
        cost_price=65.0,
        mrp=279.0,
        moq=15,
        stock=350,
        weight_g=200,
        dimensions_cm="30x10x5",
        white_label=True,
        gst_compliant=True,
        images=[],
        description="Expandable drawer organizers. No tools needed.",
        product_url="https://deodap.com/product/drawer-dividers",
    ),
    DeodapProduct(
        sku="DEODAP-HOM-002",
        title="Tension Rods Set of 2 - Stainless Steel Extendable",
        category="home-organization",
        cost_price=95.0,
        mrp=379.0,
        moq=10,
        stock=180,
        weight_g=320,
        dimensions_cm="40x5x5",
        white_label=True,
        gst_compliant=True,
        images=[],
        description="Spring tension rods 80-120cm. No drilling required.",
        product_url="https://deodap.com/product/tension-rods",
    ),
    DeodapProduct(
        sku="DEODAP-HOM-003",
        title="Adhesive Cable Clips - Cable Management Pack of 20",
        category="home-organization",
        cost_price=35.0,
        mrp=149.0,
        moq=20,
        stock=600,
        weight_g=45,
        dimensions_cm="12x8x2",
        white_label=True,
        gst_compliant=True,
        images=[],
        description="Self-adhesive cable clips. Strong 3M backing.",
        product_url="https://deodap.com/product/adhesive-cable-clips",
    ),
    DeodapProduct(
        sku="DEODAP-PET-001",
        title="Silicone Lick Mat for Dogs - Slow Feeder",
        category="pet-accessories",
        cost_price=55.0,
        mrp=229.0,
        moq=15,
        stock=280,
        weight_g=85,
        dimensions_cm="20x20x1",
        white_label=True,
        gst_compliant=True,
        images=[],
        description="Textured lick mat. Suction cups for wall/floor.",
        product_url="https://deodap.com/product/silicone-lick-mat",
    ),
]


BASE_URL = os.environ.get("DEODAP_BASE_URL", "https://deodap.in").rstrip("/")
DEFAULT_CATEGORIES = [
    "kitchen-dining-items",
    "cookware-items",
    "home-storage-organisation-items",
    "home-decor-wall-art-items",
    "best-selling-products",
]
ENV_CATEGORIES = os.environ.get("DEODAP_CATEGORIES")
ADAPTIVE_DOMAIN = "deodap.in"
MAX_COLLECTION_PAGES = int(os.environ.get("DEODAP_MAX_PAGES", "3"))


def resolve_categories(categories: Optional[List[str]]) -> List[str]:
    if categories:
        return categories
    if ENV_CATEGORIES:
        return [c for c in ENV_CATEGORIES.split(",") if c.strip()]
    return DEFAULT_CATEGORIES


class DeodapSpider(MarketplaceSpider):
    name = "deodap_catalog"
    allowed_domains = {"deodap.in"}
    adaptive_domain = ADAPTIVE_DOMAIN
    concurrent_requests = 6
    concurrent_requests_per_domain = 6
    max_products = 0
    output_path = "data/deodap_catalog_raw.json"

    def __init__(self, categories: Optional[List[str]] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.categories = resolve_categories(categories)

    def configure_sessions(self, manager):
        manager.add(
            "http",
            FetcherSession(
                impersonate="chrome",
                stealthy_headers=True,
                timeout=30,
                retries=3,
                retry_delay=2,
                **self.session_config(),
            ),
            default=True,
        )

    async def start_requests(self):
        for category in self.categories:
            for page in range(1, MAX_COLLECTION_PAGES + 1):
                yield Request(
                    f"{BASE_URL}/collections/{category}?page={page}",
                    callback=self.parse_category,
                    meta={"category": category, "page": page},
                )

    async def parse_category(self, response: Response):
        category = response.request.meta.get("category") if response.request else "unknown"
        links = response.css("a[href*='/products/']", "deodap-product-link", **self.flags)
        handles = []
        for link in links:
            href = link.attrib.get("href", "").split("?")[0]
            if href not in handles:
                handles.append(href)
        if not handles:
            self.logger.warning("No product links in collection %s", category)
            return
        self.logger.info("Collection %s page %s: %d products", category, response.request.meta.get("page", ""), len(handles))
        for handle in handles:
            yield Request(
                f"{BASE_URL}{handle}",
                callback=self.parse_product,
                meta={"category": category},
            )

    async def parse_product(self, response: Response):
        category = response.request.meta.get("category") if response.request else "unknown"
        try:
            product = _parse_shopify_product(response, category)
        except Exception as exc:
            self.logger.error("Parse failed for %s: %s", response.url, exc)
            return
        if not product or not product.sku:
            return
        item = asdict(product)
        item["quality"] = "full"
        yield item

    async def parse(self, response: Response):
        async for item in self.parse_category(response):
            yield item


def _parse_shopify_product(response: Response, category: str) -> Optional[DeodapProduct]:
    body = response.html_content
    sku = None
    cost_price = None
    mrp = None
    images: List[str] = []
    description = ""

    variant_match = re.search(r'"variants":\s*(\[.*?\])(?=,|"\w)', body, re.DOTALL)
    if variant_match:
        variants_json = variant_match.group(1)
        prices = [float(m.group(1)) for m in re.finditer(r'"amount":\s*([\d.]+)', variants_json)]
        skus = [m.group(1) for m in re.finditer(r'"sku":\s*"([^"]*)"', variants_json)]
        if prices:
            cost_price = prices[0]
        if skus:
            sku = skus[0]
    if cost_price is None:
        price_m = re.search(r'"price":\s*"([\d.]+)"', body)
        if price_m:
            cost_price = float(price_m.group(1))

    compare_m = re.search(r'"compare_at_price":\s*"?([\d.]+)"?', body)
    if compare_m:
        raw = compare_m.group(1)
        mrp = float(raw) / 100 if raw.isdigit() and len(raw) >= 4 else float(raw)
    if mrp is None:
        mrp = cost_price

    meta_desc = re.search(r'<meta name="description" content="([^"]*)"', body)
    if meta_desc:
        description = re.sub(r"&amp;", "&", meta_desc.group(1))

    images = list(
        dict.fromkeys(
            src
            for src in re.findall(r"//deodap\.in/cdn/shop/files/[^\"' )?]+\.(?:png|jpe?g|webp|avif)", body)
        )
    )[:5]

    product_url = response.url.replace("?variant=", "?variant=") if "?" in response.url else response.url

    return DeodapProduct(
        sku=sku or extract_product_id(product_url, "/products/") or "unknown",
        title=(response.css("h1").first.text or "").strip() or f"DeoDap {sku}",
        category=category,
        cost_price=cost_price if cost_price is not None else 0.0,
        mrp=mrp if mrp is not None else cost_price,
        moq=10,
        stock=100,
        weight_g=200,
        dimensions_cm="20x15x5",
        white_label=True,
        gst_compliant=True,
        images=images,
        description=description,
        product_url=product_url,
    )


def mock_items(categories: Optional[List[str]] = None) -> list:
    if categories:
        return [asdict(p) for p in MOCK_DEODAP_CATALOG if p.category in categories]
    return [asdict(p) for p in MOCK_DEODAP_CATALOG]


def fetch_deodap_catalog() -> List[DeodapProduct]:
    return MOCK_DEODAP_CATALOG


if __name__ == "__main__":
    from scrapers.sources.base import run_spider, write_items

    import argparse

    parser = argparse.ArgumentParser(description="DeoDap wholesale catalog spider (use `pipeline run` instead)")
    parser.add_argument("--mock", action="store_true", help="Write bundled mock data")
    parser.add_argument("--categories", type=str, default=None, help="Comma-separated category slugs")
    args = parser.parse_args()
    categories = [c.strip() for c in args.categories.split(",")] if args.categories else None

    if args.mock:
        items = mock_items()
        write_items(items, "data/deodap_catalog_raw.json")
    else:
        spider = DeodapSpider(categories=categories)
        items = run_spider(spider)
        write_items(items, "data/deodap_catalog_raw.json")