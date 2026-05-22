"""
daily-digest Lambda — entry point.

Triggered by EventBridge at 11:45 AM IST (06:15 UTC) daily.
Sends a WhatsApp price summary to all opted-in subscribers.
"""

from datetime import date, timezone, datetime
from src.shared.db.dynamo_reader import get_latest_snapshot, get_summary_subscribers
from src.shared.notifications.whatsapp_client import send_text
from src.lambdas.daily_digest.digest_builder import build_message
from src.lambdas.daily_digest.price_diff import get_price_diffs
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


def handler(event: dict, context) -> dict:
    today = date.today()
    logger.info(f"Daily digest starting — {today}")

    snapshot = get_latest_snapshot()
    if snapshot is None:
        logger.error("Daily digest: no price snapshot available — aborting")
        return {"status": "error", "reason": "no snapshot"}

    diffs = get_price_diffs(today)
    subscribers = get_summary_subscribers()

    logger.info(f"Daily digest: {len(subscribers)} subscribers")

    sent = 0
    failed = 0

    for user in subscribers:
        try:
            message = build_message(
                user=user,
                snapshot=snapshot,
                diffs=diffs,
                language=user.language,
            )
            send_text(user.phone_number, message)
            sent += 1
        except Exception as e:
            logger.error(f"Daily digest failed for {user.phone_number}: {e}")
            failed += 1

    logger.info(f"Daily digest complete — sent={sent} failed={failed}")
    return {"status": "ok", "sent": sent, "failed": failed}
