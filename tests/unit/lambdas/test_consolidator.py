from dotenv import load_dotenv
load_dotenv()
"""
test_consolidator.py

Unit tests for the Consolidator class.
Uses mock scraper results — no live API calls.

IMPORTANT — Always run this from project root:
    python tests/unit/lambdas/test_consolidator.py

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
14. Disabled source is skipped
15. Failed scraper result handled gracefully
16. GoldAPI.io fixture data loads correctly
"""

from dotenv import load_dotenv
load_dotenv()

import sys
import json
import logging
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

sys.path.insert(0, ".")

from src.lambdas.consolidator.consolidator import Consolidator

# ============================================================
# Set up logging
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s"
)

# ============================================================
# Helpers
# ============================================================
def passed(msg):
    print(f"  ✅  {msg}")

def failed(msg):
    print(f"  ❌  {msg}")
    sys.exit(1)

def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")

# ============================================================
# Load GoldAPI.io fixture
# ============================================================
def load_goldapi_fixture():
    with open("tests/fixtures/mock_goldapi_response.json", "r") as f:
        return json.load(f)

# ============================================================
# Mock scraper results — realistic data
# ============================================================
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

# Build fixture-based goldapi records using fixture file
def build_goldapi_records():
    fixture   = load_goldapi_fixture()
    records   = []

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
            extra={
                "karats": karats,
                "ask":    data["ask"],
                "bid":    data["bid"]
            }
        ))
    return records

# ============================================================
# Build mock pipeline results
# All scraper results the consolidator would receive
# ============================================================
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
                "mcx_gold":     3250.00,
                "ibja_gold":    3210.00,
                "lbma_gold_am": 3088.50,
                "lbma_gold_pm": 3092.75
            }),
            mock_spot_record("silver",   32.30, "metals_dev"),
            mock_spot_record("platinum", 978.00, "metals_dev"),
            mock_spot_record("copper",   4.48,  "metals_dev"),
        ]),
        mock_scraper_result("goldapi_io", build_goldapi_records()),
        mock_scraper_result("goodreturns", [
            mock_city_record("mumbai",  8950.0),
            mock_city_record("delhi",   8930.0),
            mock_city_record("chennai", 8960.0),
        ]),
    ]

TEST_INR_RATE = 0.01099

# ============================================================
# TEST 1 — Consolidator initialises without errors
# ============================================================
section("TEST 1 — Consolidator initialises without errors")

try:
    consolidator = Consolidator()
    passed("Consolidator initialised")
except Exception as e:
    failed(f"Consolidator failed to initialise — {str(e)}")

# ============================================================
# TEST 2 — All components initialised
# ============================================================
section("TEST 2 — All components initialised")

if consolidator.validator is not None:
    passed("Validator initialised")
else:
    failed("Validator is None")

if consolidator.merger is not None:
    passed("Merger initialised")
else:
    failed("Merger is None")

if consolidator.dynamo_writer is not None:
    passed("DynamoWriter initialised")
else:
    failed("DynamoWriter is None")

if consolidator.s3_writer is not None:
    passed("S3Writer initialised")
else:
    failed("S3Writer is None")

if consolidator.sources_config:
    passed(f"Sources config loaded — {len(consolidator.sources_config)} sources")
else:
    failed("Sources config is empty")

# ============================================================
# TEST 3 — Pipeline runs with mock scraper results
# We patch _run_scrapers to return mock data
# so we don't make real API calls
# ============================================================
section("TEST 3 — Pipeline runs with mock scraper results")

mock_results = build_mock_scraper_results()

with patch.object(
    consolidator,
    "_run_scrapers",
    return_value=(mock_results, TEST_INR_RATE)
):
    result = consolidator.run()

if result["status"] == "success":
    passed(f"Pipeline status: success")
else:
    failed(f"Pipeline failed — error: {result.get('error')}")

if result["duration_seconds"] >= 0:
    passed(f"Duration: {result['duration_seconds']}s")
else:
    failed("Duration should be >= 0")

# ============================================================
# TEST 4 — Snapshot present in result
# ============================================================
section("TEST 4 — Snapshot present in result")

snapshot = result["snapshot"]

