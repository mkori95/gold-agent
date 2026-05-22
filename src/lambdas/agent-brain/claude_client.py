import anthropic
import os
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)

MODEL_SONNET = "claude-sonnet-4-6"
MODEL_HAIKU = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024

# Only alert_setup extraction is safe for Haiku — it's pure JSON parsing with no price context.
# All intents that use live price data must use Sonnet; Haiku 4.5 does not reliably follow
# context-grounded instructions for price data, especially with Indian number formatting.
_HAIKU_INTENTS = set()  # reserved for future use when a suitable task is identified

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def model_for_intent(intent: str) -> str:
    return MODEL_HAIKU if intent in _HAIKU_INTENTS else MODEL_SONNET


def ask(system_prompt: str, history: list[dict], user_message: str, intent: str = "unknown") -> str:
    """
    Call Claude with conversation history and return the reply text.
    history: list of {"role": "user"|"assistant", "content": "..."}
    """
    messages = history + [{"role": "user", "content": user_message}]
    model = model_for_intent(intent)

    client = _get_client()
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=messages,
    )

    reply = response.content[0].text
    logger.info(f"Claude reply ({len(reply)} chars) model={model} intent={intent} "
                f"input_tokens={response.usage.input_tokens}, "
                f"output_tokens={response.usage.output_tokens}")
    return reply
