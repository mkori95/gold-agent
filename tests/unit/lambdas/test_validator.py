"""
test_validator.py

Unit tests for the Validator class.

IMPORTANT — Always run this from project root:
    python tests/unit/lambdas/test_validator.py

What this tests:
1.  Valid result object               → is_valid True
2.  Status is "failed"                → is_valid False
3.  Status is "skipped"               → is_valid False
4.  Missing top-level required field  → is_valid False
5.  data is empty list                → is_valid False
6.  data is None                      → is_valid False
7.  data is not a list                → is_valid False
8.  records_count mismatch            → is_valid False
9.  Record missing required field     → is_valid False
10. None input                        → is_valid False
11. filter_valid() mixed list         → returns only valid results
12. filter_valid() all invalid        → returns empty list
13. filter_valid() empty list         → returns empty list
14. Result has all required fields    → all fields present
"""

import sys
import logging
from datetime import datetime, timezone

sys.path.insert(0, ".")

from src.lambdas.consolidator.validator import Validator

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
# Helper — build a mock price record
# ============================================================
def mock_record(metal="gold", price_usd=3100.00, source_id="gold_api_com"):
    return {
        "metal":       metal,
        "price_usd":   price_usd,
        "currency":    "USD",
        "price_inr":   None,
        "unit":        "troy_ounce",
        "source_id":   source_id,
        "source_name": "Gold-API.com",
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "extra":       {}
    }

# ============================================================
# Helper — build a mock scraper result
# ============================================================
def mock_result(
    source_id="gold_api_com",
    status="success",
    records=None,
    records_count=None
):
    if records is None:
        records = [
            mock_record("gold",     3100.00, source_id),
            mock_record("silver",   32.50,   source_id),
            mock_record("platinum", 980.00,  source_id),
            mock_record("copper",   4.50,    source_id),
        ]

    count = records_count if records_count is not None else len(records)

    return {
        "source_id":        source_id,
        "source_name":      "Gold-API.com",
        "status":           status,
        "data":             records,
        "error":            None,
        "duration_seconds": 0.84,
        "scraped_at":       datetime.now(timezone.utc).isoformat(),
        "records_count":    count
    }

# ============================================================
# Initialise
# ============================================================
validator = Validator()

# ============================================================
# TEST 1 — Valid result object
# ============================================================
section("TEST 1 — Valid result object")

result = validator.validate(mock_result())

if result["is_valid"] == True:
    passed("Valid result — is_valid True")
else:
    failed(f"Valid result should pass — reason: {result['reason']}")

if result["reason"] is None:
    passed("reason is None for valid result")
else:
    failed(f"reason should be None — got: {result['reason']}")

# ============================================================
# TEST 2 — Status is "failed"
# ============================================================
section("TEST 2 — Status is 'failed'")

result = validator.validate(mock_result(status="failed"))

if result["is_valid"] == False:
    passed("Status 'failed' — is_valid False")
else:
    failed("Failed status should be rejected")

if result["reason"] is not None:
    passed(f"reason populated: {result['reason']}")
else:
    failed("reason should be populated")

# ============================================================
# TEST 3 — Status is "skipped"
# ============================================================
section("TEST 3 — Status is 'skipped'")

result = validator.validate(mock_result(status="skipped"))

if result["is_valid"] == False:
    passed("Status 'skipped' — is_valid False")
else:
    failed("Skipped status should be rejected")

# ============================================================
# TEST 4 — Missing required top-level field
# ============================================================
section("TEST 4 — Missing required top-level field")

incomplete = mock_result()
del incomplete["scraped_at"]   # remove a required field

result = validator.validate(incomplete)

if result["is_valid"] == False:
    passed("Missing 'scraped_at' field — is_valid False")
else:
    failed("Missing required field should be rejected")

if result["reason"] is not None:
    passed(f"reason populated: {result['reason']}")
else:
    failed("reason should be populated")

# ============================================================
# TEST 5 — data is empty list
# ============================================================
section("TEST 5 — data is empty list")

result = validator.validate(mock_result(records=[], records_count=0))

if result["is_valid"] == False:
    passed("Empty data list — is_valid False")
else:
    failed("Empty data should be rejected")

if result["reason"] is not None:
    passed(f"reason populated: {result['reason']}")
else:
    failed("reason should be populated")

# ============================================================
# TEST 6 — data is None
# ============================================================
section("TEST 6 — data is None")

