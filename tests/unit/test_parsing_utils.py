from scrapers.parsing_utils import (
    extract_product_id,
    parse_bsr,
    parse_dimensions_cm,
    parse_int,
    parse_price,
    parse_rating,
    parse_weight_g,
)


def test_parse_price():
    assert parse_price("₹1,299.50") == 1299.5
    assert parse_price("Rs. 499") == 499.0
    assert parse_price("INR 99") == 99.0
    assert parse_price("no price here") is None
    assert parse_price(None) is None


def test_parse_int():
    assert parse_int("1,234 ratings", 0) == 1234
    assert parse_int("none", 7) == 7


def test_parse_rating():
    assert parse_rating("4.4 out of 5") == 4.4


def test_parse_weight_g():
    assert parse_weight_g("Item Weight: 220 g") == 220
    assert parse_weight_g("1.5 kg") == 1500


def test_parse_dimensions_cm():
    assert parse_dimensions_cm("18 x 6 x 4 cm") == "18x6x4"
    assert parse_dimensions_cm("42x3x2 cm") == "42x3x2"


def test_parse_bsr():
    assert parse_bsr("#1,250 in Kitchen") == (1250, "Kitchen")
    assert parse_bsr("nothing") == (None, None)


def test_extract_product_id():
    assert extract_product_id("https://www.amazon.in/dp/B09X7Y6Z5W?th=1", "/dp/") == "B09X7Y6Z5W"


def test_textnode_importable_without_scrapling():
    from scrapers.parsing_utils import TextNode
    assert TextNode is not None