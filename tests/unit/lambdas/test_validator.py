"""
Unit tests for the Validator class.

What this tests:
1.  Valid result object               -> is_valid True
2.  Status is "failed"                -> is_valid False
3.  Status is "skipped"               -> is_valid False
4.  Missing top-level required field  -> is_valid False
5.  data is empty list                -> is_valid False
6.  data is None                      -> is_valid False
7.  data is not a list                -> is_valid False
8.  records_count mismatch            -> is_valid False
9.  Record missing required field     -> is_valid False
10. None input                        -> is_valid False
11. filter_valid() mixed list         -> returns only valid results
12. filter_valid() all invalid        -> returns empty list
13. filter_valid() empty list         -> returns empty list
14. Result has all required fields    -> all fields present
"""
import pytest
from datetime import datetime, timezone
from src.lambdas.consolidator.validator import Validator


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


def mock_result(source_id="gold_api_com", status="success", records=None, records_count=None):
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


@pytest.fixture(scope="module")
def validator():
    return Validator()


def test_valid_result(validator):
    result = validator.validate(mock_result())
    assert result["is_valid"] is True
    assert result["reason"] is None


def test_failed_status_rejected(validator):
    result = validator.validate(mock_result(status="failed"))
    assert result["is_valid"] is False
    assert result["reason"] is not None


def test_skipped_status_rejected(validator):
    result = validator.validate(mock_result(status="skipped"))
    assert result["is_valid"] is False


def test_missing_required_field_rejected(validator):
    incomplete = mock_result()
    del incomplete["scraped_at"]
    result = validator.validate(incomplete)
    assert result["is_valid"] is False
    assert result["reason"] is not None


def test_empty_data_rejected(validator):
    result = validator.validate(mock_result(records=[], records_count=0))
    assert result["is_valid"] is False
    assert result["reason"] is not None


def test_none_data_rejected(validator):
    result_obj = mock_result()
    result_obj["data"] = None
    result = validator.validate(result_obj)
    assert result["is_valid"] is False


def test_non_list_data_rejected(validator):
    result_obj = mock_result()
    result_obj["data"] = "not a list"
    result = validator.validate(result_obj)
    assert result["is_valid"] is False


def test_records_count_mismatch_rejected(validator):
    # 4 records in data but records_count says 2
    result = validator.validate(mock_result(records_count=2))
    assert result["is_valid"] is False
    assert result["reason"] is not None


def test_record_missing_field_rejected(validator):
    bad_record = mock_record()
    del bad_record["metal"]
    result = validator.validate(mock_result(records=[bad_record], records_count=1))
    assert result["is_valid"] is False
    assert result["reason"] is not None


def test_none_input_rejected(validator):
    result = validator.validate(None)
    assert result["is_valid"] is False


def test_filter_valid_mixed(validator):
    mixed = [
        mock_result("gold_api_com"),                    # valid
        mock_result("metals_dev", status="failed"),     # invalid
        mock_result("goldapi_io"),                      # valid
        mock_result("goodreturns", status="skipped"),   # invalid
    ]
    valid_results = validator.filter_valid(mixed)
    assert len(valid_results) == 2
    valid_sources = [r["source_id"] for r in valid_results]
    assert "gold_api_com" in valid_sources
    assert "goldapi_io" in valid_sources
    assert "metals_dev" not in valid_sources
    assert "goodreturns" not in valid_sources


def test_filter_valid_all_invalid(validator):
    all_invalid = [
        mock_result("source_a", status="failed"),
        mock_result("source_b", status="skipped"),
        mock_result("source_c", records=[], records_count=0),
    ]
    assert validator.filter_valid(all_invalid) == []


def test_filter_valid_empty_list(validator):
    assert validator.filter_valid([]) == []


def test_result_required_fields(validator):
    result = validator.validate(mock_result())
    for field in ["is_valid", "source_id", "reason"]:
        assert field in result, f"Field missing: {field}"
