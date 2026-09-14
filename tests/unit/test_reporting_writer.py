import csv
from dataclasses import asdict

from scrapers.config import Settings
from scrapers.io import load_json
from scrapers.matching.matcher import MatchRecord, MatchSummary
from scrapers.reporting.writer import (
    CSV_COLUMNS,
    write_all_outputs,
    write_csv,
    write_winners_markdown,
)


def _make_match() -> MatchRecord:
    kwargs = {name: None for name in MatchRecord.__dataclass_fields__}
    kwargs.update({
        "marketplace": "amazon", "marketplace_asin": "B1",
        "marketplace_title": "Silicone Stretch Lids Set of 12",
        "marketplace_price": 199.0, "marketplace_reviews": 23,
        "deodap_sku": "SKU1", "deodap_title": "Silicone Stretch Lids",
        "deodap_cost": 65.0, "deodap_moq": 10, "deodap_stock": 200,
        "deodap_weight_g": 180, "deodap_white_label": True, "deodap_gst_compliant": True,
        "match_confidence": 0.8, "net_margin_inr": 60.0, "roi_pct": 80.0,
        "absolute_margin_inr": 134.0, "margin_percentage": 206.2, "opportunity_score": 75.0,
        "marketplace_rating": 4.2, "movers_rank": 3, "bsr_current": 1250,
        "seller_count": 3, "fba_seller_count": 1, "weight_g": 180,
    })
    return MatchRecord(**kwargs)


def test_csv_columns_unchanged():
    assert CSV_COLUMNS == [
        "amazon_title", "deodap_sku", "cost", "amazon_price",
        "absolute_margin_inr", "margin_percentage",
    ]


def test_write_csv(tmp_path):
    path = tmp_path / "out.csv"
    write_csv(str(path), [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}], columns=["a", "b"])
    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows == [["a", "b"], ["1", "x"], ["2", "y"]]


def test_markdown_has_header():
    md = write_winners_markdown([])
    assert "Rank" in md
    assert "Opportunity" in md


def test_write_all_outputs(tmp_path):
    s = Settings(output_dir=str(tmp_path / "data"))
    summary = MatchSummary(marketplace_total=1, candidates=[_make_match()],
                           winners=[_make_match()], near_misses=[])
    paths = write_all_outputs(s, summary)
    data = load_json(paths["matched_json"])
    assert data["marketplace_total"] == 1
    assert len(data["winners"]) == 1
    assert paths["matched_json"].endswith("matched_products.json")
    assert paths["markdown"].endswith("winners.md")
    assert (tmp_path / "data" / "matched_products.csv").exists()