result_obj = mock_result()
result_obj["data"] = None

result = validator.validate(result_obj)

if result["is_valid"] == False:
    passed("data=None — is_valid False")
else:
    failed("None data should be rejected")

# ============================================================
# TEST 7 — data is not a list
# ============================================================
section("TEST 7 — data is not a list")

result_obj = mock_result()
result_obj["data"] = "not a list"

result = validator.validate(result_obj)

if result["is_valid"] == False:
    passed("data as string — is_valid False")
else:
    failed("Non-list data should be rejected")

# ============================================================
# TEST 8 — records_count mismatch
# ============================================================
section("TEST 8 — records_count mismatch")

# 4 records in data but records_count says 2
result = validator.validate(mock_result(records_count=2))

if result["is_valid"] == False:
    passed("records_count mismatch — is_valid False")
else:
    failed("Mismatched records_count should be rejected")

if result["reason"] is not None:
    passed(f"reason populated: {result['reason']}")
else:
    failed("reason should be populated")

# ============================================================
# TEST 9 — Record missing required field
# ============================================================
section("TEST 9 — Record missing required field")

bad_record = mock_record()
del bad_record["metal"]   # remove required field from record

result = validator.validate(mock_result(
    records=[bad_record],
    records_count=1
))

if result["is_valid"] == False:
    passed("Record missing 'metal' field — is_valid False")
else:
    failed("Record with missing field should be rejected")

if result["reason"] is not None:
    passed(f"reason populated: {result['reason']}")
else:
    failed("reason should be populated")

# ============================================================
# TEST 10 — None input
# ============================================================
section("TEST 10 — None input")

result = validator.validate(None)

if result["is_valid"] == False:
    passed("None input — is_valid False")
else:
    failed("None input should be rejected")

# ============================================================
# TEST 11 — filter_valid() with mixed valid and invalid results
# ============================================================
section("TEST 11 — filter_valid() with mixed results")

mixed = [
    mock_result("gold_api_com"),                    # valid
    mock_result("metals_dev", status="failed"),     # invalid — failed
    mock_result("goldapi_io"),                      # valid
    mock_result("goodreturns", status="skipped"),   # invalid — skipped
]

valid_results = validator.filter_valid(mixed)

if len(valid_results) == 2:
    passed("filter_valid() returned 2 valid results from 4 total")
else:
    failed(f"Expected 2 valid results — got {len(valid_results)}")

valid_sources = [r["source_id"] for r in valid_results]

if "gold_api_com" in valid_sources:
    passed("gold_api_com included")
else:
    failed("gold_api_com should be included")

if "goldapi_io" in valid_sources:
    passed("goldapi_io included")
else:
    failed("goldapi_io should be included")

if "metals_dev" not in valid_sources:
    passed("metals_dev (failed) correctly excluded")
else:
    failed("metals_dev should be excluded")

if "goodreturns" not in valid_sources:
    passed("goodreturns (skipped) correctly excluded")
else:
    failed("goodreturns should be excluded")

# ============================================================
# TEST 12 — filter_valid() all invalid
# ============================================================
section("TEST 12 — filter_valid() all invalid")

all_invalid = [
    mock_result("source_a", status="failed"),
    mock_result("source_b", status="skipped"),
    mock_result("source_c", records=[], records_count=0),
]

valid_results = validator.filter_valid(all_invalid)

if len(valid_results) == 0:
    passed("filter_valid() returned empty list when all invalid")
else:
    failed(f"Expected 0 valid results — got {len(valid_results)}")

# ============================================================
# TEST 13 — filter_valid() empty list
# ============================================================
section("TEST 13 — filter_valid() empty list")

valid_results = validator.filter_valid([])

if valid_results == []:
    passed("filter_valid() returned empty list for empty input")
else:
    failed(f"Expected empty list — got {valid_results}")

# ============================================================
# TEST 14 — Result has all required fields
# ============================================================
section("TEST 14 — Validation result has all required fields")

required_fields = ["is_valid", "source_id", "reason"]

result = validator.validate(mock_result())

for field in required_fields:
    if field in result:
        passed(f"Field present: {field} = {result[field]}")
    else:
        failed(f"Field MISSING: {field}")

# ============================================================
# DONE
# ============================================================
section("ALL TESTS PASSED ✅")
print()
print("  Validator is working correctly.")
print("  Safe to proceed to merger.py")
print()