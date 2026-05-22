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


def build_price_context(city: Optional[str] = None) -> str:
    """
    Pull the latest price snapshot from DynamoDB and format it as
    a structured text block for Claude's system prompt.
    """
    snapshot = get_latest_snapshot()
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

            if city and metal.city_rates and city in metal.city_rates:
                city_rate = float(metal.city_rates[city])
                lines.append(f"  City rate ({city}): ₹{city_rate:,.0f}/10g")

        lines.append(f"  Confidence: {metal.confidence} ({metal.source_count} sources)")
        lines.append("")

    return "\n".join(lines)
