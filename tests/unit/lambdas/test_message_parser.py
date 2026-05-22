from src.lambdas.whatsapp_handler.message_parser import parse_incoming


def _make_payload(text="hello", from_="919876543210", msg_type="text"):
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "id": "wamid.abc123",
                        "from": from_,
                        "type": msg_type,
                        "text": {"body": text},
                        "timestamp": "1716307200",
                    }],
                    "contacts": [{"profile": {"name": "Test User"}}],
                }
            }]
        }]
    }


def test_parses_text_message():
    result = parse_incoming(_make_payload("what is gold price"))
    assert result is not None
    assert result["text"] == "what is gold price"
    assert result["from"] == "919876543210"
    assert result["message_id"] == "wamid.abc123"
    assert result["name"] == "Test User"


def test_returns_none_for_non_text():
    result = parse_incoming(_make_payload(msg_type="image"))
    assert result is None


def test_returns_none_for_no_messages():
    payload = {
        "entry": [{"changes": [{"value": {"statuses": [{"status": "delivered"}]}}]}]
    }
    assert parse_incoming(payload) is None


def test_returns_none_for_empty_payload():
    assert parse_incoming({}) is None


def test_returns_none_for_malformed_payload():
    assert parse_incoming({"entry": "bad"}) is None
