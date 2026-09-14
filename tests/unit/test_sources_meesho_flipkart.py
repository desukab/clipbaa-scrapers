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