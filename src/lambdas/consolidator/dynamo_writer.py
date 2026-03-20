"""
dynamo_writer.py

Writes consolidated price snapshot to DynamoDB.

Currently a STUB — logs what it would do but makes no
real AWS calls. Real implementation added in Phase 1
deployment when AWS infrastructure is ready.

DynamoDB table: live_prices
Purpose: Stores the latest consensus price per metal so
         the WhatsApp bot can read it with low latency.

Real implementation will:
    - Write one record per metal to live_prices table
    - Use metal id as the partition key
    - Overwrite previous record — always latest price only
    - Include full consensus fields, confidence, sources

Usage:
    writer = DynamoWriter()
    result = writer.write(snapshot)
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# DynamoDB table name — will be read from environment in real implementation
LIVE_PRICES_TABLE = "live_prices"


class DynamoWriter:
    """
    Writes consolidated snapshot to DynamoDB live_prices table.

    STUB — no real AWS calls yet.
    Real implementation added when AWS infrastructure is ready.
    """

    def __init__(self):
        """
        Initialises DynamoWriter.

        Real implementation will initialise boto3 DynamoDB client here:
            import boto3
            self.dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
            self.table    = self.dynamodb.Table(LIVE_PRICES_TABLE)
        """
        self.table_name = LIVE_PRICES_TABLE

        logger.info(
            f"DynamoWriter initialised — "
            f"table: {self.table_name} — "
            f"[STUB — no real AWS connection]"
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

        records_written = 0

        for metal, metal_data in metals.items():
            try:
                self._write_metal_record(
                    metal=metal,
                    metal_data=metal_data,
                    snapshot_id=snapshot.get("snapshot_id"),
                    inr_rate=snapshot.get("inr_rate"),
                    usd_to_inr=snapshot.get("usd_to_inr")
                )
                records_written += 1

            except Exception as e:
                # One metal failing does not stop others
                logger.error(
                    f"DynamoWriter failed to write {metal} — {str(e)}"
                )
                continue

        logger.info(
            f"DynamoWriter complete — "
            f"{records_written}/{len(metals)} metals written — "
            f"[STUB]"
        )

        return self._build_result(
            status="stub",
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

        Real implementation will call:
            self.table.put_item(Item={
                "metal":          metal,
                "price_usd":      metal_data["price_usd"],
                "price_inr":      metal_data["price_inr"],
                "confidence":     metal_data["confidence"],
                "sources_used":   metal_data["sources_used"],
                "sources_count":  metal_data["sources_count"],
                "spread_percent": metal_data["spread_percent"],
                "snapshot_id":    snapshot_id,
                "updated_at":     datetime.now(timezone.utc).isoformat()
            })

        Args:
            metal:       Metal id
            metal_data:  Metal consensus data from merger
            snapshot_id: Snapshot timestamp id
            inr_rate:    INR exchange rate
            usd_to_inr:  USD to INR conversion rate
        """

        # STUB — log what would be written
        logger.info(
            f"[STUB] Would write to DynamoDB table '{self.table_name}' — "
            f"metal: {metal} — "
            f"price_usd: ${metal_data.get('price_usd')} — "
            f"price_inr: ₹{metal_data.get('price_inr')} — "
            f"confidence: {metal_data.get('confidence')} — "
            f"snapshot_id: {snapshot_id}"
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
            status:          "stub" / "success" / "skipped" / "failed"
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