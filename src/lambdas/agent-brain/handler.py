"""
agent-brain Lambda — entry point.

Invoked asynchronously by whatsapp-handler for every non-trivial intent.
Builds context from DynamoDB, calls Claude, sends WhatsApp reply.
"""

import json
from src.lambdas.agent_brain.context_builder import build_price_context
from src.lambdas.agent_brain.prompt_builder import build_system_prompt
from src.lambdas.agent_brain.claude_client import ask
from src.lambdas.agent_brain.language_handler import append_language_reminder
from src.lambdas.whatsapp_handler.session_manager import load_history, save_turn, format_history_for_claude
from src.lambdas.conversation.alert_setup import handle as handle_alert_setup
from src.shared.notifications.whatsapp_client import send_text
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)

# Intents handled by dedicated logic — NOT passed to Claude for action
_DEDICATED_HANDLERS = {"alert_setup"}


def handler(event: dict, context) -> dict:
    """
    Expected event payload:
    {
        "phone_number": "+919876543210",
        "message": "What is gold price today?",
        "language": "en",
        "intent": "price_query",
        "city": "Chennai"
    }
    """
    phone_number = event.get("phone_number", "")
    message = event.get("message", "")
    language = event.get("language", "en")
    intent = event.get("intent", "price_query")
    city = event.get("city", "")

    logger.info(f"agent-brain processing: user={phone_number} intent={intent} lang={language}")

    try:
        # --- alert_setup: extract params → write DynamoDB → confirm ---
        # Claude is NOT used to "handle" this — only to extract structured data.
        # The backend sets the alert; we confirm only after it's written.
        if intent == "alert_setup":
            reply = handle_alert_setup(phone_number, message, language)
            save_turn(phone_number, message, reply)
            send_text(phone_number, reply)
            logger.info(f"Alert setup reply sent to {phone_number}")
            return {"status": "ok"}

        # --- All other intents: Claude answers with live price context ---
        price_context = build_price_context(city=city or None)
        system_prompt = build_system_prompt(language, price_context)

        history_records = load_history(phone_number, limit=6)
        history = format_history_for_claude(history_records)

        user_message = append_language_reminder(message, language)
        reply = ask(system_prompt, history, user_message)

        save_turn(phone_number, message, reply)
        send_text(phone_number, reply)

        logger.info(f"Reply sent to {phone_number}")
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"agent-brain error for {phone_number}: {e}", exc_info=True)
        send_text(
            phone_number,
            "Sorry, something went wrong. Please try again in a few minutes."
        )
        return {"status": "error", "error": str(e)}
