import pytest

from scrapers.errors import DependencyError
from scrapers.io import load_json
from scrapers.sources.base import (
    SPIDERS_OK,
    dedupe_items,
    ensure_output_paths,
    load_items,
    run_spider,
    write_items,
)


def test_dedupe_prefers_full_and_merges():
    items = [
        {"asin": "A1", "title": "t", "current_price": 100, "quality": "card"},
        {"asin": "A1", "title": "t", "current_price": 110, "seller_count": 3, "quality": "full"},
        {"asin": "A2", "title": "u", "current_price": 90, "quality": "full"},
    ]
    out = dedupe_items(items)
    by_asin = {i["asin"]: i for i in out}
    assert set(by_asin) == {"A1", "A2"}
    assert by_asin["A1"]["current_price"] == 110
    assert by_asin["A1"]["seller_count"] == 3


def test_write_load_items(tmp_path):
    path = tmp_path / "raw.json"
    write_items([{"a": 1}], str(path))
    assert load_items(str(path)) == [{"a": 1}]
    assert load_json(path) == [{"a": 1}]


def test_load_missing_returns_empty(tmp_path):
    assert load_items(str(tmp_path / "nope.json")) == []


def test_ensure_output_paths(tmp_path):
    p = str(tmp_path / "x" / "y.json")
    ensure_output_paths([p])
    assert (tmp_path / "x").exists()


def test_run_spider_requires_scrapling():
    if SPIDERS_OK:
        pytest.skip("scrapling present; dependency guard not applicable")
    with pytest.raises(DependencyError):
        run_spider(object())