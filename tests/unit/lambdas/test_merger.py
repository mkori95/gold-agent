"""
Unit tests for the Merger class.

What this tests:
1.  Basic merge -- 3 API sources         -> metals dict built correctly
2.  INR rate applied                     -> price_inr calculated correctly
3.  Consensus confidence                 -> high for 3 sources
4.  GoodReturns city rates               -> go to city_rates{} not trimmed mean
5.  Metals.Dev extra fields              -> attached to correct metal
6.  GoldAPI.io karat prices              -> attached to gold
7.  Karat fallback calculation           -> used when GoldAPI.io missing
8.  Anomaly detection integration        -> bad price rejected before trimmed mean
9.  No INR rate                          -> price_inr is None
10. Merge result has required metal fields
11. Merged result has required top-level fields
12. source_prices preserved
13. GoodReturns excluded from consensus
"""
import pytest
from datetime import datetime, timezone
from src.lambdas.consolidator.merger import Merger


TEST_INR_RATE = 0.01099


def mock_spot_record(metal, price_usd, source_id, extra=None):
    return {
        "metal":       metal,
        "price_usd":   price_usd,
        "currency":    "USD",
        "price_inr":   None,
        "unit":        "troy_ounce",
        "source_id":   source_id,
        "source_name": source_id,
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "extra":       extra or {}
    }


def mock_city_record(city, price_22k, source_id="goodreturns"):
    return {
        "metal":       "gold",
        "price_usd":   None,
        "currency":    "INR",
        "price_inr":   price_22k,
        "unit":        "gram",
        "source_id":   source_id,
        "source_name": "GoodReturns.in",
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "extra": {
            "city":          city,
            "karat_prices":  {"24K": 9780.0, "22K": price_22k, "18K": 7340.0},
            "primary_karat": "22K",
            "currency":      "INR"
        }
    }


def mock_scraper_result(source_id, records):
    return {
        "source_id":        source_id,
        "source_name":      source_id,
        "status":           "success",
        "data":             records,
        "error":            None,
        "duration_seconds": 0.5,
        "scraped_at":       datetime.now(timezone.utc).isoformat(),
        "records_count":    len(records)
    }


@pytest.fixture(scope="module")
def merger():
    return Merger()


@pytest.fixture(scope="module")
def base_results():
    return [
        mock_scraper_result("gold_api_com", [
            mock_spot_record("gold",     3100.00, "gold_api_com"),
            mock_spot_record("silver",   32.50,   "gold_api_com"),
            mock_spot_record("platinum", 980.00,  "gold_api_com"),
            mock_spot_record("copper",   4.50,    "gold_api_com"),
        ]),
        mock_scraper_result("metals_dev", [
            mock_spot_record("gold",     3098.00, "metals_dev",
                extra={"mcx_gold": 3250.00, "ibja_gold": 3210.00,
                       "lbma_gold_am": 3088.50, "lbma_gold_pm": 3092.75}),
            mock_spot_record("silver",   32.30,   "metals_dev"),
            mock_spot_record("platinum", 978.00,  "metals_dev"),
            mock_spot_record("copper",   4.48,    "metals_dev"),
        ]),
        mock_scraper_result("goldapi_io", [
            mock_spot_record("gold",     3102.00, "goldapi_io",
                extra={"karats": {"24K": 99.80, "22K": 91.48, "18K": 74.85}}),
            mock_spot_record("silver",   32.60,   "goldapi_io"),
            mock_spot_record("platinum", 982.00,  "goldapi_io"),
        ]),
    ]


@pytest.fixture(scope="module")
def merged(merger, base_results):
    return merger.merge(base_results, inr_rate=TEST_INR_RATE)


def test_all_metals_present(merged):
    assert "metals" in merged
    for metal in ["gold", "silver", "platinum", "copper"]:
        assert metal in merged["metals"], f"{metal} missing from merged result"


def test_inr_rate_applied_correctly(merged):
    gold = merged["metals"]["gold"]
    expected_inr = round(gold["price_usd"] / TEST_INR_RATE, 2)
    assert gold["price_inr"] == expected_inr
    assert merged["inr_rate"] == TEST_INR_RATE
    assert merged["usd_to_inr"] == round(1 / TEST_INR_RATE, 4)


def test_confidence_high_for_three_sources(merged):
    gold = merged["metals"]["gold"]
    assert gold["confidence"] == "high"
    assert gold["sources_count"] == 3


