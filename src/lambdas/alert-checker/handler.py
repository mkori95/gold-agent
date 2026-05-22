"""
alert-checker Lambda — entry point.

Runs hourly via EventBridge. Scans all active alerts, checks against
live prices, sends WhatsApp notifications if thresholds are breached.
"""

from src.shared.db.dynamo_reader import get_all_active_alerts, get_latest_snapshot
from src.lambdas.alert_checker.threshold_checker import get_current_price_per_gram, is_triggered
from src.lambdas.alert_checker.alert_trigger import trigger_alert
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


def handler(event: dict, context) -> dict:
    logger.info("alert-checker started")

    snapshot = get_latest_snapshot()
    if snapshot is None:
        logger.warning("No price snapshot available — skipping alert check")
        return {"status": "skipped", "reason": "no_snapshot"}

    alerts = get_all_active_alerts()
    logger.info(f"Checking {len(alerts)} active alerts against snapshot {snapshot.snapshot_date}")

    sent = 0
    skipped = 0

    for alert in alerts:
        current_price = get_current_price_per_gram(snapshot, alert.metal, alert.karat)
        if current_price is None:
            logger.warning(f"No price for {alert.metal} — skipping alert {alert.alert_id}")
            skipped += 1
            continue

        if is_triggered(alert, current_price):
            was_sent = trigger_alert(alert, current_price)
            sent += 1 if was_sent else 0
        else:
            skipped += 1

    logger.info(f"Alert run complete: {sent} sent, {skipped} skipped")
    return {"status": "ok", "sent": sent, "skipped": skipped}
