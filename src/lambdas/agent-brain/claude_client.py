import anthropic
import os
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def ask(system_prompt: str, history: list[dict], user_message: str) -> str:
    """
    Call Claude with conversation history and return the reply text.
    history: list of {"role": "user"|"assistant", "content": "..."}
    """
    messages = history + [{"role": "user", "content": user_message}]

    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},  # cache system prompt across turns
            }
        ],
        messages=messages,
    )

    reply = response.content[0].text
    logger.info(f"Claude reply ({len(reply)} chars), "
                f"input_tokens={response.usage.input_tokens}, "
                f"output_tokens={response.usage.output_tokens}")
    return reply
