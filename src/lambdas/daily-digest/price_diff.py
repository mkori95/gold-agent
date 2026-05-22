from datetime import date, timedelta
from typing import Optional
from src.shared.db.s3_reader import get_snapshot_for_date, get_price_for_metal


def _fmt_diff(current: Optional[float], previous: Optional[float]) -> str:
    """Returns a formatted diff string like '+₹234' or '-₹156' or 'N/A'."""
    if current is None or previous is None:
        return "N/A"
    diff = round(current - previous, 0)
    sign = "+" if diff >= 0 else ""
    return f"{sign}₹{abs(int(diff)):,}"


def get_price_diffs(today: date) -> dict:
    """
    Returns price diffs for gold and silver vs yesterday and last week.
    Falls back to nearest available snapshot if exact date is missing.
    Always returns the actual date used for comparison so it can be shown to users.

    Return structure:
    {
        "yesterday": {
            "date": "21 May 2026",
            "gold_22k": "+₹234",
            "gold_24k": "+₹255",
            "gold_18k": "+₹192",
            "silver":   "-₹12",
            "platinum": "N/A",
        },
        "last_week": { ... same shape ... }
    }
    """
    today_snap, _ = get_snapshot_for_date(today)

    result = {}
    for label, target_date in [
        ("yesterday", today - timedelta(days=1)),
        ("last_week", today - timedelta(days=7)),
    ]:
        snap, actual_date = get_snapshot_for_date(target_date)
        if snap is None or today_snap is None:
            result[label] = {"date": actual_date or "unavailable"}
            continue

        today_gold  = get_price_for_metal(today_snap, "gold")
        today_silver = get_price_for_metal(today_snap, "silver")
        today_plat  = get_price_for_metal(today_snap, "platinum")

        prev_gold   = get_price_for_metal(snap, "gold")
        prev_silver = get_price_for_metal(snap, "silver")
        prev_plat   = get_price_for_metal(snap, "platinum")

        result[label] = {
            "date":      actual_date,
            "gold_22k":  _fmt_diff(today_gold["price_22k"],    prev_gold["price_22k"]),
            "gold_24k":  _fmt_diff(today_gold["price_24k"],    prev_gold["price_24k"]),
            "gold_18k":  _fmt_diff(today_gold["price_18k"],    prev_gold["price_18k"]),
            "silver":    _fmt_diff(today_silver["price_per_gram"], prev_silver["price_per_gram"]),
            "platinum":  _fmt_diff(today_plat["price_per_gram"],   prev_plat["price_per_gram"]),
        }

    return result
