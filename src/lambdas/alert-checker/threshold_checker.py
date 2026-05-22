from src.shared.models.alert import AlertPreference
from src.shared.models.price import PriceSnapshot
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


def get_current_price_per_gram(snapshot: PriceSnapshot, metal: str, karat: str = "22K") -> float | None:
    """
    Returns the per-gram INR price for the given metal and karat.
    For gold, uses karat-specific prices if available.
    For silver/platinum, returns price_inr converted to per-gram.
    """
    metal_data = snapshot.metals.get(metal)
    if not metal_data:
        return None

    if metal == "gold":
        if karat == "24K" and metal_data.price_24k_inr:
            return metal_data.price_24k_inr
        if metal_data.price_22k_inr:
            return metal_data.price_22k_inr
        # Fallback: convert troy oz INR to per gram
        if metal_data.price_inr:
            return round(metal_data.price_inr / 31.1035, 2)
        return None

    # Silver, platinum — price_inr is per troy oz, convert to per gram
    if metal_data.price_inr:
        return round(metal_data.price_inr / 31.1035, 2)

    return None


def is_triggered(alert: AlertPreference, current_price: float) -> bool:
    if alert.direction == "below":
        return current_price <= alert.threshold_inr
    if alert.direction == "above":
        return current_price >= alert.threshold_inr
    return False
