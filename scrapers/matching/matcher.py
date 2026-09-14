"""Pure matcher: marketplace listing -> DeoDap catalog pairing and winner filtering."""
import os
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from scrapers.config import Settings
from scrapers.io import load_json
from scrapers.matching.scoring import (
    calculate_margin,
    eligible_deodap,
    is_noise,
    NEAR_MISS_FLOOR,
    opportunity_score,
    similarity,
    to_float,
    utility_bonus,
)

CSV_COLUMNS = [
    "amazon_title",
    "deodap_sku",
    "cost",
    "amazon_price",
    "absolute_margin_inr",
    "margin_percentage",
]


@dataclass
class MatchRecord:
    marketplace: str = ""
    marketplace_asin: str = ""
    marketplace_title: str = ""
    marketplace_price: float = 0.0
    marketplace_reviews: int = 0
    marketplace_rating: Optional[float] = None
    movers_rank: Optional[int] = None
    bsr_current: Optional[int] = None
    seller_count: int = 0
    fba_seller_count: int = 0
    weight_g: Optional[int] = None

    deodap_sku: str = ""
    deodap_title: str = ""
    deodap_cost: float = 0.0
    deodap_moq: int = 0
    deodap_stock: int = 0
    deodap_weight_g: int = 0
    deodap_white_label: bool = False
    deodap_gst_compliant: bool = False

    match_confidence: float = 0.0
    net_margin_inr: float = 0.0
    roi_pct: float = 0.0
    absolute_margin_inr: float = 0.0
    margin_percentage: float = 0.0
    opportunity_score: float = 0.0


@dataclass
class MatchSummary:
    marketplace_total: int
    candidates: list
    winners: list
    near_misses: list

    @property
    def high_opportunity(self) -> int:
        return sum(1 for w in self.winners if w.opportunity_score >= 65)

    def to_dict(self) -> dict:
        return {
            "marketplace_total": self.marketplace_total,
            "candidates": [asdict(c) for c in self.candidates],
            "winners": [asdict(w) for w in self.winners],
            "near_misses": [asdict(n) for n in self.near_misses],
            "high_opportunity": self.high_opportunity,
        }


