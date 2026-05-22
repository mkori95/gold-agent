from datetime import datetime, timezone, timedelta
from src.shared.models.alert import AlertPreference

COOLDOWN_HOURS = 12  # don't re-alert within 12 hours of last trigger


def is_in_cooldown(alert: AlertPreference) -> bool:
    if not alert.last_triggered:
        return False
    try:
        last = datetime.fromisoformat(alert.last_triggered)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - last) < timedelta(hours=COOLDOWN_HOURS)
    except ValueError:
        return False
