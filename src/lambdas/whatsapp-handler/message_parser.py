from typing import Optional
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


def parse_incoming(body: dict) -> Optional[dict]:
    """
    Extract the first text message from a Meta webhook payload.
    Returns a flat dict or None if the payload has no actionable message.
    """
    try:
        entries = body.get("entry", [])
        if not isinstance(entries, list) or not entries:
            return None
        entry = entries[0]
        if not isinstance(entry, dict):
            return None
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})

        messages = value.get("messages", [])
        if not messages:
            return None  # status update, not a message

        msg = messages[0]
        msg_type = msg.get("type")

        if msg_type != "text":
            # Phase 2 handles text only; audio/image deferred to Phase 3
            logger.info(f"Ignoring non-text message type: {msg_type}")
            return None

        contacts = value.get("contacts", [{}])
        contact = contacts[0] if contacts else {}

        return {
            "message_id": msg["id"],
            "from": msg["from"],                      # sender phone number
            "text": msg["text"]["body"],
            "timestamp": msg.get("timestamp", ""),
            "name": contact.get("profile", {}).get("name", ""),
        }
    except (KeyError, IndexError) as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        return None