class DeodapMatcher:
    def __init__(self, min_confidence: float = 0.5):
        self.min_confidence = min_confidence
        self.deodap_catalog: List[Dict] = []
        self.near_misses: List[MatchRecord] = []

    def load_catalog(self, filepath: str) -> None:
        self.deodap_catalog = list(load_json(filepath, default=[]))

    def _best_candidate(self, mp_title: str, mp_price: float) -> tuple:
        best_match = None
        best_confidence = 0.0
        for dp in self.deodap_catalog:
            if not eligible_deodap(dp, mp_price):
                continue
            confidence = similarity(mp_title, dp.get("title", ""))
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = dp
        return best_match, best_confidence

    def find_matches(self, marketplace_products: List[Dict]) -> List[MatchRecord]:
        matches: List[MatchRecord] = []
        self.near_misses = []

        for mp in marketplace_products:
            mp_title = str(mp.get("title") or "")
            mp_price = to_float(mp.get("current_price"))
            if mp_price <= 0:
                continue

            best_match, best_confidence = self._best_candidate(mp_title, mp_price)
            if not best_match:
                continue

            scored = self._score_match(mp, best_match, best_confidence)
            if best_confidence >= self.min_confidence:
                matches.append(scored)
            elif best_confidence >= NEAR_MISS_FLOOR:
                self.near_misses.append(scored)

        return matches

    def _score_match(self, mp: Dict, best_match: Dict, best_confidence: float) -> MatchRecord:
        mp_title = str(mp.get("title") or "")
        mp_weight = int(to_float(mp.get("weight_g")) or 200)
        mp_price = to_float(mp.get("current_price"))
        cost = to_float(best_match.get("cost_price"))

        net_margin, roi = calculate_margin(mp_price, cost, mp_weight)
        absolute_margin_inr = round(mp_price - cost, 2)
        margin_percentage = round(((mp_price - cost) / cost) * 100, 1) if cost > 0 else 0.0

        movers_rank = mp.get("movers_rank") or 999
        review_count = int(to_float(mp.get("review_count")))
        bsr_avg = to_float(mp.get("bsr_30d_avg")) or (to_float(mp.get("bsr_current")) or 10000) * 2
        bsr_current = to_float(mp.get("bsr_current")) or 10000

        opportunity = opportunity_score(movers_rank, review_count, bsr_avg, bsr_current, roi)

        return MatchRecord(
            marketplace=mp.get("source", "unknown"),
            marketplace_asin=mp.get("asin") or mp.get("product_id") or "",
            marketplace_title=mp_title,
            marketplace_price=mp_price,
            marketplace_reviews=review_count,
            marketplace_rating=mp.get("rating"),
            movers_rank=mp.get("movers_rank"),
            bsr_current=bsr_current,
            seller_count=int(to_float(mp.get("seller_count"))),
            fba_seller_count=int(to_float(mp.get("fba_seller_count"))),
            weight_g=mp_weight,
            deodap_sku=str(best_match.get("sku", "")),
            deodap_title=str(best_match.get("title", "")),
            deodap_cost=cost,
            deodap_moq=int(to_float(best_match.get("moq"))),
            deodap_stock=int(to_float(best_match.get("stock"))),
            deodap_weight_g=int(to_float(best_match.get("weight_g"))),
            deodap_white_label=bool(best_match.get("white_label")),
            deodap_gst_compliant=bool(best_match.get("gst_compliant")),
            match_confidence=best_confidence,
            net_margin_inr=round(net_margin, 2),
            roi_pct=round(roi, 1),
            absolute_margin_inr=absolute_margin_inr,
            margin_percentage=margin_percentage,
            opportunity_score=round(opportunity, 1),
        )

    def filter_winners(
        self,
        candidates,
        min_absolute_margin: float = 200.0,
        min_margin_pct: float = 35.0,
        min_ticket_price: float = 300.0,
        max_sellers: int = 5,
        max_fba_sellers: int = 2,
    ) -> list:
        winners = []
        for m in candidates:
            if m.marketplace_price < min_ticket_price:
                continue
            if m.absolute_margin_inr < min_absolute_margin:
                continue
            if m.margin_percentage < min_margin_pct:
                continue
            if m.seller_count > max_sellers:
                continue
            if m.fba_seller_count > max_fba_sellers:
                continue
            if is_noise(m.marketplace_title):
                continue
            winners.append(m)
        winners.sort(key=lambda m: (utility_bonus(m.marketplace_title), m.opportunity_score), reverse=True)
        return winners


def load_marketplace_products(output_dir: str) -> list:
    products = []
    for filename, source in [
        ("amazon_movers_raw.json", "amazon"),
        ("meesho_trending_raw.json", "meesho"),
        ("flipkart_bestsellers_raw.json", "flipkart"),
    ]:
        path = os.path.join(output_dir, filename)
        batch = list(load_json(path, default=[]))
        for p in batch:
            p["source"] = p.get("source") or source
            if to_float(p.get("current_price")) > 0:
                products.append(p)
    return products


def run_matching(settings: Settings) -> MatchSummary:
    matcher = DeodapMatcher(min_confidence=settings.min_confidence)
    matcher.load_catalog(os.path.join(settings.output_dir, "deodap_catalog_raw.json"))
    products = load_marketplace_products(settings.output_dir)
    candidates = matcher.find_matches(products)
    winners = matcher.filter_winners(
        candidates,
        min_absolute_margin=settings.min_absolute_margin,
        min_margin_pct=settings.min_margin_pct,
        min_ticket_price=settings.min_ticket_price,
        max_sellers=settings.max_sellers,
        max_fba_sellers=settings.max_fba_sellers,
    )
    return MatchSummary(
        marketplace_total=len(products),
        candidates=candidates,
        winners=winners,
        near_misses=list(matcher.near_misses),
    )