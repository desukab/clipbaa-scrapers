import re
from typing import Any, List, Optional, Sequence, Tuple, Union

try:  # scrapling is only required for live runs
    from scrapling.parser import Selector, Selectors

    TextNode = Union[Selector, Selectors]
except ImportError:  # pragma: no cover
    TextNode = Any

INDIAN_PRICE_RE = re.compile(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)")
PLAIN_NUMBER_RE = re.compile(r"([\d,]+(?:\.\d{1,2})?)")


def first_text(
    doc: TextNode,
    selectors: Union[str, Sequence[str]],
    identifier: str = "",
    adaptive: bool = False,
    auto_save: bool = False,
    percentage: int = 40,
    default: Optional[str] = None,
) -> Optional[str]:
    if isinstance(selectors, str):
        selectors = (selectors,)
    for index, selector in enumerate(selectors):
        use_adaptive = bool(identifier) and index == 0
        element = doc.css(
            selector,
            identifier or selector,
            adaptive=adaptive and use_adaptive,
            auto_save=auto_save and use_adaptive,
            percentage=percentage,
        ).first
        if element is not None:
            text = element.text
            if text and text.strip():
                return text.strip()
    return default


def all_text(
    doc: TextNode,
    selectors: Union[str, Sequence[str]],
    identifier: str = "",
    adaptive: bool = False,
    auto_save: bool = False,
    percentage: int = 40,
) -> List[str]:
    if isinstance(selectors, str):
        selectors = (selectors,)
    results: List[str] = []
    for index, selector in enumerate(selectors):
        use_adaptive = bool(identifier) and index == 0
        elements = doc.css(
            selector,
            identifier or selector,
            adaptive=adaptive and use_adaptive,
            auto_save=auto_save and use_adaptive,
            percentage=percentage,
        )
        for element in elements:
            text = element.text
            if text and text.strip():
                results.append(text.strip())
    return results


def full_text(
    doc: TextNode,
    selectors: Union[str, Sequence[str]],
    identifier: str = "",
    adaptive: bool = False,
    auto_save: bool = False,
    percentage: int = 40,
    separator: str = "\n",
    default: Optional[str] = None,
) -> Optional[str]:
    if isinstance(selectors, str):
        selectors = (selectors,)
    for index, selector in enumerate(selectors):
        use_adaptive = bool(identifier) and index == 0
        element = doc.css(
            selector,
            identifier or selector,
            adaptive=adaptive and use_adaptive,
            auto_save=auto_save and use_adaptive,
            percentage=percentage,
        ).first
        if element is not None:
            text = element.get_all_text(separator=separator, strip=True)
            if text and text.strip():
                return text.strip()
    return default


def count_matches(doc: TextNode, selector: str, default: int = 0) -> int:
    elements = doc.css(selector)
    return len(elements) or default


def has_any_text(
    doc: TextNode,
    selector: str,
    needles: Sequence[str],
    identifier: str = "",
    adaptive: bool = False,
    auto_save: bool = False,
    percentage: int = 40,
) -> bool:
    elements = doc.css(
        selector,
        identifier or selector,
        adaptive=adaptive and bool(identifier),
        auto_save=auto_save and bool(identifier),
        percentage=percentage,
    )
    lowered = tuple(needle.lower() for needle in needles)
    for element in elements:
        text = element.text or ""
        if any(needle in text.lower() for needle in lowered):
            return True
    return False


def breadcrumb_path(
    doc: TextNode,
    selectors: Union[str, Sequence[str]],
    identifier: str = "",
    adaptive: bool = False,
    auto_save: bool = False,
    percentage: int = 40,
    default: str = "Unknown",
) -> str:
    crumbs = all_text(doc, selectors, identifier, adaptive, auto_save)
    return " > ".join(crumbs[-3:]) if crumbs else default


def parse_price(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    text = text.strip()
    match = INDIAN_PRICE_RE.search(text)
    if match:
        return float(match.group(1).replace(",", ""))
    match = PLAIN_NUMBER_RE.search(text)
    if match:
        try:
            return float(match.group(1).replace(",", ""))
        except (ValueError, TypeError):
            return None
    return None


def parse_int(text: Optional[str], default: int = 0) -> int:
    if not text:
        return default
    match = re.search(r"[\d,]+", text.replace(",", ""))
    if match:
        try:
            return int(match.group(0).replace(",", "").strip())
        except (ValueError, TypeError):
            return default
    return default


def parse_optional_int(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    match = re.search(r"[\d,]+", text.replace(",", ""))
    if match:
        try:
            return int(match.group(0).replace(",", "").strip())
        except (ValueError, TypeError):
            return None
    return None


def parse_rating(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            return None
    return None


def parse_weight_g(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    kilograms = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|kilograms?|kilos?)\b", text, re.IGNORECASE)
    if kilograms:
        try:
            return int(float(kilograms.group(1)) * 1000)
        except (ValueError, TypeError):
            return None
    grams = re.search(r"(\d+(?:\.\d+)?)\s*(?:gm?|g)\b", text, re.IGNORECASE)
    if grams:
        try:
            return int(float(grams.group(1)))
        except (ValueError, TypeError):
            return None
    grams_plain = re.search(r"(\d{2,4})\s*gram|item weight.{0,20}(\d{2,4})", text, re.IGNORECASE)
    if grams_plain:
        try:
            return int(grams_plain.group(1) or grams_plain.group(2))
        except (ValueError, TypeError):
            return None
    return None


def parse_dimensions_cm(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    cm_match = re.search(
        r"(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(?:cm|centimeters?|cms)\b",
        text,
        re.IGNORECASE,
    )
    if cm_match:
        return f"{cm_match.group(1)}x{cm_match.group(2)}x{cm_match.group(3)}"
    inch_match = re.search(
        r"(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(?:in|inches?)",
        text,
    )
    if inch_match:
        cm = "x".join(str(round(float(g) * 2.54, 1)) for g in inch_match.groups())
        return cm
    loose_cm = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:cm|centimeters?)",
        text,
        re.IGNORECASE,
    )
    if loose_cm:
        return loose_cm.group(1)
    return None


def parse_bsr(text: Optional[str]) -> Tuple[Optional[int], Optional[str]]:
    if not text:
        return None, None
    match = re.search(r"#([\d,]+)\s+in\s+([^(]+)", text)
    if match:
        rank = int(match.group(1).replace(",", ""))
        category = match.group(2).strip()
        return rank, category
    return None, None


def extract_product_id(url: str, marker: str) -> Optional[str]:
    if marker not in url:
        return None
    tail = url.split(marker, 1)[1]
    tail = tail.strip("/").split("?", 1)[0].split("#", 1)[0]
    product_id = tail.split("/", 1)[0]
    return product_id or None


def short_text(text: Optional[str], limit: int = 120) -> str:
    text = (text or "Unknown").replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + "..."