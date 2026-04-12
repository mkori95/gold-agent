"""
Unit tests for the AnomalyDetector class.

What this tests:
1.  Valid gold price           -> is_valid True
2.  Valid silver price         -> is_valid True
3.  Valid platinum price       -> is_valid True
4.  Valid copper price         -> is_valid True
5.  Price below minimum        -> is_valid False, reason populated
6.  Price above maximum        -> is_valid False, reason populated
7.  Price is zero              -> is_valid False
8.  Price is negative          -> is_valid False
9.  Price is None              -> is_valid False
10. Price is wrong type        -> is_valid False
11. Unknown metal              -> is_valid True (let through with warning)
12. filter() -- mixed list     -> returns only valid records
13. filter() -- all invalid    -> returns empty list
14. filter() -- empty list     -> returns empty list
15. Result has required fields -> all fields present
"""
import pytest
from src.lambdas.consolidator.anomaly_detector import AnomalyDetector


def mock_record(metal, price_usd, source_id="test_source"):
    return {
        "metal":       metal,
        "price_usd":   price_usd,
        "source_id":   source_id,
        "source_name": "Test Source",
        "currency":    "USD",
        "price_inr":   None,
        "unit":        "troy_ounce",
        "timestamp":   "2026-03-01T10:00:00+00:00",
        "extra":       {}
    }


@pytest.fixture(scope="module")
def detector():
    return AnomalyDetector()


def test_init(detector):
    assert detector.metals_config, "Metals config failed to load — check config/metals.json"


def test_valid_gold_price(detector):
    result = detector.validate(mock_record("gold", 3100.00))
    assert result["is_valid"] is True
    assert result["reason"] is None


def test_valid_silver_price(detector):
    result = detector.validate(mock_record("silver", 32.50))
    assert result["is_valid"] is True


def test_valid_platinum_price(detector):
    result = detector.validate(mock_record("platinum", 980.00))
    assert result["is_valid"] is True


def test_valid_copper_price(detector):
    result = detector.validate(mock_record("copper", 4.50))
    assert result["is_valid"] is True


def test_price_below_minimum(detector):
    result = detector.validate(mock_record("gold", 100.00))
    assert result["is_valid"] is False, "Gold $100 should be rejected (below $500 minimum)"
    assert result["reason"] is not None


def test_price_above_maximum(detector):
    result = detector.validate(mock_record("gold", 50000.00))
    assert result["is_valid"] is False, "Gold $50000 should be rejected (above $15000 maximum)"
    assert result["reason"] is not None


def test_price_is_zero(detector):
    result = detector.validate(mock_record("gold", 0))
    assert result["is_valid"] is False
    assert result["reason"] is not None


def test_price_is_negative(detector):
    result = detector.validate(mock_record("gold", -100.00))
    assert result["is_valid"] is False


def test_price_is_none(detector):
    result = detector.validate(mock_record("gold", None))
    assert result["is_valid"] is False
    assert result["reason"] is not None


def test_price_wrong_type(detector):
    result = detector.validate(mock_record("gold", "3100.00"))
    assert result["is_valid"] is False


def test_unknown_metal_passes_through(detector):
    result = detector.validate(mock_record("unobtanium", 999.00))
    assert result["is_valid"] is True, "Unknown metals should be allowed through — never silently drop data"


def test_filter_mixed_list(detector):
    mixed_records = [
        mock_record("gold",     3100.00, "source_a"),   # valid
        mock_record("gold",     100.00,  "source_b"),   # invalid -- too low
        mock_record("silver",   32.50,   "source_c"),   # valid
        mock_record("gold",     50000.00,"source_d"),   # invalid -- too high
        mock_record("platinum", 980.00,  "source_e"),   # valid
    ]
    valid_records = detector.filter(mixed_records)
    assert len(valid_records) == 3
    valid_sources = [r["source_id"] for r in valid_records]
    assert "source_a" in valid_sources
    assert "source_c" in valid_sources
    assert "source_e" in valid_sources
    assert "source_b" not in valid_sources
    assert "source_d" not in valid_sources


def test_filter_all_invalid(detector):
    all_invalid = [
        mock_record("gold", 100.00),    # too low
        mock_record("gold", 50000.00),  # too high
        mock_record("gold", None),      # no price
    ]
    assert detector.filter(all_invalid) == []


def test_filter_empty_list(detector):
    assert detector.filter([]) == []


def test_result_required_fields(detector):
    result = detector.validate(mock_record("gold", 3100.00))
    for field in ["is_valid", "price_usd", "metal", "source_id", "reason"]:
        assert field in result, f"Field missing: {field}"
