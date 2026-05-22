"""
Tests for alert_setup.handle() — the full flow: extract → write → confirm.
Claude extraction is mocked so tests are fast and offline.
DynamoDB write is mocked so no AWS calls are made.
"""

from unittest.mock import patch, MagicMock
import pytest

from src.lambdas.conversation.alert_setup import handle, _extract_params


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_extract(metal, direction, threshold, karat=None):
    return {
        "metal": metal,
        "direction": direction,
        "threshold_inr": threshold,
        "karat": karat,
    }


# ── _extract_params (unit) ────────────────────────────────────────────────────

def test_extract_returns_none_when_claude_returns_bad_json():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not json at all")]
    with patch("src.lambdas.conversation.alert_setup._get_client") as mock_client:
        mock_client.return_value.messages.create.return_value = mock_response
        assert _extract_params("random text") is None


def test_extract_returns_none_when_fields_missing():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"metal": "gold", "direction": null, "threshold_inr": null}')]
    with patch("src.lambdas.conversation.alert_setup._get_client") as mock_client:
        mock_client.return_value.messages.create.return_value = mock_response
        assert _extract_params("gold something") is None


def test_extract_strips_markdown_fences():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='```json\n{"metal": "gold", "direction": "below", "threshold_inr": 6500, "karat": "22K"}\n```'
    )]
    with patch("src.lambdas.conversation.alert_setup._get_client") as mock_client:
        mock_client.return_value.messages.create.return_value = mock_response
        result = _extract_params("alert me when gold drops below 6500")
    assert result["metal"] == "gold"
    assert result["threshold_inr"] == 6500


# ── handle() — full flow ──────────────────────────────────────────────────────

@patch("src.lambdas.conversation.alert_setup.put_alert")
@patch("src.lambdas.conversation.alert_setup._extract_params")
def test_handle_english_creates_alert_and_confirms(mock_extract, mock_put):
    mock_extract.return_value = _mock_extract("gold", "below", 6500, "22K")
    reply = handle("+919876543210", "alert me when gold drops below 6500", "en")
    mock_put.assert_called_once()
    assert "✅" in reply
    assert "6,500" in reply
    assert "Gold" in reply


@patch("src.lambdas.conversation.alert_setup.put_alert")
@patch("src.lambdas.conversation.alert_setup._extract_params")
def test_handle_hindi_creates_alert_and_confirms(mock_extract, mock_put):
    mock_extract.return_value = _mock_extract("gold", "below", 6500, "22K")
    reply = handle("+919876543210", "सोना ₹6500 से नीचे जाए तो बताना", "hi")
    mock_put.assert_called_once()
    assert "✅" in reply
    assert "6,500" in reply
    assert "सोना" in reply
    assert "नीचे" in reply


@patch("src.lambdas.conversation.alert_setup.put_alert")
@patch("src.lambdas.conversation.alert_setup._extract_params")
def test_handle_tamil_creates_alert_and_confirms(mock_extract, mock_put):
    mock_extract.return_value = _mock_extract("gold", "below", 6500, "22K")
    reply = handle("+919876543210", "தங்கம் ₹6500 கீழே போனால் சொல்லு", "ta")
    mock_put.assert_called_once()
    assert "✅" in reply
    assert "தங்கம்" in reply
    assert "கீழே" in reply


@patch("src.lambdas.conversation.alert_setup.put_alert")
@patch("src.lambdas.conversation.alert_setup._extract_params")
def test_handle_telugu_creates_alert_and_confirms(mock_extract, mock_put):
    mock_extract.return_value = _mock_extract("gold", "below", 6500, "22K")
    reply = handle("+919876543210", "బంగారం ₹6500 కంటే తక్కువైతే చెప్పు", "te")
    mock_put.assert_called_once()
    assert "✅" in reply
    assert "బంగారం" in reply
    assert "కింద" in reply


@patch("src.lambdas.conversation.alert_setup.put_alert")
@patch("src.lambdas.conversation.alert_setup._extract_params")
def test_handle_above_direction(mock_extract, mock_put):
    mock_extract.return_value = _mock_extract("silver", "above", 80, "999")
    reply = handle("+919876543210", "alert me when silver goes above 80", "en")
    mock_put.assert_called_once()
    assert "above" in reply
    assert "80" in reply


@patch("src.lambdas.conversation.alert_setup.put_alert")
@patch("src.lambdas.conversation.alert_setup._extract_params")
def test_handle_no_alert_written_when_extraction_fails(mock_extract, mock_put):
    mock_extract.return_value = None
    reply = handle("+919876543210", "tell me something about gold", "en")
    mock_put.assert_not_called()
    assert "✅" not in reply


@patch("src.lambdas.conversation.alert_setup.put_alert")
@patch("src.lambdas.conversation.alert_setup._extract_params")
def test_clarification_in_hindi_when_extraction_fails(mock_extract, mock_put):
    mock_extract.return_value = None
    reply = handle("+919876543210", "सोने के बारे में कुछ बताओ", "hi")
    mock_put.assert_not_called()
    assert "₹" in reply  # clarification message has example prices


@patch("src.lambdas.conversation.alert_setup.put_alert")
@patch("src.lambdas.conversation.alert_setup._extract_params")
def test_default_karat_22k_for_gold(mock_extract, mock_put):
    mock_extract.return_value = _mock_extract("gold", "below", 6500, karat=None)
    handle("+919876543210", "alert when gold drops below 6500", "en")
    call_args = mock_put.call_args[0][0]
    assert call_args.karat == "22K"


@patch("src.lambdas.conversation.alert_setup.put_alert")
@patch("src.lambdas.conversation.alert_setup._extract_params")
def test_default_karat_999_for_silver(mock_extract, mock_put):
    mock_extract.return_value = _mock_extract("silver", "below", 80, karat=None)
    handle("+919876543210", "alert when silver drops below 80", "en")
    call_args = mock_put.call_args[0][0]
    assert call_args.karat == "999"
