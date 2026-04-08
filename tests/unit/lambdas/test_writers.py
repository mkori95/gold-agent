"""
test_writers.py

Unit tests for DynamoWriter and S3Writer.

boto3 calls are mocked so these tests run without AWS credentials.
For a real end-to-end write test, run the consolidator directly:
    python src/lambdas/consolidator/consolidator.py

IMPORTANT — Always run this from project root:
    python tests/unit/lambdas/test_writers.py

What this tests:
--- DynamoWriter ---
1.  Initialises without errors
2.  write() returns success status
3.  write() returns correct records_written count
4.  write() handles empty snapshot gracefully
5.  write() handles None gracefully
6.  Result has all required fields

--- S3Writer ---
7.  Initialises without errors
8.  write() returns success status
9.  write() writes 2 paths — timestamped + latest.json
10. write() handles empty snapshot gracefully
11. S3 path built correctly from snapshot_id
12. Result has all required fields
"""

import sys
import logging
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

sys.path.insert(0, ".")

from src.lambdas.consolidator.dynamo_writer import DynamoWriter
from src.lambdas.consolidator.s3_writer     import S3Writer

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
# Mock snapshot — realistic structure
# ============================================================
def mock_snapshot():
    return {
        "snapshot_id":    "2026-03-01T14:00:00+00:00",
        "consolidated_at": datetime.now(timezone.utc).isoformat(),
        "inr_rate":       0.01099,
        "usd_to_inr":     90.99,
        "metals": {
            "gold": {
                "price_usd":      3101.50,
                "price_inr":      282120.0,
                "unit":           "troy_ounce",
                "confidence":     "high",
                "sources_used":   ["gold_api_com", "metals_dev"],
                "sources_count":  3,
                "source_prices":  {
                    "gold_api_com": 3100.00,
                    "metals_dev":   3098.00,
                    "goldapi_io":   3106.50
                },
                "spread_percent": 0.27,
                "spread_flagged": False,
                "karats": {
                    "24K": {"price_usd": 3101.19, "price_inr": 281890.0},
                    "22K": {"price_usd": 2842.26, "price_inr": 258400.0},
                    "18K": {"price_usd": 2326.13, "price_inr": 211590.0}
                },
                "city_rates": {
                    "mumbai":  {"24K": 139720.0, "22K": 128077.0, "18K": 104790.0},
                    "delhi":   {"24K": 139500.0, "22K": 127900.0, "18K": 104600.0},
                    "chennai": {"24K": 139800.0, "22K": 128100.0, "18K": 104850.0}
                },
                "extra": {
                    "mcx_gold":     3250.00,
                    "ibja_gold":    3210.00,
                    "lbma_gold_am": 3088.50,
                    "lbma_gold_pm": 3092.75
                }
            },
            "silver": {
                "price_usd":      32.45,
                "price_inr":      2951.0,
                "unit":           "troy_ounce",
                "confidence":     "high",
                "sources_used":   ["gold_api_com", "metals_dev"],
                "sources_count":  3,
                "source_prices":  {
                    "gold_api_com": 32.50,
                    "metals_dev":   32.30,
                    "goldapi_io":   32.55
                },
                "spread_percent": 0.77,
                "spread_flagged": False,
                "karats":         {},
                "city_rates":     {
                    "mumbai": {"999 Fine": 225530.0, "925 Sterling": 208615.0}
                },
                "extra":          {}
            }
        }
    }

# ============================================================
# ============================================================
# DYNAMO WRITER TESTS
# ============================================================
# ============================================================

section("DYNAMO WRITER TESTS")

# ============================================================
# TEST 1 — DynamoWriter initialises without errors
# ============================================================
section("TEST 1 — DynamoWriter initialises without errors")

with patch("boto3.resource") as mock_resource:
    mock_table = MagicMock()
    mock_resource.return_value.Table.return_value = mock_table

    try:
        dynamo_writer = DynamoWriter()
        passed(f"DynamoWriter initialised — table: {dynamo_writer.table_name}")
    except Exception as e:
        failed(f"DynamoWriter failed to initialise — {str(e)}")

# ============================================================
# TEST 2 — write() returns success status
# ============================================================
section("TEST 2 — write() returns success status")

with patch("boto3.resource") as mock_resource:
    mock_table = MagicMock()
    mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    mock_resource.return_value.Table.return_value = mock_table

    dynamo_writer = DynamoWriter()
    result = dynamo_writer.write(mock_snapshot())

if result["status"] == "success":
    passed("write() returned status 'success'")
else:
    failed(f"Expected status 'success' — got '{result['status']}'")

# ============================================================
# TEST 3 — write() returns correct records_written count
# ============================================================
section("TEST 3 — write() records_written count")

with patch("boto3.resource") as mock_resource:
    mock_table = MagicMock()
    mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    mock_resource.return_value.Table.return_value = mock_table

    dynamo_writer = DynamoWriter()
    result = dynamo_writer.write(mock_snapshot())

# Snapshot has 2 metals — gold and silver
if result["records_written"] == 2:
    passed(f"records_written = 2 (one per metal)")
else:
    failed(f"Expected records_written=2 — got {result['records_written']}")

# ============================================================
# TEST 4 — write() handles empty snapshot gracefully
# ============================================================
section("TEST 4 — write() handles empty snapshot gracefully")

with patch("boto3.resource") as mock_resource:
    mock_table = MagicMock()
    mock_resource.return_value.Table.return_value = mock_table

    dynamo_writer = DynamoWriter()
    result = dynamo_writer.write({})

