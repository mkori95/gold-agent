from typing import Optional
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


def parse_incoming(body: dict) -> Optional[dict]:
    """
    Extract the first actionable message from a Meta webhook payload.
    Returns a flat dict or None if the payload has no actionable message.

    Text:  {"type": "text",  "text": "...",      "from": ..., "message_id": ..., "name": ..., "timestamp": ...}
    Audio: {"type": "audio", "media_id": "...",  "from": ..., "message_id": ..., "name": ..., "timestamp": ...}
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

        contacts = value.get("contacts", [{}])
        contact = contacts[0] if contacts else {}

        base = {
            "message_id": msg["id"],
            "from": msg["from"],
            "timestamp": msg.get("timestamp", ""),
            "name": contact.get("profile", {}).get("name", ""),
        }

        if msg_type == "text":
            return {**base, "type": "text", "text": msg["text"]["body"]}

        if msg_type == "audio":
            return {**base, "type": "audio", "media_id": msg["audio"]["id"]}

        if msg_type == "button":
            # Template quick-reply button click — payload or text used for intent classification
            button = msg.get("button", {})
            text = button.get("payload") or button.get("text", "")
            return {**base, "type": "text", "text": text}

        if msg_type == "interactive":
            interactive = msg.get("interactive", {})
            if interactive.get("type") == "button_reply":
                button = interactive["button_reply"]
                text = button.get("id") or button.get("title", "")
                return {**base, "type": "text", "text": text}

        logger.info(f"Ignoring unsupported message type: {msg_type}")
        return None

    except (KeyError, IndexError) as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        return None
