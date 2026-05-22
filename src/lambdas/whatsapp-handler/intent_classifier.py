import re

# Intent keywords — ordered most-specific first
_PATTERNS = [
    ("alert_setup", [
        r"alert", r"notify", r"notification", r"inform me",
        r"बताओ जब", r"अलर्ट", r"எச்சரிக்கை", r"హెచ్చరిక",
    ]),
    ("calculator", [
        r"how much gold", r"how many gram", r"kitna gram", r"calculate",
        r"కొనాలి", r"வாங்க", r"कितना", r"budget", r"rupee.*gram", r"gram.*rupee",
    ]),
    ("festival_advice", [
        r"diwali", r"akshaya tritiya", r"dhanteras", r"festival",
        r"त्योहार", r"दिवाली", r"பண்டிகை", r"పండుగ", r"shubh", r"good time to buy",
    ]),
    ("trend_query", [
        r"trend", r"rising", r"falling", r"going up", r"going down",
        r"ऊपर", r"नीचे", r"increase", r"decrease", r"forecast", r"predict",
    ]),
    ("price_query", [
        r"price", r"rate", r"cost", r"today", r"gold", r"silver", r"platinum",
        r"भाव", r"दाम", r"சோனா", r"வெள்ளி", r"விலை", r"ధర", r"బంగారం", r"రేటు",
        r"sona", r"chandi", r"kya hai", r"kitna hai",
    ]),
    ("greeting", [
        r"^hi$", r"^hello$", r"^hey$", r"namaste", r"namaskar",
        r"vanakkam", r"నమస్కారం", r"నమస్తే",
    ]),
    ("help", [
        r"help", r"what can you", r"commands", r"options", r"menu",
        r"मदद", r"உதவி", r"సహాయం",
    ]),
]


def classify_intent(text: str) -> str:
    lower = text.lower().strip()
    for intent, patterns in _PATTERNS:
        for pat in patterns:
            if re.search(pat, lower):
                return intent
    return "unknown"
