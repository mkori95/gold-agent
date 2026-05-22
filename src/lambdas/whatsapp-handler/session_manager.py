from src.shared.db.dynamo_reader import get_conversation_history
from src.shared.db.dynamo_writer import put_conversation_turn
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


def load_history(phone_number: str, limit: int = 5) -> list[dict]:
    """Returns the last N conversation turns for context."""
    return get_conversation_history(phone_number, limit=limit)


def save_turn(phone_number: str, user_message: str, assistant_reply: str) -> None:
    put_conversation_turn(phone_number, "user", user_message)
    put_conversation_turn(phone_number, "assistant", assistant_reply)


def format_history_for_claude(turns: list[dict]) -> list[dict]:
    """Convert DynamoDB turn records to Claude messages format."""
    return [{"role": t["role"], "content": t["message"]} for t in turns]
