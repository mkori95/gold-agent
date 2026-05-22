"""
alert_manager.py

Handles alert listing and removal for WhatsApp users.
"""

import re
from src.shared.db.dynamo_reader import get_user_alerts
from src.shared.db.dynamo_writer import deactivate_alert
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)

_METAL_PATTERNS = {
    "gold":     [r"gold", r"sona", r"sonar", r"सोना", r"தங்கம்", r"బంగారం"],
    "silver":   [r"silver", r"chandi", r"चांदी", r"வெள்ளி", r"వెండి"],
    "platinum": [r"platinum", r"प्लेटिनम", r"பிளாட்டினம்", r"ప్లాటినం"],
}

_METAL_NAMES = {
    "gold":     {"en": "Gold",      "hi": "सोना",      "ta": "தங்கம்",       "te": "బంగారం"},
    "silver":   {"en": "Silver",    "hi": "चांदी",     "ta": "வெள்ளி",       "te": "వెండి"},
    "platinum": {"en": "Platinum",  "hi": "प्लेटिनम",  "ta": "பிளாட்டினம்",  "te": "ప్లాటినం"},
}

_DIRECTION_WORDS = {
    "below": {"en": "below", "hi": "नीचे", "ta": "கீழே", "te": "కింద"},
    "above": {"en": "above", "hi": "ऊपर",  "ta": "மேலே", "te": "పైన"},
}

_NO_ALERTS = {
    "en": (
        "You don't have any active alerts yet.\n\n"
        "To set one, say:\n"
        "\"Alert me when gold drops below ₹6500/gram\""
    ),
    "hi": (
        "आपका कोई सक्रिय अलर्ट नहीं है।\n\n"
        "सेट करने के लिए कहें:\n"
        "\"जब सोना ₹6500/gram से नीचे जाए तो बताना\""
    ),
    "ta": (
        "உங்களுக்கு எந்த செயல்பாட்டு எச்சரிக்கையும் இல்லை.\n\n"
        "அமைக்க: \"தங்கம் ₹6500/gram கீழே போனால் சொல்லு\""
    ),
    "te": (
        "మీకు ఏ చురుకైన హెచ్చరికలు లేవు.\n\n"
        "సెట్ చేయడానికి: \"బంగారం ₹6500/gram కంటే తక్కువ అయితే చెప్పు\""
    ),
}

_LIST_HEADER = {
    "en": "📋 *Your active alerts:*\n",
    "hi": "📋 *आपके सक्रिय अलर्ट:*\n",
    "ta": "📋 *உங்கள் செயல்பாட்டு எச்சரிக்கைகள்:*\n",
    "te": "📋 *మీ చురుకైన హెచ్చరికలు:*\n",
}

_LIST_FOOTER = {
    "en": "\nTo remove one, say \"remove my gold alert\".",
    "hi": "\nहटाने के लिए कहें: \"मेरा सोना अलर्ट हटाओ\"।",
    "ta": "\nநீக்க: \"என் தங்கம் எச்சரிக்கையை நீக்கு\" என்று சொல்லுங்கள்.",
    "te": "\nతొలగించడానికి: \"నా బంగారం హెచ్చరిక తొలగించు\" అని చెప్పండి.",
}

_REMOVED = {
    "en": "✅ Removed your *{metal}* alert (notify when {direction} ₹{threshold:,.0f}/gram).",
    "hi": "✅ आपका *{metal}* अलर्ट हटा दिया गया (₹{threshold:,.0f}/gram से {direction_word} होने पर)।",
    "ta": "✅ உங்கள் *{metal}* எச்சரிக்கை நீக்கப்பட்டது (₹{threshold:,.0f}/gram {direction_word}).",
    "te": "✅ మీ *{metal}* హెచ్చరిక తొలగించబడింది (₹{threshold:,.0f}/gram {direction_word}).",
}

_NO_ALERT_FOR_METAL = {
    "en": "You don't have an active *{metal}* alert to remove.",
    "hi": "आपका कोई सक्रिय *{metal}* अलर्ट नहीं है।",
    "ta": "உங்களுக்கு *{metal}* எச்சரிக்கை இல்லை.",
    "te": "మీకు *{metal}* హెచ్చరిక లేదు.",
}

_WHICH_TO_REMOVE = {
    "en": (
        "Which alert would you like to remove?\n"
        "You have active alerts for: {metals}.\n\n"
        "Say \"remove my gold alert\" or \"remove my silver alert\"."
    ),
    "hi": (
        "कौन सा अलर्ट हटाना है?\n"
        "आपके पास {metals} के अलर्ट हैं।\n\n"
        "\"मेरा सोना अलर्ट हटाओ\" कहें।"
    ),
    "ta": (
        "எந்த எச்சரிக்கையை நீக்க வேண்டும்?\n"
        "{metals} எச்சரிக்கைகள் உள்ளன."
    ),
    "te": (
        "ఏ హెచ్చరిక తొలగించాలి?\n"
        "{metals} హెచ్చరికలు ఉన్నాయి."
    ),
}


def _extract_metal(text: str):
    lower = text.lower()
    for metal, patterns in _METAL_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, lower):
                return metal
    return None


def _metal_name(metal: str, lang: str) -> str:
    return _METAL_NAMES.get(metal, {}).get(lang, metal.capitalize())


def handle_alert_remove(phone_number: str, message: str, language: str) -> str:
    lang = language if language in _NO_ALERTS else "en"

    alerts = get_user_alerts(phone_number)
    active = [a for a in alerts if a.is_active]

    if not active:
        return _NO_ALERTS[lang]

    metal = _extract_metal(message)

    if metal is None:
        if len(active) == 1:
            metal = active[0].metal
        else:
            metals_str = ", ".join(_metal_name(a.metal, lang) for a in active)
            return _WHICH_TO_REMOVE[lang].format(metals=metals_str)

    to_remove = [a for a in active if a.metal == metal]
    if not to_remove:
        return _NO_ALERT_FOR_METAL[lang].format(metal=_metal_name(metal, lang))

    for alert in to_remove:
        deactivate_alert(phone_number, alert.alert_id)
        logger.info(f"Alert deactivated: {alert.alert_id} — {phone_number}")

    a = to_remove[0]
    direction_word = _DIRECTION_WORDS.get(a.direction, {}).get(lang, a.direction)
    return _REMOVED[lang].format(
        metal=_metal_name(metal, lang),
        threshold=a.threshold_inr,
        direction=a.direction,
        direction_word=direction_word,
    )


def handle_alert_list(phone_number: str, language: str) -> str:
    lang = language if language in _NO_ALERTS else "en"

    alerts = get_user_alerts(phone_number)
    active = [a for a in alerts if a.is_active]

    if not active:
        return _NO_ALERTS[lang]

    lines = [_LIST_HEADER[lang]]
    for a in active:
        direction_word = _DIRECTION_WORDS.get(a.direction, {}).get(lang, a.direction)
        lines.append(
            f"• *{_metal_name(a.metal, lang)}* — "
            f"{direction_word} ₹{a.threshold_inr:,.0f}/gram ({a.karat})"
        )

    lines.append(_LIST_FOOTER[lang])
    return "\n".join(lines)
