import os

import pytest

from scrapers.config import Settings
from scrapers.matching.history import (
    collect_raw,
    compute_alerts,
    compute_velocity,
    history_path,
)


def _rows():
    return [
        {"source": "amazon", "key": "B1", "ts": "20260901T000000Z", "price": 200.0,
         "rating": 4.0, "review_count": 10, "stock": None},
        {"source": "amazon", "key": "B1", "ts": "20260914T000000Z", "price": 150.0,
         "rating": 4.2, "review_count": 12, "stock": None},
    ]


def test_collect_raw():
    rows = collect_raw(
        {"amazon": [{"asin": "B1", "current_price": 150.0, "rating": 4.1, "review_count": 5}]},
        "ts1",
    )
    assert rows[0] == {"source": "amazon", "key": "B1", "ts": "ts1", "price": 150.0,
                       "rating": 4.1, "review_count": 5, "stock": None}


def test_velocity_drop():
    assert compute_velocity(_rows())["B1"] == pytest.approx(-25.0, abs=1e-6)


def test_price_drop_alert():
    drops = [a for a in compute_alerts(_rows(), price_drop_pct=5.0) if a["kind"] == "price_drop"]
    assert len(drops) == 1
    assert drops[0]["key"] == "B1"


def test_restock_alert():
    rows = [
        {"source": "deodap", "key": "S1", "ts": "t1", "price": 60.0, "stock": 0},
        {"source": "deodap", "key": "S1", "ts": "t2", "price": 60.0, "stock": 50},
    ]
    assert any(a["kind"] == "restock" for a in compute_alerts(rows, restock_threshold=20))


def test_history_path():
    s = Settings(output_dir="data", history_dir=None)
    assert history_path(s) == os.path.join("data", "products.jsonl")
    s2 = Settings(output_dir="data", history_dir="hist")
    assert history_path(s2) == os.path.join("hist", "products.jsonl")