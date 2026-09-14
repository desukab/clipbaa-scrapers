from scrapers.schemas import normalize_record, validate_record


def _amz():
    return {
        "source": "amazon", "asin": "B1", "title": "T", "current_price": "199",
        "product_url": "https://a.in/dp/B1", "quality": "card",
    }


def _deodap():
    return {
        "source": "deodap", "sku": "S1", "title": "T", "cost_price": "65",
        "product_url": "https://d.in/p/1",
    }


def test_amazon_valid():
    assert validate_record(_amz()) == []


def test_deodap_valid():
    assert validate_record(_deodap()) == []


def test_missing_required_fields():
    bad = _amz()
    bad["current_price"] = 0
    errors = validate_record(bad)
    assert any("current_price" in e for e in errors)

    d_bad = _deodap()
    del d_bad["sku"]
    assert validate_record(d_bad)


def test_normalize_coerces_numerics():
    rec = normalize_record(_amz())
    assert rec["current_price"] == 199.0
    assert rec["review_count"] == 0


def test_unknown_source_uses_marketplace_rules():
    rec = {"source": "mystery", "title": "T", "current_price": 10, "product_url": "u"}
    assert validate_record(rec) == []