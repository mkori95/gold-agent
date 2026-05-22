import time
from typing import Optional
from src.shared.db.dynamo_reader import get_latest_snapshot
from src.shared.models.price import PriceSnapshot
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
}

_CACHE_TTL_SECONDS = 3600  # prices refresh once daily — 1 hour TTL is safe

_cached_snapshot: Optional[PriceSnapshot] = None
_cache_fetched_at: float = 0.0


def _get_snapshot() -> Optional[PriceSnapshot]:
    global _cached_snapshot, _cache_fetched_at
    if _cached_snapshot is not None and (time.time() - _cache_fetched_at) < _CACHE_TTL_SECONDS:
        logger.info("Price snapshot served from cache")
        return _cached_snapshot
    snapshot = get_latest_snapshot()
    if snapshot is not None:
        _cached_snapshot = snapshot
        _cache_fetched_at = time.time()
        logger.info("Price snapshot fetched from DynamoDB and cached")
    return snapshot


def build_price_context(city: Optional[str] = None) -> str:
    """
    Pull the latest price snapshot (cached) and format it as
    a structured text block for Claude's system prompt.
    """
    snapshot = _get_snapshot()
    if snapshot is None:
        return "Live price data is currently unavailable."

    lines = [f"Price snapshot date: {snapshot.snapshot_date}", ""]

    for metal_id, metal in snapshot.metals.items():
        lines.append(f"=== {metal_id.upper()} ===")
        lines.append(f"  Price (USD/troy oz): ${metal.price_usd:,.2f}")

        if metal.price_inr:
            lines.append(f"  Price (INR/troy oz): ₹{metal.price_inr:,.0f}")

        if metal.inr_rate:
            lines.append(f"  USD/INR rate used: {metal.inr_rate:.2f}")

        if metal_id == "gold":
            if metal.price_22k_inr:
                lines.append(f"  22K gold per gram (INR): ₹{metal.price_22k_inr:,.0f}")
            if metal.price_24k_inr:
                lines.append(f"  24K gold per gram (INR): ₹{metal.price_24k_inr:,.0f}")

            if metal.city_rates:
                lines.append("  Indian city rates (22K per 10g):")
                for city_key in sorted(metal.city_rates.keys()):
                    display = city_key.replace("-", " ").title()
                    lines.append(f"    {display}: ₹{float(metal.city_rates[city_key]):,.0f}")

        lines.append(f"  Confidence: {metal.confidence} ({metal.source_count} sources)")
        lines.append("")

    return "\n".join(lines)
