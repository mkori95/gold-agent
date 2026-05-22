from src.shared.models.user import User
from src.shared.db.dynamo_reader import get_user
from src.shared.db.dynamo_writer import put_user, update_user_seen
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


def get_or_create_user(phone_number: str, name: str, detected_language: str) -> User:
    """
    Fetch existing user from DynamoDB or create a new one.
    On every call, bump last_seen and message_count.
    """
    user = get_user(phone_number)

    if user is None:
        user = User(
            phone_number=phone_number,
            name=name or None,
            language=detected_language,
        )
        put_user(user)
        logger.info(f"New user created: {phone_number}")
    else:
        update_user_seen(phone_number)

    return user


def update_user_language(phone_number: str, language: str) -> None:
    user = get_user(phone_number)
    if user:
        user.language = language
        put_user(user)