def test_city_rates_from_goodreturns(merger, base_results):
    results_with_cities = base_results + [
        mock_scraper_result("goodreturns", [
            mock_city_record("mumbai",  8950.0),
            mock_city_record("delhi",   8930.0),
            mock_city_record("chennai", 8960.0),
        ])
    ]
    merged_with_cities = merger.merge(results_with_cities, inr_rate=TEST_INR_RATE)
    city_rates = merged_with_cities["metals"]["gold"]["city_rates"]
    assert city_rates, "city_rates missing or empty"
    for city in ["mumbai", "delhi", "chennai"]:
        assert city in city_rates, f"city_rates missing {city}"


def test_metals_dev_extra_fields(merged):
    extra = merged["metals"]["gold"]["extra"]
    for field in ["mcx_gold", "ibja_gold", "lbma_gold_am", "lbma_gold_pm"]:
        assert extra.get(field) is not None, f"extra.{field} missing from gold"


def test_goldapi_io_karat_prices(merged):
    karats = merged["metals"]["gold"]["karats"]
    assert karats, "karats dict missing or empty"
    for karat in ["24K", "22K", "18K"]:
        assert karat in karats, f"karat {karat} missing"


def test_karat_fallback_without_goldapi(merger):
    results_no_goldapi = [
        mock_scraper_result("gold_api_com", [mock_spot_record("gold", 3100.00, "gold_api_com")]),
        mock_scraper_result("metals_dev",   [mock_spot_record("gold", 3098.00, "metals_dev")]),
    ]
    merged_no_goldapi = merger.merge(results_no_goldapi, inr_rate=TEST_INR_RATE)
    karats = merged_no_goldapi["metals"]["gold"]["karats"]
    assert karats, "Fallback karats missing"
    for karat in ["24K", "22K", "18K"]:
        assert karat in karats, f"Fallback {karat} missing"


def test_anomaly_detection_rejects_bad_price(merger):
    results_with_bad = [
        mock_scraper_result("gold_api_com", [mock_spot_record("gold", 3100.00, "gold_api_com")]),
        mock_scraper_result("metals_dev",   [mock_spot_record("gold", 3098.00, "metals_dev")]),
        mock_scraper_result("goldapi_io",   [mock_spot_record("gold", 99999.00, "goldapi_io")]),
    ]
    merged_bad = merger.merge(results_with_bad, inr_rate=TEST_INR_RATE)
    gold_bad = merged_bad["metals"]["gold"]
    assert gold_bad["confidence"] == "medium", \
        f"Expected 'medium' after bad price rejection, got '{gold_bad['confidence']}'"
    assert "goldapi_io" not in gold_bad["sources_used"]


def test_no_inr_rate_gives_none_price_inr(merger, base_results):
    merged_no_inr = merger.merge(base_results, inr_rate=None)
    assert merged_no_inr["metals"]["gold"]["price_inr"] is None
    assert merged_no_inr["inr_rate"] is None


def test_gold_metal_required_fields(merged):
    gold = merged["metals"]["gold"]
    for field in ["price_usd", "price_inr", "unit", "confidence", "sources_used",
                  "sources_count", "source_prices", "spread_percent", "spread_flagged",
                  "karats", "city_rates", "extra"]:
        assert field in gold, f"Field missing: {field}"


def test_merged_result_top_level_fields(merged):
    for field in ["inr_rate", "usd_to_inr", "metals"]:
        assert field in merged, f"Top-level field missing: {field}"


def test_source_prices_preserved(merged):
    source_prices = merged["metals"]["gold"]["source_prices"]
    for source in ["gold_api_com", "metals_dev", "goldapi_io"]:
        assert source in source_prices, f"source_prices missing {source}"


def test_goodreturns_excluded_from_consensus(merger, base_results):
    results_with_cities = base_results + [
        mock_scraper_result("goodreturns", [
            mock_city_record("mumbai", 8950.0),
            mock_city_record("delhi",  8930.0),
        ])
    ]
    merged_with_cities = merger.merge(results_with_cities, inr_rate=TEST_INR_RATE)
    source_prices = merged_with_cities["metals"]["gold"]["source_prices"]
    assert "goodreturns" not in source_prices, \
        "goodreturns should not appear in source_prices (city rates only)"
