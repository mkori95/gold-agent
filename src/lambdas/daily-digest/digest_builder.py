from datetime import date, datetime, timezone, timedelta
from typing import Optional
from src.shared.models.price import PriceSnapshot
from src.shared.models.user import User

IST = timezone(timedelta(hours=5, minutes=30))

# Must match the exact template name approved by Meta
DAILY_DIGEST_TEMPLATE_NAME = "gold_agent_daily_update"


def _city_22k_price(snapshot: PriceSnapshot, city: Optional[str]) -> Optional[float]:
    """Returns 22K per-gram price for user's city if available, else national average."""
    gold = snapshot.metals.get("gold")
    if not gold:
        return None
    if city and gold.city_rates:
        city_key = city.lower().replace(" ", "-")
        raw = gold.city_rates.get(city_key)
        if raw:
            try:
                return round(float(raw) / 10, 0)
            except (ValueError, TypeError):
                pass
    return gold.price_22k_inr


def _fmt_price(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{int(round(value)):,}"


def _ist_time(iso_str: str) -> str:
    """Convert ISO UTC timestamp to IST time string like '11:45 AM'."""
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST).strftime("%-I:%M %p")
    except Exception:
        return "—"


def build_template_params(user: User, snapshot: PriceSnapshot, diffs: dict) -> list:
    """
    Returns 16 string values for the daily_metal_digest template variables:

    {{1}}  city                {{2}}  date
    {{3}}  24K price           {{4}}  24K today diff    {{5}}  24K week diff
    {{6}}  22K price           {{7}}  22K today diff    {{8}}  22K week diff
    {{9}}  18K price
    {{10}} silver price        {{11}} silver today diff {{12}} silver week diff
    {{13}} platinum price
    {{14}} updated time (IST)  {{15}} yesterday date   {{16}} last week date
    """
    gold     = snapshot.metals.get("gold")
    silver   = snapshot.metals.get("silver")
    platinum = snapshot.metals.get("platinum")

    today_str  = datetime.now(IST).strftime("%-d %b %Y")
    city_label = user.city or "India"

    p22    = _fmt_price(_city_22k_price(snapshot, user.city))
    p24    = _fmt_price(gold.price_24k_inr if gold else None)
    p18    = _fmt_price(gold.price_18k_inr if gold else None)
    p_sil  = _fmt_price(round(silver.price_inr / 31.1035, 0) if silver and silver.price_inr else None)
    p_plat = _fmt_price(round(platinum.price_inr / 31.1035, 0) if platinum and platinum.price_inr else None)

    yday = diffs.get("yesterday", {})
    week = diffs.get("last_week", {})

    return [
        city_label,                       # {{1}}
        today_str,                        # {{2}}
        p24,                              # {{3}}
        yday.get("gold_24k", "N/A"),      # {{4}}
        week.get("gold_24k", "N/A"),      # {{5}}
        p22,                              # {{6}}
        yday.get("gold_22k", "N/A"),      # {{7}}
        week.get("gold_22k", "N/A"),      # {{8}}
        p18,                              # {{9}}
        p_sil,                            # {{10}}
        yday.get("silver", "N/A"),        # {{11}}
        week.get("silver", "N/A"),        # {{12}}
        p_plat,                           # {{13}}
        _ist_time(snapshot.timestamp),    # {{14}}
        yday.get("date", "unavailable"),  # {{15}}
        week.get("date", "unavailable"),  # {{16}}
    ]
