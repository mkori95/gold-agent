LANGUAGE_REMINDER = {
    "hi": "\n\n(कृपया हिंदी में उत्तर दें)",
    "ta": "\n\n(தயவுசெய்து தமிழில் பதில் சொல்லுங்கள்)",
    "te": "\n\n(దయచేసి తెలుగులో సమాధానం ఇవ్వండి)",
    "en": "",
}


def append_language_reminder(user_message: str, language: str) -> str:
    """
    Appends a language reminder to the user message so Claude always
    responds in the correct language even if the message is in English.
    """
    reminder = LANGUAGE_REMINDER.get(language, "")
    return user_message + reminder if reminder else user_message
