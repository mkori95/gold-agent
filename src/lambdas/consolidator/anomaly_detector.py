"""
anomaly_detector.py

Validates price records from scrapers before they enter
the consensus calculation.

A price record is rejected if:
- price_usd is None, zero, or negative
- price_usd is outside the valid range defined in metals.json
- metal field is missing

Unknown metals are allowed through with a warning —
we never silently drop data we don't understand.

This class is completely standalone — it reads metals.json
directly and has no dependency on the scraper engine.

Usage:
    detector = AnomalyDetector()

    # Validate a single record
    result = detector.validate(record)

    # Filter a list of records — returns only valid ones
    valid_records = detector.filter(records)
"""

import json
import os
import logging
from src.shared.utils.config_loader import load_json

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Validates price records against known price ranges.

    Reads valid price ranges from config/metals.json.
    Rejects records with prices outside those ranges.
    Never crashes — always returns a result.
    """

    def __init__(self):
        """
        Loads metals config on startup.
        Price ranges are read once and reused for all validations.
        """
        self.metals_config = self._load_metals_config()

    # ============================================================
    # Validate a single price record
    # ============================================================
    def validate(self, record: dict) -> dict:
        """
        Validates a single price record.

        Args:
            record: Standard price record dict from a scraper
                    Must have at minimum: metal, price_usd, source_id

        Returns:
            Dict with validation result:
            {
                "is_valid":  True/False,
                "price_usd": float or None,
                "metal":     string,
                "source_id": string,
                "reason":    None or string explaining rejection
            }
        """

        metal     = record.get("metal",     "unknown")
        price_usd = record.get("price_usd")
        source_id = record.get("source_id", "unknown")

        # --------------------------------------------------------
        # Check 1 — price_usd must exist
        # --------------------------------------------------------
        if price_usd is None:
            reason = "price_usd is None"
            logger.warning(
                f"[{source_id}] Anomaly detected for {metal} — {reason}"
            )
            return self._build_result(
                is_valid=False,
                record=record,
                reason=reason
            )

        # --------------------------------------------------------
        # Check 2 — price must be a number
        # --------------------------------------------------------
        if not isinstance(price_usd, (int, float)):
            reason = f"price_usd is not a number: {type(price_usd)}"
            logger.warning(
                f"[{source_id}] Anomaly detected for {metal} — {reason}"
            )
            return self._build_result(
                is_valid=False,
                record=record,
                reason=reason
            )

        # --------------------------------------------------------
        # Check 3 — price must be positive
        # --------------------------------------------------------
        if price_usd <= 0:
            reason = f"price_usd is zero or negative: {price_usd}"
            logger.warning(
                f"[{source_id}] Anomaly detected for {metal} — {reason}"
            )
            return self._build_result(
                is_valid=False,
                record=record,
                reason=reason
            )

        # --------------------------------------------------------
        # Check 4 — price must be within range from metals.json
        # --------------------------------------------------------
        if metal not in self.metals_config:
            # Unknown metal — let it through with a warning
            # Never silently drop data we don't understand
            logger.warning(
                f"[{source_id}] Unknown metal '{metal}' — "
                f"no price range defined — allowing through"
            )
            return self._build_result(
                is_valid=True,
                record=record,
                reason=None
            )

        metal_config = self.metals_config[metal]
        price_range  = metal_config.get("price_range_usd", {})
        min_price    = price_range.get("min")
        max_price    = price_range.get("max")

        if min_price is not None and price_usd < min_price:
            reason = (
                f"price_usd ${price_usd} is below minimum "
                f"${min_price} for {metal}"
            )
            logger.warning(
                f"[{source_id}] Anomaly detected for {metal} — {reason}"
            )
            return self._build_result(
                is_valid=False,
                record=record,
                reason=reason
            )

        if max_price is not None and price_usd > max_price:
            reason = (
                f"price_usd ${price_usd} is above maximum "
                f"${max_price} for {metal}"
            )
            logger.warning(
                f"[{source_id}] Anomaly detected for {metal} — {reason}"
            )
            return self._build_result(
                is_valid=False,
                record=record,
                reason=reason
            )

        # --------------------------------------------------------
        # All checks passed
        # --------------------------------------------------------
        logger.info(
            f"[{source_id}] {metal} price validated — "
            f"${price_usd} is within range"
        )

        return self._build_result(
            is_valid=True,
            record=record,
            reason=None
        )

    # ============================================================
    # Filter a list of records — returns only valid ones
    # ============================================================
    def filter(self, records: list) -> list:
        """
        Validates a list of price records and returns only valid ones.

        Invalid records are logged and dropped.
        Never crashes — always returns a list (may be empty).

        Args:
            records: List of standard price record dicts

        Returns:
            List of valid records only
            Empty list if all records are invalid
        """

        if not records:
            logger.warning("No records provided to filter")
            return []

        valid   = []
        invalid = []

        for record in records:
            result = self.validate(record)

            if result["is_valid"]:
                valid.append(record)
            else:
                invalid.append({
                    "source_id": record.get("source_id", "unknown"),
                    "metal":     record.get("metal",     "unknown"),
                    "price_usd": record.get("price_usd"),
                    "reason":    result["reason"]
                })

        if invalid:
            logger.warning(
                f"Anomaly detection — rejected {len(invalid)} records: "
                f"{invalid}"
            )

        logger.info(
            f"Anomaly detection complete — "
            f"{len(valid)} valid, {len(invalid)} rejected "
            f"from {len(records)} total"
        )

        return valid

    # ============================================================
    # Build standard validation result
    # ============================================================
    def _build_result(
        self,
        is_valid:  bool,
        record:    dict,
        reason:    str
    ) -> dict:
        """
        Builds the standard validation result dict.

        Args:
            is_valid: Whether the record passed validation
            record:   The original price record
            reason:   Rejection reason or None if valid

        Returns:
            Standard validation result dict
        """
        return {
            "is_valid":  is_valid,
            "price_usd": record.get("price_usd"),
            "metal":     record.get("metal",     "unknown"),
            "source_id": record.get("source_id", "unknown"),
            "reason":    reason
        }

    # ============================================================
    # Load metals config from config/metals.json
    # ============================================================
    def _load_metals_config(self) -> dict:
        """
        Loads metals.json and returns dict keyed by metal id.

        Returns:
            Dict of metal configs keyed by metal id
            Empty dict if file cannot be loaded
        """
        try:
            # config_path = os.path.join(
            #     os.path.dirname(__file__),
            #     "..", "..", "..", "config", "metals.json"
            # )
            # config_path = os.path.abspath(config_path)

            # with open(config_path, "r") as f:
            #     data = json.load(f)
            data = load_json("metals.json")

            config = {
                metal["id"]: metal
                for metal in data["metals"]
            }

            logger.info(
                f"AnomalyDetector loaded metals config — "
                f"metals: {list(config.keys())}"
            )

            return config

        except Exception as e:
            logger.error(
                f"AnomalyDetector could not load metals config — "
                f"price range validation disabled — {str(e)}"
            )
            return {}