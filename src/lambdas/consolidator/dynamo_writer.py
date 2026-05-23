"""
dynamo_writer.py

Writes consolidated price snapshot to DynamoDB.

DynamoDB table: gold-agent-live-prices
Purpose: Stores the latest consensus price per metal so
         the WhatsApp bot can read it with low latency.

Writes one record per metal — always overwrites previous.
Metal id is the partition key.

Table name is read from DYNAMO_LIVE_PRICES_TABLE env var,
defaulting to "gold-agent-live-prices".

Usage:
    writer = DynamoWriter()
    result = writer.write(snapshot)
"""

import os
import logging
from src.shared.utils.logger import get_logger
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = get_logger(__name__)

LIVE_PRICES_TABLE = os.environ.get("DYNAMO_LIVE_PRICES_TABLE", "gold-agent-live-prices")
AWS_REGION        = os.environ.get("AWS_REGION", "ap-south-1")

# Indian 22K gold floor — off-hours RapidAPI returns ~₹895/gram (stale); real price is ₹14,000+
MIN_GOLD_22K_PER_GRAM = 8_000


class DynamoWriter:
    """
    Writes consolidated snapshot to DynamoDB live prices table.

    One record per metal, always overwrites previous.
    Metal id is the partition key.
    """

    def __init__(self):
        """
        Initialises DynamoWriter with boto3 DynamoDB resource.
        """
        self.table_name = LIVE_PRICES_TABLE

        try:
            dynamodb   = boto3.resource("dynamodb", region_name=AWS_REGION)
            self.table = dynamodb.Table(self.table_name)
            logger.info(
                f"DynamoWriter initialised — table: {self.table_name}"
            )
        except Exception as e:
            self.table = None
            logger.error(
                f"DynamoWriter: boto3 init failed — {str(e)}"
            )

    # ============================================================
    # Write full snapshot to DynamoDB
    # ============================================================
    def write(self, snapshot: dict) -> dict:
        """
        Writes consolidated snapshot to DynamoDB.

        Writes one record per metal — always overwrites previous.
        Metal id is the partition key.

        Args:
            snapshot: Full consolidated snapshot dict from consolidator

        Returns:
            Dict with status and metadata
        """

        if not snapshot:
            logger.warning("DynamoWriter received empty snapshot — nothing to write")
            return self._build_result(
                status="skipped",
                records_written=0,
                reason="empty snapshot"
            )

        metals = snapshot.get("metals", {})

        if not metals:
            logger.warning("DynamoWriter snapshot has no metals — nothing to write")
            return self._build_result(
                status="skipped",
                records_written=0,
                reason="no metals in snapshot"
            )

        if not self.table:
            logger.error("DynamoWriter: table not initialised — skipping write")
            return self._build_result(
                status="failed",
                records_written=0,
                reason="DynamoDB table not initialised"
            )

        records_written  = 0
        records_skipped  = 0
        skip_reasons     = []

        logger.info(
            f"DynamoWriter starting — "
            f"{len(metals)} metals to evaluate: {list(metals.keys())} — "
            f"snapshot_id: {snapshot.get('snapshot_id')}"
        )

        for metal, metal_data in metals.items():
            try:
                sources_count = metal_data.get("sources_count", 0)
                sources_used  = metal_data.get("sources_used", [])

                # ── Guard 1: minimum 2 spot-price sources for gold ──────────
                if metal == "gold" and sources_count < 2:
                    reason = f"only {sources_count} source ({sources_used}) — need ≥2"
                    logger.warning(f"[GOLD] SKIPPED — {reason} — keeping existing DynamoDB value")
                    skip_reasons.append(f"gold: {reason}")
                    records_skipped += 1
                    continue

                # ── Guard 2: 22K per-gram sanity floor ──────────────────────
                if metal == "gold":
                    city_rates_raw = metal_data.get("city_rates", {})
                    INTL = {"united-states", "united-kingdom", "dubai"}
                    indian = {k: v for k, v in city_rates_raw.items() if k not in INTL}
                    rates_22k = [
                        v.get("22K") for v in indian.values()
                        if isinstance(v, dict) and v.get("22K")
                    ]
                    if rates_22k:
                        avg_per_gram = sum(rates_22k) / len(rates_22k) / 10
                        if avg_per_gram < MIN_GOLD_22K_PER_GRAM:
                            reason = (
                                f"22K city avg ₹{avg_per_gram:.0f}/gram below floor "
                                f"₹{MIN_GOLD_22K_PER_GRAM} — sources: {sources_used}"
                            )
                            logger.warning(f"[GOLD] SKIPPED — {reason} — keeping existing DynamoDB value")
                            skip_reasons.append(f"gold: {reason}")
                            records_skipped += 1
                            continue

                self._write_metal_record(
                    metal=metal,
                    metal_data=metal_data,
                    snapshot_id=snapshot.get("snapshot_id"),
                    inr_rate=snapshot.get("inr_rate"),
                    usd_to_inr=snapshot.get("usd_to_inr")
                )
                records_written += 1

            except Exception as e:
                logger.error(f"[{metal.upper()}] write failed — {str(e)}", exc_info=True)
                continue

        logger.info(
            f"DynamoWriter complete — "
            f"written: {records_written} — "
            f"skipped: {records_skipped} — "
            f"table: {self.table_name}"
        )
        if skip_reasons:
            logger.warning(
                f"DynamoWriter skip summary — {skip_reasons}"
            )

        return self._build_result(
            status="success",
            records_written=records_written,
            reason=None
        )

    # ============================================================
    # Write a single metal record
    # ============================================================
    def _write_metal_record(
        self,
        metal:       str,
        metal_data:  dict,
        snapshot_id: str,
        inr_rate:    float,
        usd_to_inr:  float
    ) -> None:
        """
        Writes a single metal record to DynamoDB.

        Uses put_item — always overwrites previous record for this metal.

        Args:
            metal:       Metal id (partition key)
            metal_data:  Metal consensus data from merger
            snapshot_id: Snapshot timestamp id
            inr_rate:    INR exchange rate
            usd_to_inr:  USD to INR conversion rate
        """

        # Derive 22K/24K per-gram prices from RapidAPI city averages (Indian market rate)
        city_rates = metal_data.get("city_rates", {})
        INTERNATIONAL = {"united-states", "united-kingdom", "dubai"}
        price_22k_inr = None
        price_24k_inr = None
        price_18k_inr = None
        if metal == "gold" and city_rates:
            indian_rates = {loc: v for loc, v in city_rates.items() if loc not in INTERNATIONAL}
            prices_22k = [v.get("22K") for v in indian_rates.values() if isinstance(v, dict) and v.get("22K")]
            prices_24k = [v.get("24K") for v in indian_rates.values() if isinstance(v, dict) and v.get("24K")]
            if prices_22k:
                price_22k_inr = str(round(sum(prices_22k) / len(prices_22k) / 10, 2))
                price_18k_inr = str(round(float(price_22k_inr) * 18 / 22, 2))
            if prices_24k:
                price_24k_inr = str(round(sum(prices_24k) / len(prices_24k) / 10, 2))

        # Flatten city_rates to {city: "22K_price_per_10g"} — strings, no floats in DynamoDB
        city_rates_simple = {
            loc: str(rates.get("22K"))
            for loc, rates in city_rates.items()
            if isinstance(rates, dict) and rates.get("22K")
            and loc not in ("united-states", "united-kingdom", "dubai")  # INR cities only
        } if city_rates else {}

        item = {
            "metal":          metal,
            "price_usd":      str(metal_data.get("price_usd") or ""),
            "price_inr":      str(metal_data.get("price_inr") or ""),
            "price_18k_inr":  price_18k_inr or "",
            "price_22k_inr":  price_22k_inr or "",
            "price_24k_inr":  price_24k_inr or "",
            "city_rates":     city_rates_simple,
            "unit":           metal_data.get("unit", "troy_ounce"),
            "confidence":     metal_data.get("confidence", "unknown"),
            "sources_used":   metal_data.get("sources_used", []),
            "sources_count":  metal_data.get("sources_count", 0),
            "spread_percent": str(metal_data.get("spread_percent") or ""),
            "spread_flagged": metal_data.get("spread_flagged", False),
            "snapshot_id":    snapshot_id or "",
            "inr_rate":       str(inr_rate or ""),
            "usd_to_inr":     str(usd_to_inr or ""),
            "updated_at":     datetime.now(timezone.utc).isoformat()
        }

        logger.info(
            f"[{metal.upper()}] Writing to DynamoDB — "
            f"price_usd: ${metal_data.get('price_usd')} — "
            f"price_22k_inr: ₹{price_22k_inr}/gram — "
            f"price_24k_inr: ₹{price_24k_inr}/gram — "
            f"city_rates_count: {len(city_rates_simple)} — "
            f"sources: {metal_data.get('sources_used')}"
        )

        self.table.put_item(Item=item)

        logger.info(
            f"[{metal.upper()}] WRITTEN OK — "
            f"snapshot_id: {snapshot_id} — "
            f"22K: ₹{price_22k_inr}/gram — "
            f"24K: ₹{price_24k_inr}/gram — "
            f"USD: ${metal_data.get('price_usd')} — "
            f"confidence: {metal_data.get('confidence')}"
        )

    # ============================================================
    # Build standard result dict
    # ============================================================
    def _build_result(
        self,
        status:          str,
        records_written: int,
        reason:          str
    ) -> dict:
        """
        Builds standard result dict.

        Args:
            status:          "success" / "skipped" / "failed"
            records_written: Number of records written
            reason:          Reason if skipped or failed

        Returns:
            Standard result dict
        """
        return {
            "status":          status,
            "table":           self.table_name,
            "records_written": records_written,
            "reason":          reason,
            "written_at":      datetime.now(timezone.utc).isoformat()
        }
