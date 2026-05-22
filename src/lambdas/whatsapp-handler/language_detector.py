def detect_language(text: str) -> str:
    """
    Detect language from Unicode script ranges.
    Returns: 'hi' | 'ta' | 'te' | 'en'
    Falls back to 'en' for mixed or unrecognised scripts.
    """
    scores = {"hi": 0, "ta": 0, "te": 0}
    for ch in text:
        cp = ord(ch)
        if 0x0900 <= cp <= 0x097F:   # Devanagari (Hindi)
            scores["hi"] += 1
        elif 0x0B80 <= cp <= 0x0BFF: # Tamil
            scores["ta"] += 1
        elif 0x0C00 <= cp <= 0x0C7F: # Telugu
            scores["te"] += 1

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "en"
