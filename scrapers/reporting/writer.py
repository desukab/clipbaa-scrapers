"""Result serializers: JSON, CSV (stdlib), and a markdown winners report."""
import csv
import os
from dataclasses import asdict
from typing import List, Optional

from scrapers.config import Settings
from scrapers.io import atomic_write_json, atomic_write_text, ensure_dir
from scrapers.matching.matcher import CSV_COLUMNS, MatchRecord, MatchSummary


def write_json(path: str, data) -> None:
    atomic_write_json(path, data)


def write_csv(path: str, rows: List[dict], columns: Optional[List[str]] = None) -> None:
    columns = columns or CSV_COLUMNS
    ensure_dir(os.path.dirname(os.path.abspath(path)))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([row.get(c, "") for c in columns])


def _winner_row(m: MatchRecord) -> dict:
    return {
        "amazon_title": m.marketplace_title,
        "deodap_sku": m.deodap_sku,
        "cost": m.deodap_cost,
        "amazon_price": m.marketplace_price,
        "absolute_margin_inr": m.absolute_margin_inr,
        "margin_percentage": m.margin_percentage,
    }


def write_winners_markdown(winners: List[MatchRecord], path: Optional[str] = None, top_n: int = 25) -> str:
    lines = [
        "# Matched Product Winners",
        "",
        "> Ranked opportunity report. Thresholds are config-driven (see run manifest).",
        "",
        "| Rank | Marketplace | Title | DeoDap SKU | Cost | Price | Margin INR | Margin % | Conf | Opportunity |",
        "|------|-------------|-------|------------|------|-------|-----------|----------|------|------------|",
    ]
    for i, m in enumerate(winners[:top_n], 1):
        lines.append(
            f"| {i} | {m.marketplace} | {m.marketplace_title[:60]} | {m.deodap_sku} "
            f"| ₹{m.deodap_cost} | ₹{m.marketplace_price} | ₹{m.absolute_margin_inr} "
            f"| {m.margin_percentage}% | {m.match_confidence:.0%} | {m.opportunity_score} |"
        )
    md = "\n".join(lines) + "\n"
    if path:
        atomic_write_text(path, md)
    return md


def write_near_misses(path: str, rows: List[dict]) -> None:
    write_json(path, rows)


def write_all_outputs(settings: Settings, summary: MatchSummary) -> dict:
    out = settings.output_dir
    ensure_dir(out)
    paths = {
        "matched_json": os.path.join(out, "matched_products.json"),
        "matched_csv": os.path.join(out, "matched_products.csv"),
        "markdown": os.path.join(out, "winners.md"),
        "near_matches": os.path.join(out, "near_matches.json"),
    }
    write_json(paths["matched_json"], summary.to_dict())
    write_csv(paths["matched_csv"], [_winner_row(w) for w in summary.winners])
    write_winners_markdown(summary.winners, path=paths["markdown"], top_n=settings.report_top_n)
    write_near_misses(paths["near_matches"], [asdict(n) for n in summary.near_misses])
    return paths