from scrapers.sources.deodap import DeodapSpider, MOCK_DEODAP_CATALOG, mock_items, resolve_categories


def test_mock_catalog_complete():
    records = mock_items()
    assert len(records) == len(MOCK_DEODAP_CATALOG)
    for r in records:
        assert r["sku"]
        assert r["title"]
        assert r["cost_price"] > 0
        assert r["white_label"] is True
        assert r["gst_compliant"] is True


def test_mock_items_category_filter():
    records = mock_items(categories=["kitchen-tools"])
    assert len(records) >= 2
    assert all(r["category"] == "kitchen-tools" for r in records)


def test_resolve_categories_default():
    cats = resolve_categories(None)
    assert "best-selling-products" in cats


def test_spider_surface():
    assert DeodapSpider.name == "deodap_catalog"
    assert DeodapSpider.allowed_domains == {"deodap.in"}
    assert DeodapSpider.max_products == 0