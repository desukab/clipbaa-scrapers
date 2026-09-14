"""Append-only price history, velocity, and change alerts."""
import json
from pathlib import Path
from typing import Dict, List

from scrapers.config import Settings
from scrapers.io import atomic_write_text, ensure_dir


def history_path(settings: Settings) -> str:
    base = settings.history_dir or settings.output_dir
    return str(Path(base) / "products.jsonl")


def collect_raw(products: Dict[str, List[dict]], run_ts: str) -> List[dict]:
    rows = []
    for source, items in products.items():
        for it in items:
            key = it.get("asin") or it.get("product_id") or it.get("sku")
            if not key:
                continue
            price = it.get("cost_price") if source == "deodap" else it.get("current_price")
            rows.append({
                "source": source,
                "key": key,
                "ts": run_ts,
                "price": price,
                "rating": it.get("rating"),
                "review_count": it.get("review_count"),
                "stock": it.get("stock"),
            })
    return rows


def read_lines(path: str) -> List[dict]:
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    try:
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # tolerate corrupt history lines
    except OSError:
        return []
    return rows


def append_history(path: str, rows: List[dict]) -> None:
    if not rows:
        return
    ensure_dir(Path(path).parent)
    existing = read_lines(path)
    combined = existing + rows
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in combined)
    atomic_write_text(path, text)


def compute_velocity(rows: List[dict], lookback_days: int = 14) -> Dict[str, float]:
    by_key: Dict[str, List[dict]] = {}
    for r in rows:
        by_key.setdefault(r["key"], []).append(r)
    result: Dict[str, float] = {}
    for key, group in by_key.items():
        priced = [r for r in group if isinstance(r.get("price"), (int, float))]
        if len(priced) < 2:
            continue
        earliest, latest = priced[0], priced[-1]
        if not earliest.get("price"):
            continue
        change = (latest["price"] - earliest["price"]) / earliest["price"] * 100
        result[key] = round(change, 2)
    return result


def compute_alerts(
    rows: List[dict],
    price_drop_pct: float = 5.0,
    restock_threshold: int = 20,
) -> List[dict]:
    alerts: List[dict] = []
    by_key: Dict[str, List[dict]] = {}
    for r in rows:
        by_key.setdefault(r["key"], []).append(r)
    for key, group in by_key.items():
        priced = [r for r in group if isinstance(r.get("price"), (int, float))]
        if len(priced) >= 2:
            first, last = priced[0], priced[-1]
            if first.get("price") and last.get("price"):
                drop = (first["price"] - last["price"]) / first["price"] * 100
                if drop >= price_drop_pct:
                    alerts.append({"key": key, "kind": "price_drop", "pct": round(drop, 2),
                                   "from": first["price"], "to": last["price"]})
        stocks = [r for r in group if isinstance(r.get("stock"), int)]
        if len(stocks) >= 2:
            first_stock, last_stock = stocks[0]["stock"], stocks[-1]["stock"]
            if first_stock < restock_threshold and last_stock >= restock_threshold:
                alerts.append({"key": key, "kind": "restock", "from": first_stock, "to": last_stock})
    return alerts