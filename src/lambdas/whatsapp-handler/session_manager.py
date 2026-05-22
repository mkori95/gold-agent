from datetime import datetime, timezone, timedelta
from src.shared.db.dynamo_reader import get_conversation_history
from src.shared.db.dynamo_writer import put_conversation_turn
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)

SESSION_TIMEOUT_MINUTES = 30


def load_history(phone_number: str, limit: int = 10) -> list[dict]:
    """
    Returns recent conversation turns for context.
    Returns empty list if the last message is older than SESSION_TIMEOUT_MINUTES,
    so stale conversations don't confuse the current exchange.
    """
    turns = get_conversation_history(phone_number, limit=limit)
    if not turns:
        return []

    last_turn = turns[-1]
    try:
        last_time = datetime.fromisoformat(last_turn.get("timestamp", ""))
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        if last_time < cutoff:
            logger.info(f"Session expired for {phone_number} — starting fresh context")
            return []
    except (ValueError, TypeError):
        pass

    return turns


def save_turn(phone_number: str, user_message: str, assistant_reply: str) -> None:
    put_conversation_turn(phone_number, "user", user_message)
    put_conversation_turn(phone_number, "assistant", assistant_reply)


def format_history_for_claude(turns: list[dict]) -> list[dict]:
    """Convert DynamoDB turn records to Claude messages format."""
    return [{"role": t["role"], "content": t["message"]} for t in turns]
