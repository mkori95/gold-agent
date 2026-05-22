import os
from datetime import datetime, timezone
from src.shared.db.dynamo_client import get_table
from src.shared.models.user import User
from src.shared.models.alert import AlertPreference
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)

TABLE_USERS = os.environ.get("DYNAMO_TABLE_USERS", "gold-agent-users")
TABLE_ALERTS = os.environ.get("DYNAMO_TABLE_ALERT_PREFERENCES", "gold-agent-alert-preferences")
TABLE_HISTORY = os.environ.get("DYNAMO_TABLE_CONVERSATION_HISTORY", "gold-agent-conversation-history")


def put_user(user: User) -> None:
    table = get_table(TABLE_USERS)
    table.put_item(Item=user.to_dynamo())
    logger.info(f"User saved: {user.phone_number}")


def update_user_seen(phone_number: str) -> None:
    table = get_table(TABLE_USERS)
    table.update_item(
        Key={"phone_number": phone_number},
        UpdateExpression="SET last_seen = :ts ADD message_count :one",
        ExpressionAttributeValues={
            ":ts": datetime.now(timezone.utc).isoformat(),
            ":one": 1,
        },
    )


def put_alert(alert: AlertPreference) -> None:
    table = get_table(TABLE_ALERTS)
    table.put_item(Item=alert.to_dynamo())
    logger.info(f"Alert saved: {alert.alert_id}")


def deactivate_alert(phone_number: str, alert_id: str) -> None:
    table = get_table(TABLE_ALERTS)
    table.update_item(
        Key={"phone_number": phone_number, "alert_id": alert_id},
        UpdateExpression="SET is_active = :f",
        ExpressionAttributeValues={":f": False},
    )


def record_alert_trigger(phone_number: str, alert_id: str) -> None:
    table = get_table(TABLE_ALERTS)
    table.update_item(
        Key={"phone_number": phone_number, "alert_id": alert_id},
        UpdateExpression="SET last_triggered = :ts ADD trigger_count :one",
        ExpressionAttributeValues={
            ":ts": datetime.now(timezone.utc).isoformat(),
            ":one": 1,
        },
    )


def toggle_daily_summary(phone_number: str, enabled: bool) -> None:
    table = get_table(TABLE_USERS)
    table.update_item(
        Key={"phone_number": phone_number},
        UpdateExpression="SET daily_summary = :v",
        ExpressionAttributeValues={":v": enabled},
    )
    logger.info(f"daily_summary={'on' if enabled else 'off'} for {phone_number}")


def put_conversation_turn(phone_number: str, role: str, message: str) -> None:
    table = get_table(TABLE_HISTORY)
    ts = datetime.now(timezone.utc).isoformat()
    table.put_item(Item={
        "phone_number": phone_number,
        "timestamp": ts,
        "role": role,
        "message": message,
    })
