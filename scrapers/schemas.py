"""Normalized ProductRecord schema: coercion + validation (stdlib only)."""
from typing import List, Optional

_MARKETPLACE_SOURCES = {"amazon", "meesho", "flipkart"}
_NUMERIC_FIELDS = (
    "current_price",
    "mrp",
    "cost_price",
    "discount_pct",
    "rating",
    "review_count",
    "seller_count",
    "fba_seller_count",
    "weight_g",
    "images_count",
    "movers_rank",
    "stock",
    "moq",
)


def _to_float(value) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def normalize_record(record: dict) -> dict:
    out = dict(record)
    for field in _NUMERIC_FIELDS:
        out[field] = _to_float(out.get(field))
    out.setdefault("quality", "full")
    out.setdefault("source", "unknown")
    out.setdefault("title", "")
    return out


def validate_record(record: dict) -> List[str]:
    record = normalize_record(record)
    errors: List[str] = []
    if not record.get("title"):
        errors.append("title is required")
    if not (record.get("product_url") or record.get("url")):
        errors.append("product_url is required")
    source = record.get("source")
    if source == "deodap":
        if not record.get("sku"):
            errors.append("sku is required for deodap records")
        if record.get("cost_price", 0.0) <= 0:
            errors.append("cost_price must be > 0")
    elif source in _MARKETPLACE_SOURCES:
        pid = record.get("asin") or record.get("product_id") or record.get("sku")
        if not pid:
            errors.append("marketplace id (asin/product_id/sku) is required")
        if record.get("current_price", 0.0) <= 0:
            errors.append("current_price must be > 0")
    return errors