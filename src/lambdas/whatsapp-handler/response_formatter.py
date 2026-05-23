HELP_MESSAGES = {
    "en": (
        "Hi! I'm Gold Agent 🪙\n\n"
        "I can help you with:\n"
        "• *Gold/Silver price today* — just ask!\n"
        "• *Price alerts* — \"Alert me when gold drops below ₹14,000/g\"\n"
        "• *Calculator* — \"How much gold for ₹50,000?\"\n"
        "• *Festival advice* — Is now a good time to buy?\n\n"
        "What would you like to know?"
    ),
    "hi": (
        "नमस्ते! मैं Gold Agent हूँ 🪙\n\n"
        "मैं इनमें मदद कर सकता हूँ:\n"
        "• *आज का सोना/चाँदी भाव* — बस पूछें!\n"
        "• *अलर्ट* — \"जब सोना ₹14,000/g से नीचे जाए तो बताना\"\n"
        "• *कैलकुलेटर* — \"₹50,000 में कितना सोना मिलेगा?\"\n"
        "• *त्योहार सलाह* — क्या अभी खरीदना सही है?\n\n"
        "क्या जानना है?"
    ),
    "ta": (
        "வணக்கம்! நான் Gold Agent 🪙\n\n"
        "நான் உதவக்கூடியவை:\n"
        "• *இன்றைய தங்கம்/வெள்ளி விலை* — கேளுங்கள்!\n"
        "• *விலை எச்சரிக்கை* — \"தங்கம் ₹14,000/g கீழே போனால் சொல்லு\"\n"
        "• *கணக்கீடு* — \"₹50,000-க்கு எவ்வளவு தங்கம்?\"\n"
        "• *பண்டிகை ஆலோசனை* — இப்போது வாங்குவது சரியா?\n\n"
        "என்ன தெரிந்துகொள்ள வேண்டும்?"
    ),
    "te": (
        "నమస్కారం! నేను Gold Agent 🪙\n\n"
        "నేను సహాయపడగలిగేవి:\n"
        "• *ఈరోజు బంగారం/వెండి రేటు* — అడగండి!\n"
        "• *ధర హెచ్చరిక* — \"బంగారం ₹14,000/g కంటే తక్కువైతే చెప్పు\"\n"
        "• *లెక్కింపు* — \"₹50,000కి ఎంత బంగారం?\"\n"
        "• *పండుగ సలహా* — ఇప్పుడు కొనడం మంచిదా?\n\n"
        "ఏమి తెలుసుకోవాలి?"
    ),
}

UNKNOWN_MESSAGES = {
    "en": "I didn't quite understand that. Try asking about gold or silver prices, or type *help* to see what I can do.",
    "hi": "मैं समझ नहीं पाया। सोने या चाँदी के भाव के बारे में पूछें, या *help* टाइप करें।",
    "ta": "புரியவில்லை. தங்கம் அல்லது வெள்ளி விலை பற்றி கேளுங்கள், அல்லது *help* என்று தட்டச்சு செய்யுங்கள்.",
    "te": "అర్థం కాలేదు. బంగారం లేదా వెండి ధర గురించి అడగండి, లేదా *help* అని టైప్ చేయండి.",
}


SUMMARY_SUBSCRIBE_MESSAGES = {
    "en": "Done! You'll get a daily gold price update every morning around 11:45 AM IST.\n\nReply *stop summary* anytime to unsubscribe.",
    "hi": "हो गया! आपको हर सुबह लगभग 11:45 बजे सोने का भाव मिलेगा।\n\n*stop summary* लिखकर कभी भी बंद कर सकते हैं।",
    "ta": "சரி! தினமும் காலை 11:45 மணி அளவில் தங்கம் விலை அனுப்பப்படும்.\n\n*stop summary* என்று தட்டச்சு செய்து நிறுத்தலாம்.",
    "te": "సరే! ప్రతిరోజూ ఉదయం 11:45 గంటలకు బంగారం ధర పంపబడుతుంది.\n\n*stop summary* అని టైప్ చేసి ఎప్పుడైనా ఆపవచ్చు.",
}

SUMMARY_UNSUBSCRIBE_MESSAGES = {
    "en": "Done! You won't receive the daily summary anymore. Reply *daily update* anytime to subscribe again.",
    "hi": "ठीक है! अब आपको रोज़ का अपडेट नहीं आएगा। दोबारा शुरू करने के लिए *daily update* लिखें।",
    "ta": "சரி! இனி தினசரி சுருக்கம் வராது. மீண்டும் பெற *daily update* என்று தட்டச்சு செய்யுங்கள்.",
    "te": "సరే! ఇకపై రోజువారీ సారాంశం రాదు. మళ్ళీ పొందడానికి *daily update* అని టైప్ చేయండి.",
}


def help_message(language: str) -> str:
    return HELP_MESSAGES.get(language, HELP_MESSAGES["en"])


def unknown_message(language: str) -> str:
    return UNKNOWN_MESSAGES.get(language, UNKNOWN_MESSAGES["en"])


def summary_subscribe_message(language: str) -> str:
    return SUMMARY_SUBSCRIBE_MESSAGES.get(language, SUMMARY_SUBSCRIBE_MESSAGES["en"])


def summary_unsubscribe_message(language: str) -> str:
    return SUMMARY_UNSUBSCRIBE_MESSAGES.get(language, SUMMARY_UNSUBSCRIBE_MESSAGES["en"])
