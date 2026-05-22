from src.lambdas.whatsapp_handler.language_detector import detect_language


def test_hindi_devanagari():
    assert detect_language("सोने का भाव क्या है") == "hi"


def test_tamil_script():
    assert detect_language("தங்கம் விலை என்ன") == "ta"


def test_telugu_script():
    assert detect_language("బంగారం ధర ఎంత") == "te"


def test_english_fallback():
    assert detect_language("what is gold price today") == "en"


def test_empty_string():
    assert detect_language("") == "en"


def test_numbers_only():
    assert detect_language("12345") == "en"


def test_mixed_english_hindi_returns_hindi():
    # More Hindi characters than English
    assert detect_language("सोना gold") == "hi"
