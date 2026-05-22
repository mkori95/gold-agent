"""
alert_setup.py

Handles the full alert setup flow:
  1. Use Claude to extract structured params from any natural language in any language
  2. Write to DynamoDB if extraction succeeds
  3. Return an honest confirmation or a clarification request

This is called by agent-brain when intent == "alert_setup".
Claude is used ONLY for extraction — it does NOT claim to set the alert.
The backend sets the alert, then we confirm.
"""

import json
import os
import re
from typing import Optional

import anthropic

from src.shared.models.alert import AlertPreference
from src.shared.db.dynamo_writer import put_alert
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


# Claude extracts structured data — returns JSON only, no prose
_EXTRACT_PROMPT = """Extract price alert parameters from this message. Return ONLY valid JSON, nothing else — no explanation, no markdown.

Message: {message}

Return exactly this JSON structure:
{{
  "metal": "gold" | "silver" | "platinum" | null,
  "direction": "below" | "above" | null,
  "threshold_inr": <number in rupees per gram> | null,
  "karat": "22K" | "24K" | "999" | null
}}

Rules:
- metal: gold (sona/सोना/தங்கம்/బంగారం), silver (chandi/चांदी/வெள்ளி/వెండి), platinum
- direction: below = drops/gire/நீழே/కింద/se niche, above = rises/badhega/மேலே/పైన/se upar
- threshold_inr: the rupee amount per gram the user mentions (just the number)
- karat: "22K" default for gold unless user says 24K; "999" default for silver/platinum
- If metal, direction, or threshold_inr cannot be determined, set them to null
- Do not convert or calculate — extract as-is from the message"""


# ── Multilingual static messages ──────────────────────────────────────────────

_CONFIRMATION = {
    "en": (
        "✅ Alert set!\n\n"
        "*{metal}* — notify me when price goes *{direction}* ₹{threshold:,.0f}/gram ({karat}).\n\n"
        "I'll WhatsApp you the moment it crosses your target. "
        "To cancel this alert anytime, say \"remove my {metal_lower} alert\"."
    ),
    "hi": (
        "✅ अलर्ट सेट हो गया!\n\n"
        "*{metal}* — जब भाव ₹{threshold:,.0f}/gram से *{direction_word}* जाए तो WhatsApp करूँगा।\n\n"
        "अलर्ट हटाने के लिए कहें: \"मेरा {metal_lower} अलर्ट हटाओ\"।"
    ),
    "ta": (
        "✅ எச்சரிக்கை அமைக்கப்பட்டது!\n\n"
        "*{metal}* — விலை ₹{threshold:,.0f}/gram-ஐ *{direction_word}* போனால் WhatsApp செய்வேன்।\n\n"
        "நீக்க: \"என் {metal_lower} எச்சரிக்கையை நீக்கு\" என்று சொல்லுங்கள்।"
    ),
    "te": (
        "✅ హెచ్చరిక సెట్ చేయబడింది!\n\n"
        "*{metal}* — ధర ₹{threshold:,.0f}/gram కంటే *{direction_word}* అయినప్పుడు WhatsApp చేస్తాను.\n\n"
        "తొలగించడానికి: \"నా {metal_lower} హెచ్చరిక తొలగించు\" అని చెప్పండి."
    ),
}

_CLARIFICATION = {
    "en": (
        "To set an alert, I need three things: the metal, the direction, and your target price.\n\n"
        "Examples:\n"
        "\"Alert me when *gold drops below ₹6500/gram*\"\n"
        "\"Tell me when *silver goes above ₹80/gram*\"\n\n"
        "Which metal, which direction, and what price?"
    ),
    "hi": (
        "अलर्ट सेट करने के लिए तीन चीज़ें बताएं: धातु, दिशा, और target भाव।\n\n"
        "उदाहरण:\n"
        "\"जब *सोना ₹6500/gram से नीचे* जाए तो बताना\"\n"
        "\"जब *चांदी ₹80/gram से ऊपर* जाए तो alert करना\"\n\n"
        "कौन सी धातु, किस दिशा में, और कितने रुपये?"
    ),
    "ta": (
        "எச்சரிக்கை அமைக்க மூன்று விஷயங்கள் சொல்லுங்கள்: உலோகம், திசை, இலக்கு விலை.\n\n"
        "உதாரணங்கள்:\n"
        "\"*தங்கம் ₹6500/gram கீழே* போனால் சொல்லு\"\n"
        "\"*வெள்ளி ₹80/gram மேலே* போனால் தெரிவி\"\n\n"
        "எந்த உலோகம், எந்த திசை, எந்த விலை?"
    ),
    "te": (
        "హెచ్చరిక సెట్ చేయడానికి మూడు విషయాలు చెప్పండి: లోహం, దిశ, మీ లక్ష్య ధర.\n\n"
        "ఉదాహరణలు:\n"
        "\"*బంగారం ₹6500/gram కంటే తక్కువ* అయితే చెప్పు\"\n"
        "\"*వెండి ₹80/gram కంటే ఎక్కువ* అయితే తెలియజేయి\"\n\n"
        "ఏ లోహం, ఏ దిశ, ఎంత ధర?"
    ),
}

_METAL_NAMES = {
    "gold":     {"en": "Gold",      "hi": "सोना",      "ta": "தங்கம்",       "te": "బంగారం"},
    "silver":   {"en": "Silver",    "hi": "चांदी",     "ta": "வெள்ளி",       "te": "వెండి"},
    "platinum": {"en": "Platinum",  "hi": "प्लेटिनम",  "ta": "பிளாட்டினம்",  "te": "ప్లాటినం"},
}

_DIRECTION_WORDS = {
    "below": {"en": "below",  "hi": "नीचे",  "ta": "கீழே",  "te": "కింద"},
    "above": {"en": "above",  "hi": "ऊपर",   "ta": "மேலே",  "te": "పైన"},
}


# ── Core logic ─────────────────────────────────────────────────────────────────

def _extract_params(message: str) -> Optional[dict]:
    """
    Ask Claude to pull metal/direction/threshold from any natural language message.
    Returns a validated dict, or None if any required field is missing.
    """
    prompt = _EXTRACT_PROMPT.format(message=message)
    response = _get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"Claude returned non-JSON for alert extraction: {raw}")
        return None

    if not data.get("metal") or not data.get("direction") or not data.get("threshold_inr"):
        return None

    return data


def handle(phone_number: str, message: str, language: str) -> str:
    """
    Full alert setup flow. Returns the reply string to send to the user.
    This is the ONLY place that creates alerts — Claude never claims to do it.
    """
    lang = language if language in _CONFIRMATION else "en"

    params = _extract_params(message)

    if params is None:
        logger.info(f"Could not extract alert params for {phone_number}: '{message}'")
        return _CLARIFICATION[lang]

    metal = params["metal"]
    direction = params["direction"]
    threshold = float(params["threshold_inr"])
    karat = params.get("karat") or ("22K" if metal == "gold" else "999")

    alert = AlertPreference(
        phone_number=phone_number,
        metal=metal,
        direction=direction,
        threshold_inr=threshold,
        karat=karat,
    )
    put_alert(alert)
    logger.info(f"Alert created: {alert.alert_id} — {phone_number}")

    metal_name = _METAL_NAMES.get(metal, {}).get(lang, metal.capitalize())
    direction_word = _DIRECTION_WORDS.get(direction, {}).get(lang, direction)

    return _CONFIRMATION[lang].format(
        metal=metal_name,
        metal_lower=metal_name.lower(),
        direction=direction,
        direction_word=direction_word,
        threshold=threshold,
        karat=karat,
    )
