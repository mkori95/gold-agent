from src.shared.models.alert import AlertPreference
from src.shared.notifications.whatsapp_client import send_text
from src.shared.db.dynamo_writer import record_alert_trigger
from src.lambdas.alert_checker.alert_formatter import format_alert
from src.lambdas.alert_checker.cooldown_manager import is_in_cooldown
from src.shared.db.dynamo_reader import get_user
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


def trigger_alert(alert: AlertPreference, current_price: float) -> bool:
    """
    Send a WhatsApp alert if not in cooldown.
    Returns True if alert was sent.
    """
    if is_in_cooldown(alert):
        logger.info(f"Alert in cooldown: {alert.alert_id}")
        return False

    user = get_user(alert.phone_number)
    language = user.language if user else "en"

    message = format_alert(alert, current_price, language)

    try:
        send_text(alert.phone_number, message)
        record_alert_trigger(alert.phone_number, alert.alert_id)
        logger.info(f"Alert sent: {alert.alert_id} to {alert.phone_number}")
        return True
    except Exception as e:
        logger.error(f"Failed to send alert {alert.alert_id}: {e}")
        return False