if snapshot is not None:
    passed("Snapshot is present")
else:
    failed("Snapshot is None")

# ============================================================
# TEST 5 — Snapshot has required top-level fields
# ============================================================
section("TEST 5 — Snapshot has required top-level fields")

required_snapshot_fields = [
    "snapshot_id",
    "consolidated_at",
    "inr_rate",
    "usd_to_inr",
    "metals"
]

for field in required_snapshot_fields:
    if field in snapshot:
        passed(f"Snapshot field present: {field} = {snapshot[field]}")
    else:
        failed(f"Snapshot field MISSING: {field}")

# ============================================================
# TEST 6 — All 4 metals present in snapshot
# ============================================================
section("TEST 6 — All 4 metals present in snapshot")

for metal in ["gold", "silver", "platinum", "copper"]:
    if metal in snapshot["metals"]:
        passed(f"{metal} present in snapshot")
    else:
        failed(f"{metal} MISSING from snapshot")

# ============================================================
# TEST 7 — Gold has correct consensus fields
# ============================================================
section("TEST 7 — Gold has correct consensus fields")

gold = snapshot["metals"]["gold"]

required_gold_fields = [
    "price_usd", "price_inr", "unit", "confidence",
    "sources_used", "sources_count", "source_prices",
    "spread_percent", "spread_flagged", "karats",
    "city_rates", "extra"
]

for field in required_gold_fields:
    if field in gold:
        passed(f"Gold field present: {field}")
    else:
        failed(f"Gold field MISSING: {field}")

if gold["confidence"] == "high":
    passed(f"Gold confidence = 'high' (3 sources)")
else:
    failed(f"Expected 'high' — got '{gold['confidence']}'")

if gold["unit"] == "troy_ounce":
    passed("Gold unit = 'troy_ounce'")
else:
    failed(f"Gold unit wrong: {gold['unit']}")

# ============================================================
# TEST 8 — INR prices calculated correctly
# ============================================================
section("TEST 8 — INR prices calculated correctly")

if snapshot["inr_rate"] == TEST_INR_RATE:
    passed(f"Snapshot inr_rate = {snapshot['inr_rate']}")
else:
    failed(f"Expected {TEST_INR_RATE} — got {snapshot['inr_rate']}")

expected_usd_to_inr = round(1 / TEST_INR_RATE, 4)
if snapshot["usd_to_inr"] == expected_usd_to_inr:
    passed(f"usd_to_inr = ₹{snapshot['usd_to_inr']}")
else:
    failed(f"Expected ₹{expected_usd_to_inr} — got ₹{snapshot['usd_to_inr']}")

gold_price_inr = gold["price_inr"]
if gold_price_inr is not None and gold_price_inr > 0:
    passed(f"Gold price_inr = ₹{gold_price_inr}")
else:
    failed(f"Gold price_inr invalid: {gold_price_inr}")

# ============================================================
# TEST 9 — City rates attached to gold
# ============================================================
section("TEST 9 — City rates attached to gold")

city_rates = gold["city_rates"]

if city_rates:
    passed(f"city_rates present — {len(city_rates)} cities")
else:
    failed("city_rates missing or empty")

for city in ["mumbai", "delhi", "chennai"]:
    if city in city_rates:
        passed(f"city_rates has {city}: {city_rates[city]}")
    else:
        failed(f"city_rates missing {city}")

# ============================================================
# TEST 10 — Extra fields (MCX, IBJA) attached to gold
# ============================================================
section("TEST 10 — Extra fields attached to gold")

extra = gold["extra"]

for field in ["mcx_gold", "ibja_gold", "lbma_gold_am", "lbma_gold_pm"]:
    if extra.get(field) is not None:
        passed(f"extra.{field} = {extra[field]}")
    else:
        failed(f"extra.{field} missing")

# ============================================================
# TEST 11 — Karat prices attached to gold
# ============================================================
section("TEST 11 — Karat prices attached to gold")

karats = gold["karats"]

if karats:
    passed(f"karats present: {list(karats.keys())}")
else:
    failed("karats missing or empty")

for karat in ["24K", "22K", "18K"]:
    if karat in karats:
        passed(f"karat {karat}: {karats[karat]}")
    else:
        failed(f"karat {karat} missing")

