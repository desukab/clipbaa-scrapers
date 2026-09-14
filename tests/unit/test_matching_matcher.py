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
    assert matches  # identical titles clear a 0.9 confidence bar
    assert all(x.match_confidence >= 0.9 for x in matches)


def test_matcher_near_miss_below_confidence():
    m = DeodapMatcher(min_confidence=0.9)
    m.deodap_catalog = CATALOG
    low = dict(AMZ[0])
    low["title"] = "Silicone Stretch Lids Reusable"
    matches = m.find_matches([low])
    assert matches == []
    assert len(m.near_misses) >= 1
    assert all(x.match_confidence < 0.9 for x in m.near_misses)