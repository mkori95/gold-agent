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
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

LIVE_PRICES_TABLE = os.environ.get("DYNAMO_LIVE_PRICES_TABLE", "gold-agent-live-prices")
AWS_REGION        = os.environ.get("AWS_REGION", "ap-south-1")


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
            f"{records_written}/{len(metals)} metals written to {self.table_name}"
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

        item = {
            "metal":          metal,
            "price_usd":      str(metal_data.get("price_usd") or ""),
            "price_inr":      str(metal_data.get("price_inr") or ""),
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

        self.table.put_item(Item=item)

        logger.info(
            f"DynamoWriter wrote {metal} — "
            f"price_usd: ${metal_data.get('price_usd')} — "
            f"price_inr: ₹{metal_data.get('price_inr')} — "
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
