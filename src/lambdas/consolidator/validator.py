"""
validator.py

Validates scraper result objects before the consolidator
processes them.

This is a structural check — it verifies that the scraper
result has the correct shape and required fields.

It does NOT check if prices are within valid ranges —
that is AnomalyDetector's job.

Two levels of validation:
    1. Result level  — checks the wrapper object from run()
    2. Record level  — checks each price record inside data[]

A result is rejected if:
    - status is not "success"
    - required top-level fields are missing
    - data is None or empty list
    - records_count does not match len(data)
    - any price record is missing required fields

Usage:
    validator = Validator()

    # Validate a single scraper result
    result = validator.validate(scraper_result)

    # Filter a list of scraper results — returns only valid ones
    valid_results = validator.filter_valid(scraper_results)
"""

import logging

logger = logging.getLogger(__name__)

# Required fields on the scraper result wrapper
REQUIRED_RESULT_FIELDS = [
    "source_id",
    "source_name",
    "status",
    "data",
    "error",
    "duration_seconds",
    "scraped_at",
    "records_count"
]

# Required fields on each price record inside data[]
REQUIRED_RECORD_FIELDS = [
    "metal",
    "price_usd",
    "source_id",
    "unit",
    "timestamp"
]


class Validator:
    """
    Validates scraper result objects before consolidation.

    Checks structure and completeness — not price values.
    Price value validation is handled by AnomalyDetector.
    """

    # ============================================================
    # Validate a single scraper result
    # ============================================================
    def validate(self, scraper_result: dict) -> dict:
        """
        Validates a single scraper result object.

        Args:
            scraper_result: The full result dict returned by scraper.run()

        Returns:
            Dict with validation result:
            {
                "is_valid":  True/False,
                "source_id": string,
                "reason":    None or string explaining rejection
            }
        """

        # Handle None input gracefully
        if scraper_result is None:
            logger.warning("Received None scraper result")
            return self._build_result(
                is_valid=False,
                source_id="unknown",
                reason="scraper_result is None"
            )

        source_id = scraper_result.get("source_id", "unknown")

        # --------------------------------------------------------
        # Check 1 — all required top-level fields must be present
        # --------------------------------------------------------
        for field in REQUIRED_RESULT_FIELDS:
            if field not in scraper_result:
                reason = f"missing required field: '{field}'"
                logger.warning(
                    f"[{source_id}] Validation failed — {reason}"
                )
                return self._build_result(
                    is_valid=False,
                    source_id=source_id,
                    reason=reason
                )

        # --------------------------------------------------------
        # Check 2 — status must be "success"
        # --------------------------------------------------------
        status = scraper_result.get("status")

        if status != "success":
            reason = f"status is '{status}' — only 'success' results are processed"
            logger.info(
                f"[{source_id}] Skipping result — {reason}"
            )
            return self._build_result(
                is_valid=False,
                source_id=source_id,
                reason=reason
            )

        # --------------------------------------------------------
        # Check 3 — data must exist and not be empty
        # --------------------------------------------------------
        data = scraper_result.get("data")

        if data is None:
            reason = "data is None"
            logger.warning(
                f"[{source_id}] Validation failed — {reason}"
            )
            return self._build_result(
                is_valid=False,
                source_id=source_id,
                reason=reason
            )

        if not isinstance(data, list):
            reason = f"data is not a list — got {type(data)}"
            logger.warning(
                f"[{source_id}] Validation failed — {reason}"
            )
            return self._build_result(
                is_valid=False,
                source_id=source_id,
                reason=reason
            )

        if len(data) == 0:
            reason = "data is empty — no price records returned"
            logger.warning(
                f"[{source_id}] Validation failed — {reason}"
            )
            return self._build_result(
                is_valid=False,
                source_id=source_id,
                reason=reason
            )

        # --------------------------------------------------------
        # Check 4 — records_count must match len(data)
        # --------------------------------------------------------
        records_count = scraper_result.get("records_count")

        if records_count != len(data):
            reason = (
                f"records_count ({records_count}) does not match "
                f"len(data) ({len(data)})"
            )
            logger.warning(
                f"[{source_id}] Validation failed — {reason}"
            )
            return self._build_result(
                is_valid=False,
                source_id=source_id,
                reason=reason
            )

        # --------------------------------------------------------
        # Check 5 — every price record must have required fields
        # --------------------------------------------------------
        for i, record in enumerate(data):
            record_check = self._validate_record(record, source_id, i)
            if not record_check["is_valid"]:
                return self._build_result(
                    is_valid=False,
                    source_id=source_id,
                    reason=record_check["reason"]
                )

        # --------------------------------------------------------
        # All checks passed
        # --------------------------------------------------------
        logger.info(
            f"[{source_id}] Validation passed — "
            f"{len(data)} records ready for consolidation"
        )

        return self._build_result(
            is_valid=True,
            source_id=source_id,
            reason=None
        )

    # ============================================================
    # Filter a list of scraper results — returns only valid ones
    # ============================================================
    def filter_valid(self, scraper_results: list) -> list:
        """
        Validates a list of scraper results and returns valid ones only.

        Args:
            scraper_results: List of scraper result dicts from run()

        Returns:
            List of valid scraper results only
            Empty list if none are valid
        """

        if not scraper_results:
            logger.warning("No scraper results provided to filter")
            return []

        valid   = []
        invalid = []

        for result in scraper_results:
            validation = self.validate(result)

            if validation["is_valid"]:
                valid.append(result)
            else:
                invalid.append({
                    "source_id": validation["source_id"],
                    "reason":    validation["reason"]
                })

        if invalid:
            logger.warning(
                f"Validator filtered out {len(invalid)} results: {invalid}"
            )

        logger.info(
            f"Validator complete — "
            f"{len(valid)} valid, {len(invalid)} invalid "
            f"from {len(scraper_results)} total"
        )

        return valid

    # ============================================================
    # Validate a single price record inside data[]
    # ============================================================
    def _validate_record(
        self,
        record:    dict,
        source_id: str,
        index:     int
    ) -> dict:
        """
        Validates a single price record inside data[].

        Checks that all required fields are present.
        Does not check price values — that is AnomalyDetector's job.

        Args:
            record:    The price record dict
            source_id: Parent source id for logging
            index:     Record index for logging

        Returns:
            Dict with is_valid and reason
        """

        for field in REQUIRED_RECORD_FIELDS:
            if field not in record:
                reason = (
                    f"record[{index}] missing required field: '{field}'"
                )
                logger.warning(
                    f"[{source_id}] Record validation failed — {reason}"
                )
                return {"is_valid": False, "reason": reason}

        return {"is_valid": True, "reason": None}

    # ============================================================
    # Build standard validation result
    # ============================================================
    def _build_result(
        self,
        is_valid:  bool,
        source_id: str,
        reason:    str
    ) -> dict:
        """
        Builds standard validation result dict.

        Args:
            is_valid:  Whether validation passed
            source_id: Source id for reference
            reason:    Rejection reason or None

        Returns:
            Standard validation result dict
        """
        return {
            "is_valid":  is_valid,
            "source_id": source_id,
            "reason":    reason
        }