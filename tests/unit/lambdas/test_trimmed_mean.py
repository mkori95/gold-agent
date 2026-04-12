"""
Unit tests for the TrimmedMean class.

What this tests:
1.  0 sources        -> confidence "unavailable", price None
2.  1 source         -> confidence "low", price = that source
3.  2 sources        -> confidence "medium", price = average
4.  3 sources        -> confidence "high", outlier effect removed
5.  4 sources        -> confidence "high", highest + lowest dropped
6.  5 sources        -> confidence "high", still trims only 1 from each end
7.  All same prices  -> spread = 0.0, still works
8.  Spread < 1%      -> no flag
9.  Spread > 2%      -> spread_flagged = True
10. Source prices    -> always preserved in result regardless of count
11. Result has all required fields
"""
import pytest
from src.lambdas.consolidator.trimmed_mean import TrimmedMean


@pytest.fixture(scope="module")
def tm():
    return TrimmedMean()


def test_zero_sources(tm):
    result = tm.calculate({})
    assert result["confidence"] == "unavailable"
    assert result["consensus_price"] is None
    assert result["sources_count"] == 0


def test_one_source(tm):
    result = tm.calculate({"gold_api_com": 3100.00})
    assert result["confidence"] == "low"
    assert result["consensus_price"] == 3100.00
    assert result["sources_count"] == 1


def test_two_sources_simple_average(tm):
    result = tm.calculate({"gold_api_com": 3100.00, "metals_dev": 3098.00})
    assert result["confidence"] == "medium"
    assert result["consensus_price"] == round((3100.00 + 3098.00) / 2, 4)
    assert result["sources_count"] == 2


def test_three_sources_trimmed_mean(tm):
    result = tm.calculate({
        "gold_api_com": 3100.00,
        "metals_dev":   3098.00,
        "goldapi_io":   3106.50
    })
    assert result["confidence"] == "high"
    # Drop highest (3106.50) and lowest (3098.00), remaining: [3100.00]
    assert result["consensus_price"] == 3100.00
    assert result["sources_count"] == 3


def test_four_sources_drops_outlier(tm):
    result = tm.calculate({
        "gold_api_com": 3100.00,
        "metals_dev":   3098.00,
        "goldapi_io":   3102.00,
        "source_four":  3500.00   # clear outlier -- dropped
    })
    assert result["confidence"] == "high"
    # Sorted: [3098, 3100, 3102, 3500] -- drop 3098 and 3500
    expected = round((3100.00 + 3102.00) / 2, 4)
    assert result["consensus_price"] == expected
    assert result["sources_count"] == 4
    assert "source_four" not in result["sources_used"]


def test_five_sources_trims_one_each_end(tm):
    result = tm.calculate({
        "source_a": 3090.00,   # lowest -- dropped
        "source_b": 3098.00,
        "source_c": 3100.00,
        "source_d": 3102.00,
        "source_e": 3200.00    # highest -- dropped
    })
    assert result["confidence"] == "high"
    expected = round((3098.00 + 3100.00 + 3102.00) / 3, 4)
    assert result["consensus_price"] == expected
    assert result["sources_count"] == 5


def test_all_same_prices_spread_zero(tm):
    result = tm.calculate({
        "gold_api_com": 3100.00,
        "metals_dev":   3100.00,
        "goldapi_io":   3100.00
    })
    assert result["spread_percent"] == 0.0
    assert result["consensus_price"] == 3100.00


def test_spread_under_one_percent_not_flagged(tm):
    result = tm.calculate({
        "gold_api_com": 3100.00,
        "metals_dev":   3098.00,
        "goldapi_io":   3102.00
    })
    assert result["spread_percent"] < 1.0
    assert result["spread_flagged"] is False


def test_spread_over_two_percent_flagged(tm):
    result = tm.calculate({
        "gold_api_com": 3100.00,
        "metals_dev":   3035.00,   # significantly lower -- creates >2% spread
        "goldapi_io":   3102.00
    })
    assert result["spread_flagged"] is True


def test_source_prices_preserved(tm):
    input_prices = {
        "gold_api_com": 3100.00,
        "metals_dev":   3098.00,
        "goldapi_io":   3106.50
    }
    result = tm.calculate(input_prices)
    assert result["source_prices"] == input_prices


def test_result_required_fields(tm):
    result = tm.calculate({"gold_api_com": 3100.00, "metals_dev": 3098.00})
    for field in ["consensus_price", "confidence", "sources_used",
                  "sources_count", "spread_percent", "spread_flagged", "source_prices"]:
        assert field in result, f"Field missing: {field}"
