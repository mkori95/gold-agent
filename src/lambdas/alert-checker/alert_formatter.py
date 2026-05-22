from src.shared.models.alert import AlertPreference

TEMPLATES = {
    "below": {
        "en": "Gold Alert 🟢\n{metal_name} has dropped to ₹{price:,.0f}/gram ({karat}).\nYour target was ₹{threshold:,.0f}/gram. Now may be a good time to buy!",
        "hi": "Gold Alert 🟢\n{metal_name} ₹{price:,.0f}/gram ({karat}) पर आ गया है।\nआपका लक्ष्य ₹{threshold:,.0f}/gram था। अभी खरीदना अच्छा हो सकता है!",
        "ta": "Gold Alert 🟢\n{metal_name} ₹{price:,.0f}/gram ({karat})-க்கு இறங்கியது.\nஉங்கள் இலக்கு ₹{threshold:,.0f}/gram. இப்போது வாங்குவது நல்லது!",
        "te": "Gold Alert 🟢\n{metal_name} ₹{price:,.0f}/gram ({karat})కి తగ్గింది.\nమీ లక్ష్యం ₹{threshold:,.0f}/gram. ఇప్పుడు కొనడం మంచిది!",
    },
    "above": {
        "en": "Gold Alert 🔴\n{metal_name} has risen to ₹{price:,.0f}/gram ({karat}).\nYour target was ₹{threshold:,.0f}/gram.",
        "hi": "Gold Alert 🔴\n{metal_name} ₹{price:,.0f}/gram ({karat}) पर पहुंच गया है।\nआपका लक्ष्य ₹{threshold:,.0f}/gram था।",
        "ta": "Gold Alert 🔴\n{metal_name} ₹{price:,.0f}/gram ({karat})-க்கு ஏறியது.\nஉங்கள் இலக்கு ₹{threshold:,.0f}/gram.",
        "te": "Gold Alert 🔴\n{metal_name} ₹{price:,.0f}/gram ({karat})కి పెరిగింది.\nమీ లక్ష్యం ₹{threshold:,.0f}/gram.",
    },
}

METAL_NAMES = {
    "gold":     {"en": "Gold",     "hi": "सोना",    "ta": "தங்கம்",  "te": "బంగారం"},
    "silver":   {"en": "Silver",   "hi": "चांदी",   "ta": "வெள்ளி",  "te": "వెండి"},
    "platinum": {"en": "Platinum", "hi": "प्लेटिनम", "ta": "பிளாட்டினம்", "te": "ప్లాటినం"},
}


def format_alert(alert: AlertPreference, current_price: float, language: str = "en") -> str:
    direction = alert.direction
    lang = language if language in ("en", "hi", "ta", "te") else "en"
    metal_name = METAL_NAMES.get(alert.metal, {}).get(lang, alert.metal.capitalize())
    template = TEMPLATES[direction][lang]
    return template.format(
        metal_name=metal_name,
        price=current_price,
        karat=alert.karat,
        threshold=alert.threshold_inr,
    )
