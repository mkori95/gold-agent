"""
Unit tests for DynamoWriter and S3Writer.
boto3 calls are mocked so these tests run without AWS credentials.

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
9.  write() writes 2 paths -- timestamped + latest.json
10. write() handles empty snapshot gracefully
11. S3 path built correctly from snapshot_id
12. Result has all required fields
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from src.lambdas.consolidator.dynamo_writer import DynamoWriter
from src.lambdas.consolidator.s3_writer import S3Writer


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
                "source_prices":  {"gold_api_com": 3100.00, "metals_dev": 3098.00, "goldapi_io": 3106.50},
                "spread_percent": 0.27,
                "spread_flagged": False,
                "karats":         {"24K": {"price_usd": 3101.19, "price_inr": 281890.0}},
                "city_rates":     {"mumbai": {"24K": 139720.0}},
                "extra":          {"mcx_gold": 3250.00, "ibja_gold": 3210.00,
                                   "lbma_gold_am": 3088.50, "lbma_gold_pm": 3092.75}
            },
            "silver": {
                "price_usd":      32.45,
                "price_inr":      2951.0,
                "unit":           "troy_ounce",
                "confidence":     "high",
                "sources_used":   ["gold_api_com", "metals_dev"],
                "sources_count":  3,
                "source_prices":  {"gold_api_com": 32.50, "metals_dev": 32.30, "goldapi_io": 32.55},
                "spread_percent": 0.77,
                "spread_flagged": False,
                "karats":         {},
                "city_rates":     {},
                "extra":          {}
            }
        }
    }


# ============================================================
# DynamoWriter tests
# ============================================================

def test_dynamo_writer_init():
    with patch("boto3.resource") as mock_resource:
        mock_resource.return_value.Table.return_value = MagicMock()
        writer = DynamoWriter()
        assert writer is not None


def test_dynamo_write_success():
    with patch("boto3.resource") as mock_resource:
        mock_table = MagicMock()
        mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        mock_resource.return_value.Table.return_value = mock_table
        writer = DynamoWriter()
        result = writer.write(mock_snapshot())
    assert result["status"] == "success"


def test_dynamo_write_records_written_count():
    with patch("boto3.resource") as mock_resource:
        mock_table = MagicMock()
        mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        mock_resource.return_value.Table.return_value = mock_table
        writer = DynamoWriter()
        result = writer.write(mock_snapshot())
    # Snapshot has 2 metals
    assert result["records_written"] == 2


def test_dynamo_write_empty_snapshot():
    with patch("boto3.resource") as mock_resource:
        mock_resource.return_value.Table.return_value = MagicMock()
        writer = DynamoWriter()
        result = writer.write({})
    assert result["status"] == "skipped"
    assert result["records_written"] == 0


def test_dynamo_write_none_snapshot():
    with patch("boto3.resource") as mock_resource:
        mock_resource.return_value.Table.return_value = MagicMock()
        writer = DynamoWriter()
        result = writer.write(None)
    assert result["status"] == "skipped"


def test_dynamo_result_required_fields():
    with patch("boto3.resource") as mock_resource:
        mock_table = MagicMock()
        mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        mock_resource.return_value.Table.return_value = mock_table
        writer = DynamoWriter()
        result = writer.write(mock_snapshot())
    for field in ["status", "table", "records_written", "reason", "written_at"]:
        assert field in result, f"Field missing: {field}"


# ============================================================
# S3Writer tests
# ============================================================

def test_s3_writer_init():
    with patch("boto3.client") as mock_client:
        mock_client.return_value = MagicMock()
        writer = S3Writer()
        assert writer is not None


def test_s3_write_success():
    with patch("boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        mock_client.return_value = mock_s3
        writer = S3Writer()
        result = writer.write(mock_snapshot())
    assert result["status"] == "success"


def test_s3_write_two_paths():
    with patch("boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        mock_client.return_value = mock_s3
        writer = S3Writer()
        result = writer.write(mock_snapshot())
    assert result["files_count"] == 2
    paths = result["paths_written"]
    timestamped = [p for p in paths if "latest" not in p]
    latest = [p for p in paths if "latest" in p]
    assert len(timestamped) == 1
    assert len(latest) == 1


def test_s3_write_empty_snapshot():
    with patch("boto3.client") as mock_client:
        mock_client.return_value = MagicMock()
        writer = S3Writer()
        result = writer.write({})
    assert result["status"] == "skipped"
    assert result["files_count"] == 0


def test_s3_path_built_correctly():
    with patch("boto3.client") as mock_client:
        mock_client.return_value = MagicMock()
        writer = S3Writer()
    actual_path = writer._build_s3_path("2026-03-01T14:00:00+00:00")
    assert actual_path == "prices/2026/03/01/14:00.json"


def test_s3_result_required_fields():
    with patch("boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        mock_client.return_value = mock_s3
        writer = S3Writer()
        result = writer.write(mock_snapshot())
    for field in ["status", "bucket", "paths_written", "files_count", "reason", "written_at"]:
        assert field in result, f"Field missing: {field}"
