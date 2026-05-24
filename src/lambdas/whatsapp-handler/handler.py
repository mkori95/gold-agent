"""
whatsapp-handler Lambda — entry point.

Handles two event types from API Gateway:
  GET  /webhook  — Meta webhook verification challenge
  POST /webhook  — Incoming WhatsApp messages
"""

import json
import os
import boto3
from src.lambdas.whatsapp_handler.signature_validator import is_valid_signature
from src.lambdas.whatsapp_handler.message_parser import parse_incoming
from src.lambdas.whatsapp_handler.language_detector import detect_language
from src.lambdas.whatsapp_handler.intent_classifier import classify_intent
from src.lambdas.whatsapp_handler.user_manager import get_or_create_user
from src.lambdas.whatsapp_handler.response_formatter import (
    help_message, summary_subscribe_message, summary_unsubscribe_message,
    summary_already_subscribed_message, summary_already_unsubscribed_message,
)
from src.shared.db.dynamo_writer import toggle_daily_summary
from src.shared.notifications.whatsapp_client import send_text, mark_read, download_media
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)

AGENT_BRAIN_FUNCTION = os.environ.get("AGENT_BRAIN_FUNCTION_NAME", "gold-agent-brain")
WHISPER_FUNCTION = os.environ.get("WHISPER_TRANSCRIBER_FUNCTION_NAME", "gold-agent-whisper-transcriber")
S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "gold-agent-prices")

_lambda_client = None
_s3_client = None


def _get_lambda_client():
    global _lambda_client
    if _lambda_client is None:
        _lambda_client = boto3.client("lambda", region_name=os.environ.get("AWS_REGION_NAME", "ap-south-1"))
    return _lambda_client


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3", region_name=os.environ.get("AWS_REGION_NAME", "ap-south-1"))
    return _s3_client


def handler(event: dict, context) -> dict:
    method = event.get("httpMethod", "POST")

    if method == "GET":
        return _handle_verification(event)

    if method == "POST":
        return _handle_message(event)

    return _response(405, {"error": "Method not allowed"})


def _handle_verification(event: dict) -> dict:
    """Meta calls GET /webhook to verify the endpoint during setup."""
    params = event.get("queryStringParameters") or {}
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")

    if mode == "subscribe" and token == verify_token:
        logger.info("Webhook verification successful")
        return {"statusCode": 200, "body": challenge}

    logger.warning(f"Webhook verification failed: mode={mode}, token={token}")
    return _response(403, {"error": "Verification failed"})


def _handle_message(event: dict) -> dict:
    """Process an incoming WhatsApp message."""
    raw_body = (event.get("body") or "").encode("utf-8")
    sig = (event.get("headers") or {}).get("x-hub-signature-256", "")

    if not is_valid_signature(raw_body, sig):
        logger.warning("Invalid webhook signature — rejected")
        return _response(401, {"error": "Invalid signature"})

    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        return _response(400, {"error": "Invalid JSON"})

    msg = parse_incoming(body)
    if msg is None:
        # Status update or unsupported type — acknowledge and ignore
        return _response(200, {"status": "ok"})

    if msg.get("type") == "audio":
        return _handle_audio(msg)

    phone_number = msg["from"]
    text = msg["text"]
    message_id = msg["message_id"]
    name = msg.get("name", "")

    # Detect language from the message text
    language = detect_language(text)

    # Get or create user
    user = get_or_create_user(phone_number, name, language)

    # Use stored language preference if user already exists and has one set
    effective_language = user.language if user.language != "en" else language

    # Mark message as read
    try:
        mark_read(message_id)
    except Exception as e:
        logger.warning(f"Could not mark message as read: {e}")

    # Classify intent
    intent = classify_intent(text)
    logger.info(f"User={phone_number} intent={intent} lang={effective_language}")

    if intent == "help" or intent == "greeting":
        send_text(phone_number, help_message(effective_language))
        return _response(200, {"status": "ok"})

    if intent == "summary_subscribe":
        if user.daily_summary:
            send_text(phone_number, summary_already_subscribed_message(effective_language))
        else:
            toggle_daily_summary(phone_number, enabled=True)
            send_text(phone_number, summary_subscribe_message(effective_language))
        return _response(200, {"status": "ok"})

    if intent == "summary_unsubscribe":
        if not user.daily_summary:
            send_text(phone_number, summary_already_unsubscribed_message(effective_language))
        else:
            toggle_daily_summary(phone_number, enabled=False)
            send_text(phone_number, summary_unsubscribe_message(effective_language))
        return _response(200, {"status": "ok"})

    # For all other intents (including "unknown") — invoke agent-brain async.
    # Unknown messages often continue a prior conversation thread; let Claude
    # decide what to do using conversation history instead of dropping them.
    _invoke_agent_brain(phone_number, text, effective_language, intent, user.city)

    return _response(200, {"status": "ok"})


def _handle_audio(msg: dict) -> dict:
    """Download voice note from Meta, upload to S3, kick off async transcription."""
    phone_number = msg["from"]
    message_id = msg["message_id"]
    name = msg.get("name", "")

    try:
        mark_read(message_id)
    except Exception as e:
        logger.warning(f"Could not mark message as read: {e}")

    user = get_or_create_user(phone_number, name, "en")
    effective_language = user.language if user.language != "en" else "en"

    try:
        ogg_bytes = download_media(msg["media_id"])
        s3_key = f"voice-temp/{message_id}.ogg"
        _get_s3_client().put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=ogg_bytes,
            ContentType="audio/ogg",
        )
        _invoke_whisper_transcriber(
            phone_number=phone_number,
            s3_key=s3_key,
            language_hint=effective_language,
            city=user.city or "",
        )
        logger.info(f"Voice note queued for transcription: {phone_number}")
    except Exception as e:
        logger.error(f"Audio handling failed for {phone_number}: {e}")
        send_text(phone_number, "Sorry, I couldn't process that voice note. Please send a text message instead.")

    return _response(200, {"status": "ok"})


def _invoke_whisper_transcriber(phone_number: str, s3_key: str, language_hint: str, city: str) -> None:
    payload = {
        "s3_bucket": S3_BUCKET,
        "s3_key": s3_key,
        "phone_number": phone_number,
        "city": city,
        "language_hint": language_hint,
    }
    _get_lambda_client().invoke(
        FunctionName=WHISPER_FUNCTION,
        InvocationType="Event",
        Payload=json.dumps(payload).encode("utf-8"),
    )


def _invoke_agent_brain(phone_number: str, text: str, language: str, intent: str, city: str) -> None:
    payload = {
        "phone_number": phone_number,
        "message": text,
        "language": language,
        "intent": intent,
        "city": city or "",
    }
    try:
        _get_lambda_client().invoke(
            FunctionName=AGENT_BRAIN_FUNCTION,
            InvocationType="Event",  # async — fire and forget
            Payload=json.dumps(payload).encode("utf-8"),
        )
        logger.info(f"agent-brain invoked async for {phone_number}")
    except Exception as e:
        logger.error(f"Failed to invoke agent-brain: {e}")
        # Send a fallback message so the user isn't left hanging
        send_text(phone_number, "Sorry, something went wrong. Please try again in a moment.")


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
