from src.lambdas.whatsapp_handler.intent_classifier import classify_intent


def test_price_query_english():
    assert classify_intent("what is gold price today") == "price_query"


def test_price_query_hindi():
    assert classify_intent("सोने का भाव क्या है") == "price_query"


def test_alert_setup():
    assert classify_intent("alert me when gold drops below 6000") == "alert_setup"


def test_calculator():
    assert classify_intent("how much gold can I buy for 50000 rupees") == "calculator"


def test_festival_advice():
    assert classify_intent("should I buy gold on diwali") == "festival_advice"


def test_trend_query():
    assert classify_intent("is gold price rising or falling") == "trend_query"


def test_greeting_hi():
    assert classify_intent("hi") == "greeting"


def test_greeting_namaste():
    assert classify_intent("namaste") == "greeting"


def test_help():
    assert classify_intent("help") == "help"


def test_unknown():
    assert classify_intent("random gibberish xyz") == "unknown"


def test_silver_price_query():
    assert classify_intent("silver rate today") == "price_query"


def test_alert_hindi():
    assert classify_intent("अलर्ट लगाओ जब सोना गिरे") == "alert_setup"
