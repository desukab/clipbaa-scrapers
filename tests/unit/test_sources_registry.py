import scrapers.sources  # noqa: F401  (registration side effect)
from scrapers.registry import get_source, list_sources


def test_builtin_names_registered():
    scrapers.sources.register_builtins()  # refresh in case other tests cleared the registry
    names = {spec.name for spec in list_sources()}
    assert names == {"amazon", "meesho", "flipkart", "deodap"}


def test_specs_have_mock_items_and_outputs():
    amazon = get_source("amazon")
    assert amazon.output_file == "amazon_movers_raw.json"
    assert amazon.live_capable is True
    assert amazon.default_max_products == 50
    assert amazon.mock_items and amazon.mock_items[0]["asin"]
    assert get_source("meesho").output_file == "meesho_trending_raw.json"
    assert get_source("flipkart").output_file == "flipkart_bestsellers_raw.json"
    assert get_source("deodap").output_file == "deodap_catalog_raw.json"
    assert get_source("deodap").mock_items and get_source("deodap").mock_items[0]["sku"]