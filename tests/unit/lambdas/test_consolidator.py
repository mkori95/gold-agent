"""
Unit tests for the Consolidator class.
Uses mock scraper results -- no live API calls.

What this tests:
1.  Consolidator initialises without errors
2.  All components initialised correctly
3.  Pipeline runs with mock scraper results
4.  Snapshot has correct structure
5.  Snapshot has all required top-level fields
6.  All 4 metals present in snapshot
7.  Gold has correct consensus fields
8.  INR prices calculated correctly
9.  City rates attached to gold
10. Extra fields (MCX, IBJA) attached to gold
11. Karat prices attached to gold
12. DynamoWriter called and returned result
13. S3Writer called and returned result
14. Failed scraper result handled gracefully
15. Pipeline result has all required fields
16. GoldAPI.io fixture data loads correctly
"""
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from src.lambdas.consolidator.consolidator import Consolidator


TEST_INR_RATE = 0.01099


def load_goldapi_fixture():
    with open("tests/fixtures/mock_goldapi_response.json", "r") as f:
        return json.load(f)


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


def mock_city_record(city, price_22k):
    return {
        "metal":       "gold",
        "price_usd":   None,
        "currency":    "INR",
        "price_inr":   price_22k,
        "unit":        "gram",
        "source_id":   "goodreturns",
        "source_name": "GoodReturns.in",
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "extra": {
            "city":          city,
            "karat_prices":  {"24K": 9780.0, "22K": price_22k, "18K": 7340.0},
            "primary_karat": "22K",
            "currency":      "INR"
        }
    }


def mock_scraper_result(source_id, records, status="success"):
    return {
        "source_id":        source_id,
        "source_name":      source_id,
        "status":           status,
        "data":             records if status == "success" else [],
        "error":            None if status == "success" else "Mock failure",
        "duration_seconds": 0.5,
        "scraped_at":       datetime.now(timezone.utc).isoformat(),
        "records_count":    len(records) if status == "success" else 0
    }


def build_goldapi_records():
    fixture = load_goldapi_fixture()
    records = []
    for metal in ["gold", "silver", "platinum"]:
        data = fixture[metal]
        karats = {
            "24K": data["price_gram_24k"],
            "22K": data["price_gram_22k"],
            "18K": data["price_gram_18k"]
        }
        records.append(mock_spot_record(
            metal=metal,
            price_usd=data["price"],
            source_id="goldapi_io",
            extra={"karats": karats, "ask": data["ask"], "bid": data["bid"]}
        ))
    return records


def build_mock_scraper_results():
    return [
        mock_scraper_result("gold_api_com", [
            mock_spot_record("gold",     3100.00, "gold_api_com"),
            mock_spot_record("silver",   32.50,   "gold_api_com"),
            mock_spot_record("platinum", 980.00,  "gold_api_com"),
            mock_spot_record("copper",   4.50,    "gold_api_com"),
        ]),
        mock_scraper_result("metals_dev", [
            mock_spot_record("gold",     3098.00, "metals_dev", extra={
                "mcx_gold": 3250.00, "ibja_gold": 3210.00,
                "lbma_gold_am": 3088.50, "lbma_gold_pm": 3092.75
            }),
            mock_spot_record("silver",   32.30,  "metals_dev"),
            mock_spot_record("platinum", 978.00, "metals_dev"),
            mock_spot_record("copper",   4.48,   "metals_dev"),
        ]),
        mock_scraper_result("goldapi_io", build_goldapi_records()),
        mock_scraper_result("goodreturns", [
            mock_city_record("mumbai",  8950.0),
            mock_city_record("delhi",   8930.0),
            mock_city_record("chennai", 8960.0),
        ]),
    ]


@pytest.fixture(scope="module")
def consolidator():
    return Consolidator()


@pytest.fixture(scope="module")
def pipeline_result(consolidator):
    with patch.object(consolidator, "_run_scrapers",
                      return_value=(build_mock_scraper_results(), TEST_INR_RATE)):
        return consolidator.run()


def test_consolidator_initialises(consolidator):
    assert consolidator is not None


def test_components_initialised(consolidator):
    assert consolidator.validator is not None
    assert consolidator.merger is not None
    assert consolidator.dynamo_writer is not None
    assert consolidator.s3_writer is not None
    assert consolidator.sources_config, "Sources config is empty"


