import json
import os
from datetime import date, timedelta
from typing import Optional, Tuple

import boto3
from botocore.exceptions import ClientError

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)

S3_BUCKET  = os.environ.get("S3_BUCKET_NAME") or "gold-agent-prices"
S3_PREFIX  = "prices"
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
MAX_LOOKBACK_DAYS = 14


def _s3_client():
    return boto3.client("s3", region_name=AWS_REGION)


def _list_keys_for_date(s3, target_date: date) -> list[str]:
    prefix = (
        f"{S3_PREFIX}/"
        f"{target_date.year:04d}/"
        f"{target_date.month:02d}/"
        f"{target_date.day:02d}/"
    )
    try:
        resp = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        return [obj["Key"] for obj in resp.get("Contents", [])]
    except ClientError:
        return []


def _read_key(s3, key: str) -> Optional[dict]:
    try:
        resp = s3.get_object(Bucket=S3_BUCKET, Key=key)
        return json.loads(resp["Body"].read())
    except Exception as e:
        logger.warning(f"S3Reader: failed to read {key} — {e}")
        return None


def get_snapshot_for_date(target_date: date) -> Tuple[Optional[dict], Optional[str]]:
    """
    Returns (snapshot_dict, actual_date_str) for the most recent snapshot
    on or before target_date. Walks back up to MAX_LOOKBACK_DAYS if the
    exact date has no snapshot. Returns (None, None) if nothing found.

    actual_date_str is the date the data was actually found on — always
    include this in any user-facing comparison so they know what's being compared.
    """
    s3 = _s3_client()

    for days_back in range(MAX_LOOKBACK_DAYS):
        check_date = target_date - timedelta(days=days_back)
        keys = _list_keys_for_date(s3, check_date)
        if not keys:
            continue
        # Take the latest file for that day (keys are HH:MM.json — sort gives chronological order)
        latest_key = sorted(keys)[-1]
        snapshot = _read_key(s3, latest_key)
        if snapshot:
            actual_date_str = check_date.strftime("%d %b %Y")
            if days_back > 0:
                logger.info(
                    f"S3Reader: no snapshot for {target_date} — "
                    f"fell back to {check_date} ({days_back} days back)"
                )
            return snapshot, actual_date_str

    logger.warning(f"S3Reader: no snapshot found within {MAX_LOOKBACK_DAYS} days of {target_date}")
    return None, None


def get_price_for_metal(snapshot: dict, metal: str) -> dict:
    """
    Extracts the key per-gram INR prices for a metal from a raw S3 snapshot dict.
    Returns a flat dict with price_22k_inr, price_24k_inr, price_18k_inr, price_inr_per_gram.
    """
    metal_data = snapshot.get("metals", {}).get(metal, {})
    city_rates = metal_data.get("city_rates", {})

    INTERNATIONAL = {"united-states", "united-kingdom", "dubai"}
    indian_rates = {k: v for k, v in city_rates.items() if k not in INTERNATIONAL}

    prices_22k = [
        v.get("22K") for v in indian_rates.values()
        if isinstance(v, dict) and v.get("22K")
    ]
    prices_24k = [
        v.get("24K") for v in indian_rates.values()
        if isinstance(v, dict) and v.get("24K")
    ]

    price_22k = round(sum(prices_22k) / len(prices_22k) / 10, 2) if prices_22k else None
    price_24k = round(sum(prices_24k) / len(prices_24k) / 10, 2) if prices_24k else None
    price_18k = round(price_22k * 18 / 22, 2) if price_22k else None

    # For silver/platinum — per-gram from troy oz price
    price_inr = metal_data.get("price_inr")
    price_per_gram = round(price_inr / 31.1035, 2) if price_inr else None

    return {
        "price_22k": price_22k,
        "price_24k": price_24k,
        "price_18k": price_18k,
        "price_per_gram": price_per_gram,
    }