if result["status"] == "skipped":
    passed("Empty snapshot — status 'skipped'")
else:
    failed(f"Expected 'skipped' — got '{result['status']}'")

if result["records_written"] == 0:
    passed("records_written = 0 for empty snapshot")
else:
    failed(f"Expected 0 — got {result['records_written']}")

# ============================================================
# TEST 5 — write() handles None gracefully
# ============================================================
section("TEST 5 — write() handles None gracefully")

with patch("boto3.resource") as mock_resource:
    mock_table = MagicMock()
    mock_resource.return_value.Table.return_value = mock_table

    dynamo_writer = DynamoWriter()
    result = dynamo_writer.write(None)

if result["status"] == "skipped":
    passed("None snapshot — status 'skipped'")
else:
    failed(f"Expected 'skipped' — got '{result['status']}'")

# ============================================================
# TEST 6 — DynamoWriter result has required fields
# ============================================================
section("TEST 6 — DynamoWriter result has required fields")

with patch("boto3.resource") as mock_resource:
    mock_table = MagicMock()
    mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    mock_resource.return_value.Table.return_value = mock_table

    dynamo_writer = DynamoWriter()
    result = dynamo_writer.write(mock_snapshot())

required_fields = ["status", "table", "records_written", "reason", "written_at"]

for field in required_fields:
    if field in result:
        passed(f"Field present: {field} = {result[field]}")
    else:
        failed(f"Field MISSING: {field}")

# ============================================================
# ============================================================
# S3 WRITER TESTS
# ============================================================
# ============================================================

section("S3 WRITER TESTS")

# ============================================================
# TEST 7 — S3Writer initialises without errors
# ============================================================
section("TEST 7 — S3Writer initialises without errors")

with patch("boto3.client") as mock_client:
    mock_s3 = MagicMock()
    mock_client.return_value = mock_s3

    try:
        s3_writer = S3Writer()
        passed(f"S3Writer initialised — bucket: {s3_writer.bucket}")
    except Exception as e:
        failed(f"S3Writer failed to initialise — {str(e)}")

# ============================================================
# TEST 8 — write() returns success status
# ============================================================
section("TEST 8 — write() returns success status")

with patch("boto3.client") as mock_client:
    mock_s3 = MagicMock()
    mock_s3.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    mock_client.return_value = mock_s3

    s3_writer = S3Writer()
    result = s3_writer.write(mock_snapshot())

if result["status"] == "success":
    passed("write() returned status 'success'")
else:
    failed(f"Expected status 'success' — got '{result['status']}'")

# ============================================================
# TEST 9 — write() writes 2 paths — timestamped + latest.json
# ============================================================
section("TEST 9 — write() writes 2 paths")

with patch("boto3.client") as mock_client:
    mock_s3 = MagicMock()
    mock_s3.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    mock_client.return_value = mock_s3

    s3_writer = S3Writer()
    result = s3_writer.write(mock_snapshot())

if result["files_count"] == 2:
    passed(f"files_count = 2")
else:
    failed(f"Expected files_count=2 — got {result['files_count']}")

paths = result["paths_written"]

timestamped = [p for p in paths if "latest" not in p]
latest      = [p for p in paths if "latest" in p]

if len(timestamped) == 1:
    passed(f"Timestamped path written: {timestamped[0]}")
else:
    failed("Expected 1 timestamped path")

if len(latest) == 1:
    passed(f"latest.json path written: {latest[0]}")
else:
    failed("Expected 1 latest.json path")

# ============================================================
# TEST 10 — write() handles empty snapshot gracefully
# ============================================================
section("TEST 10 — write() handles empty snapshot gracefully")

with patch("boto3.client") as mock_client:
    mock_s3 = MagicMock()
    mock_client.return_value = mock_s3

    s3_writer = S3Writer()
    result = s3_writer.write({})

if result["status"] == "skipped":
    passed("Empty snapshot — status 'skipped'")
else:
    failed(f"Expected 'skipped' — got '{result['status']}'")

if result["files_count"] == 0:
    passed("files_count = 0 for empty snapshot")
else:
    failed(f"Expected 0 — got {result['files_count']}")

# ============================================================
# TEST 11 — S3 path built correctly from snapshot_id
# ============================================================
section("TEST 11 — S3 path built correctly from snapshot_id")

snapshot_id   = "2026-03-01T14:00:00+00:00"
expected_path = "prices/2026/03/01/14:00.json"

with patch("boto3.client") as mock_client:
    mock_client.return_value = MagicMock()
    s3_writer_instance = S3Writer()

actual_path = s3_writer_instance._build_s3_path(snapshot_id)

if actual_path == expected_path:
    passed(f"S3 path correct: {actual_path}")
else:
    failed(f"Expected '{expected_path}' — got '{actual_path}'")

# ============================================================
# TEST 12 — S3Writer result has required fields
# ============================================================
section("TEST 12 — S3Writer result has required fields")

with patch("boto3.client") as mock_client:
    mock_s3 = MagicMock()
    mock_s3.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    mock_client.return_value = mock_s3

    s3_writer = S3Writer()
    result = s3_writer.write(mock_snapshot())

required_fields = ["status", "bucket", "paths_written", "files_count", "reason", "written_at"]

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
print("  DynamoWriter and S3Writer working correctly.")
print("  boto3 calls mocked — unit tests pass without AWS credentials.")
print("  For real write test: python src/lambdas/consolidator/consolidator.py")
print()
