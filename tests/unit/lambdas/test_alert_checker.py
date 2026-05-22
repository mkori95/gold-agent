from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta

from src.lambdas.alert_checker.threshold_checker import get_current_price_per_gram, is_triggered
from src.lambdas.alert_checker.cooldown_manager import is_in_cooldown
from src.lambdas.alert_checker.alert_formatter import format_alert
from src.shared.models.alert import AlertPreference
from src.shared.models.price import PriceSnapshot, MetalPrice


def _make_snapshot(gold_22k=6500.0, silver_per_oz=None):
    metals = {
        "gold": MetalPrice(
            metal="gold",
            price_usd=2300.0,
            price_inr=190000.0,
            inr_rate=84.0,
            confidence="high",
            source_count=3,
            price_22k_inr=gold_22k,
            price_24k_inr=7100.0,
        ),
    }
    if silver_per_oz is not None:
        metals["silver"] = MetalPrice(
            metal="silver",
            price_usd=28.0,
            price_inr=silver_per_oz,
            inr_rate=84.0,
            confidence="high",
            source_count=3,
        )
    return PriceSnapshot(snapshot_date="2026-05-21", timestamp="2026-05-21T06:00:00Z", metals=metals)


def _make_alert(metal="gold", direction="below", threshold=7000.0, karat="22K", last_triggered=None):
    return AlertPreference(
        phone_number="+919876543210",
        metal=metal,
        direction=direction,
        threshold_inr=threshold,
        karat=karat,
        last_triggered=last_triggered,
    )


# --- threshold_checker ---

def test_gold_22k_price_returned():
    snap = _make_snapshot(gold_22k=6500.0)
    price = get_current_price_per_gram(snap, "gold", "22K")
    assert price == 6500.0


def test_gold_24k_price_returned():
    snap = _make_snapshot()
    price = get_current_price_per_gram(snap, "gold", "24K")
    assert price == 7100.0


def test_silver_per_gram_conversion():
    snap = _make_snapshot(silver_per_oz=2604.35)  # ~84 INR/g * 31.1035
    price = get_current_price_per_gram(snap, "silver", "999")
    assert price is not None
    assert 80 < price < 90


def test_unknown_metal_returns_none():
    snap = _make_snapshot()
    assert get_current_price_per_gram(snap, "platinum", "999") is None


def test_is_triggered_below():
    alert = _make_alert(direction="below", threshold=7000.0)
    assert is_triggered(alert, 6500.0) is True


def test_not_triggered_below():
    alert = _make_alert(direction="below", threshold=7000.0)
    assert is_triggered(alert, 7500.0) is False


def test_is_triggered_above():
    alert = _make_alert(direction="above", threshold=7000.0)
    assert is_triggered(alert, 7500.0) is True


def test_not_triggered_above():
    alert = _make_alert(direction="above", threshold=7000.0)
    assert is_triggered(alert, 6500.0) is False


# --- cooldown_manager ---

def test_no_cooldown_when_never_triggered():
    alert = _make_alert(last_triggered=None)
    assert is_in_cooldown(alert) is False


def test_in_cooldown_within_12h():
    recent = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    alert = _make_alert(last_triggered=recent)
    assert is_in_cooldown(alert) is True


def test_not_in_cooldown_after_12h():
    old = (datetime.now(timezone.utc) - timedelta(hours=13)).isoformat()
    alert = _make_alert(last_triggered=old)
    assert is_in_cooldown(alert) is False


# --- alert_formatter ---

def test_format_alert_below_english():
    alert = _make_alert(direction="below", threshold=7000.0)
    msg = format_alert(alert, 6500.0, "en")
    assert "6,500" in msg
    assert "7,000" in msg
    assert "🟢" in msg


def test_format_alert_above_hindi():
    alert = _make_alert(direction="above", threshold=7000.0)
    msg = format_alert(alert, 7500.0, "hi")
    assert "7,500" in msg
    assert "🔴" in msg


def test_format_alert_tamil():
    alert = _make_alert(direction="below", threshold=6000.0)
    msg = format_alert(alert, 5800.0, "ta")
    assert "5,800" in msg


def test_format_alert_unknown_language_falls_back_to_english():
    alert = _make_alert(direction="below", threshold=6000.0)
    msg = format_alert(alert, 5800.0, "xx")
    assert "5,800" in msg
    assert "🟢" in msg