def test_pipeline_status_success(pipeline_result):
    assert pipeline_result["status"] == "success", \
        f"Pipeline failed -- error: {pipeline_result.get('error')}"


def test_pipeline_duration(pipeline_result):
    assert pipeline_result["duration_seconds"] >= 0


def test_snapshot_present(pipeline_result):
    assert pipeline_result["snapshot"] is not None


def test_snapshot_required_fields(pipeline_result):
    snapshot = pipeline_result["snapshot"]
    for field in ["snapshot_id", "consolidated_at", "inr_rate", "usd_to_inr", "metals"]:
        assert field in snapshot, f"Snapshot field missing: {field}"


def test_all_four_metals_present(pipeline_result):
    metals = pipeline_result["snapshot"]["metals"]
    for metal in ["gold", "silver", "platinum", "copper"]:
        assert metal in metals, f"{metal} missing from snapshot"


def test_gold_consensus_fields(pipeline_result):
    gold = pipeline_result["snapshot"]["metals"]["gold"]
    for field in ["price_usd", "price_inr", "unit", "confidence", "sources_used",
                  "sources_count", "source_prices", "spread_percent", "spread_flagged",
                  "karats", "city_rates", "extra"]:
        assert field in gold, f"Gold field missing: {field}"
    assert gold["confidence"] == "high", f"Expected 'high', got '{gold['confidence']}'"
    assert gold["unit"] == "troy_ounce"


def test_inr_prices_calculated(pipeline_result):
    snapshot = pipeline_result["snapshot"]
    assert snapshot["inr_rate"] == TEST_INR_RATE
    assert snapshot["usd_to_inr"] == round(1 / TEST_INR_RATE, 4)
    gold = snapshot["metals"]["gold"]
    assert gold["price_inr"] is not None and gold["price_inr"] > 0


def test_city_rates_attached(pipeline_result):
    city_rates = pipeline_result["snapshot"]["metals"]["gold"]["city_rates"]
    assert city_rates, "city_rates missing or empty"
    for city in ["mumbai", "delhi", "chennai"]:
        assert city in city_rates, f"city_rates missing {city}"


def test_extra_fields_attached(pipeline_result):
    extra = pipeline_result["snapshot"]["metals"]["gold"]["extra"]
    for field in ["mcx_gold", "ibja_gold", "lbma_gold_am", "lbma_gold_pm"]:
        assert extra.get(field) is not None, f"extra.{field} missing"


def test_karat_prices_attached(pipeline_result):
    karats = pipeline_result["snapshot"]["metals"]["gold"]["karats"]
    assert karats, "karats missing or empty"
    for karat in ["24K", "22K", "18K"]:
        assert karat in karats, f"karat {karat} missing"


def test_dynamo_result_present(pipeline_result):
    dynamo_result = pipeline_result["dynamo_result"]
    assert dynamo_result is not None
    assert dynamo_result["status"] in ["stub", "success"]


def test_s3_result_present(pipeline_result):
    s3_result = pipeline_result["s3_result"]
    assert s3_result is not None
    assert s3_result["status"] in ["stub", "success"]


def test_failed_scraper_handled_gracefully(consolidator):
    mock_with_failure = [r for r in build_mock_scraper_results() if r["source_id"] != "goldapi_io"]
    mock_with_failure.append(mock_scraper_result("goldapi_io", [], status="failed"))
    with patch.object(consolidator, "_run_scrapers",
                      return_value=(mock_with_failure, TEST_INR_RATE)):
        result = consolidator.run()
    assert result["status"] == "success", "Pipeline should succeed with 3 valid sources"
    gold = result["snapshot"]["metals"]["gold"]
    assert gold["confidence"] == "medium", \
        f"Expected 'medium' confidence with goldapi_io failed, got '{gold['confidence']}'"


def test_pipeline_result_required_fields(consolidator):
    with patch.object(consolidator, "_run_scrapers",
                      return_value=(build_mock_scraper_results(), TEST_INR_RATE)):
        result = consolidator.run()
    for field in ["status", "error", "snapshot", "metals_count", "scraper_results",
                  "dynamo_result", "s3_result", "started_at", "completed_at", "duration_seconds"]:
        assert field in result, f"Result field missing: {field}"


def test_goldapi_fixture_loads():
    fixture = load_goldapi_fixture()
    for metal in ["gold", "silver", "platinum"]:
        assert metal in fixture, f"Fixture missing {metal}"
    records = build_goldapi_records()
    assert len(records) == 3