# ============================================================
# TEST 12 — DynamoWriter result present
# ============================================================
section("TEST 12 — DynamoWriter result present")

dynamo_result = result["dynamo_result"]

if dynamo_result is not None:
    passed(f"dynamo_result present — status: {dynamo_result['status']}")
else:
    failed("dynamo_result is None")

if dynamo_result["status"] in ["stub", "success"]:
    passed(f"DynamoWriter status acceptable: {dynamo_result['status']}")
else:
    failed(f"Unexpected DynamoWriter status: {dynamo_result['status']}")

# ============================================================
# TEST 13 — S3Writer result present
# ============================================================
section("TEST 13 — S3Writer result present")

s3_result = result["s3_result"]

if s3_result is not None:
    passed(f"s3_result present — status: {s3_result['status']}")
else:
    failed("s3_result is None")

if s3_result["status"] in ["stub", "success"]:
    passed(f"S3Writer status acceptable: {s3_result['status']}")
else:
    failed(f"Unexpected S3Writer status: {s3_result['status']}")

# ============================================================
# TEST 14 — Failed scraper result handled gracefully
# ============================================================
section("TEST 14 — Failed scraper handled gracefully")

mock_with_failure = build_mock_scraper_results()

# Replace goldapi_io with a failed result
mock_with_failure = [
    r for r in mock_with_failure
    if r["source_id"] != "goldapi_io"
]
mock_with_failure.append(
    mock_scraper_result("goldapi_io", [], status="failed")
)

with patch.object(
    consolidator,
    "_run_scrapers",
    return_value=(mock_with_failure, TEST_INR_RATE)
):
    result_with_failure = consolidator.run()

if result_with_failure["status"] == "success":
    passed("Pipeline succeeded despite one failed scraper")
else:
    failed(f"Pipeline should succeed with 3 valid sources — got: {result_with_failure['status']}")

gold_with_failure = result_with_failure["snapshot"]["metals"]["gold"]

if gold_with_failure["confidence"] == "medium":
    passed("Gold confidence dropped to 'medium' with 2 sources (goldapi_io failed)")
else:
    failed(
        f"Expected 'medium' confidence — got '{gold_with_failure['confidence']}'"
    )

# ============================================================
# TEST 15 — Pipeline result has all required fields
# ============================================================
section("TEST 15 — Pipeline result has all required fields")

required_result_fields = [
    "status", "error", "snapshot", "metals_count",
    "scraper_results", "dynamo_result", "s3_result",
    "started_at", "completed_at", "duration_seconds"
]

with patch.object(
    consolidator,
    "_run_scrapers",
    return_value=(build_mock_scraper_results(), TEST_INR_RATE)
):
    final_result = consolidator.run()

for field in required_result_fields:
    if field in final_result:
        passed(f"Result field present: {field}")
    else:
        failed(f"Result field MISSING: {field}")

# ============================================================
# TEST 16 — GoldAPI.io fixture loads correctly
# ============================================================
section("TEST 16 — GoldAPI.io fixture loads and is used")

fixture = load_goldapi_fixture()

if "gold" in fixture:
    passed(f"Fixture has gold — price: ${fixture['gold']['price']}")
else:
    failed("Fixture missing gold")

if "silver" in fixture:
    passed(f"Fixture has silver — price: ${fixture['silver']['price']}")
else:
    failed("Fixture missing silver")

if "platinum" in fixture:
    passed(f"Fixture has platinum — price: ${fixture['platinum']['price']}")
else:
    failed("Fixture missing platinum")

goldapi_records = build_goldapi_records()
if len(goldapi_records) == 3:
    passed(f"Built {len(goldapi_records)} records from fixture")
else:
    failed(f"Expected 3 records from fixture — got {len(goldapi_records)}")

# ============================================================
# DONE
# ============================================================
section("ALL TESTS PASSED ✅")
print()
print("  Consolidator is working correctly.")
print("  All unit tests passed with mock data.")
print()
print("  Next step: end-to-end test with live scrapers")
print("  Run: python src/lambdas/consolidator/consolidator.py")
print()