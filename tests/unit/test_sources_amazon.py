from scrapers.sources.amazon import (
    MOCK_AMAZON_MOVERS,
    AmazonMoversSpider,
    extract_asin,
    mock_items,
)


def test_mock_records_have_id_title_price_url():
    records = mock_items()
    assert len(records) >= 10
    for r in records:
        assert r["asin"]
        assert r["title"]
        assert r["current_price"] > 0
        assert r["product_url"].startswith("https://")


def test_mock_records_are_stable():
    records = mock_items()
    assert records[0]["asin"] == MOCK_AMAZON_MOVERS[0].asin
    assert records[0]["current_price"] == 199.0


def test_extract_asin():
    assert extract_asin("https://www.amazon.in/dp/B09X7Y6Z5W") == "B09X7Y6Z5W"
    assert extract_asin("https://www.amazon.in/dp/NO3NOPE") is None


def test_spider_configuration_surface():
    assert AmazonMoversSpider.name == "amazon_movers"
    assert AmazonMoversSpider.allowed_domains == {"amazon.in"}
    assert AmazonMoversSpider.adaptive_domain == "amazon.in"