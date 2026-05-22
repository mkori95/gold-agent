import os
from typing import Optional
from boto3.dynamodb.conditions import Key
from src.shared.db.dynamo_client import get_table
from src.shared.models.user import User
from src.shared.models.price import PriceSnapshot
from src.shared.models.alert import AlertPreference
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)

TABLE_LIVE_PRICES = os.environ.get("DYNAMO_TABLE_LIVE_PRICES", "gold-agent-live-prices")
TABLE_USERS = os.environ.get("DYNAMO_TABLE_USERS", "gold-agent-users")
TABLE_ALERTS = os.environ.get("DYNAMO_TABLE_ALERT_PREFERENCES", "gold-agent-alert-preferences")
TABLE_HISTORY = os.environ.get("DYNAMO_TABLE_CONVERSATION_HISTORY", "gold-agent-conversation-history")


def get_latest_snapshot() -> Optional[PriceSnapshot]:
    """Returns the latest price snapshot by scanning all per-metal rows."""
    table = get_table(TABLE_LIVE_PRICES)
    resp = table.scan()
    items = resp.get("Items", [])
    if not items:
        return None
    return PriceSnapshot.from_dynamo_rows(items)


def get_user(phone_number: str) -> Optional[User]:
    table = get_table(TABLE_USERS)
    resp = table.get_item(Key={"phone_number": phone_number})
    item = resp.get("Item")
    return User.from_dynamo(item) if item else None


def get_user_alerts(phone_number: str) -> list[AlertPreference]:
    table = get_table(TABLE_ALERTS)
    resp = table.query(
        KeyConditionExpression=Key("phone_number").eq(phone_number)
    )
    return [AlertPreference.from_dynamo(i) for i in resp.get("Items", [])]


def get_all_active_alerts() -> list[AlertPreference]:
    table = get_table(TABLE_ALERTS)
    resp = table.scan(
        FilterExpression="is_active = :t",
        ExpressionAttributeValues={":t": True},
    )
    return [AlertPreference.from_dynamo(i) for i in resp.get("Items", [])]


def get_conversation_history(phone_number: str, limit: int = 5) -> list[dict]:
    table = get_table(TABLE_HISTORY)
    resp = table.query(
        KeyConditionExpression=Key("phone_number").eq(phone_number),
        ScanIndexForward=False,
        Limit=limit,
    )
    turns = resp.get("Items", [])
    return list(reversed(turns))
