"""
s3_writer.py

Writes consolidated price snapshot to S3 as JSON.

S3 path pattern:
    prices/YYYY/MM/DD/HH:MM.json
    e.g. prices/2026/03/01/14:00.json

Also writes a latest.json for quick access:
    prices/latest.json

Bucket name is read from S3_BUCKET_NAME env var,
defaulting to "gold-agent-prices".

Usage:
    writer = S3Writer()
    result = writer.write(snapshot)
"""

import json
import os
import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

S3_BUCKET  = os.environ.get("S3_BUCKET_NAME") or "gold-agent-prices"
S3_PREFIX  = "prices"
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")


class S3Writer:
    """
    Writes consolidated snapshot to S3 as JSON.

    Writes two files per run:
    1. Timestamped path — permanent historical record
    2. prices/latest.json — always overwritten with most recent
    """

    def __init__(self):
        """
        Initialises S3Writer with boto3 S3 client.
        """
        self.bucket = S3_BUCKET

        try:
            self.s3 = boto3.client("s3", region_name=AWS_REGION)
            logger.info(
                f"S3Writer initialised — bucket: {self.bucket}"
            )
        except Exception as e:
            self.s3 = None
            logger.error(
                f"S3Writer: boto3 init failed — {str(e)}"
            )

    # ============================================================
    # Write full snapshot to S3
    # ============================================================
    def write(self, snapshot: dict) -> dict:
        """
        Writes consolidated snapshot to S3.

        Writes two files:
        1. Timestamped path — permanent historical record
        2. latest.json — always overwritten with most recent

        Args:
            snapshot: Full consolidated snapshot dict from consolidator

        Returns:
            Dict with status, paths written, and metadata
        """

        if not snapshot:
            logger.warning("S3Writer received empty snapshot — nothing to write")
            return self._build_result(
                status="skipped",
                paths_written=[],
                reason="empty snapshot"
            )

        if not self.s3:
            logger.error("S3Writer: client not initialised — skipping write")
            return self._build_result(
                status="failed",
                paths_written=[],
                reason="S3 client not initialised"
            )

        snapshot_id      = snapshot.get("snapshot_id", datetime.now(timezone.utc).isoformat())
        timestamped_path = self._build_s3_path(snapshot_id)
        latest_path      = f"{S3_PREFIX}/latest.json"

        try:
            snapshot_json = json.dumps(snapshot, indent=2, default=str)
        except Exception as e:
            logger.error(f"S3Writer failed to serialise snapshot — {str(e)}")
            return self._build_result(
                status="failed",
                paths_written=[],
                reason=f"JSON serialisation failed: {str(e)}"
            )

        paths_written = []

        # Write timestamped file
        try:
            self._write_to_s3(timestamped_path, snapshot_json)
            paths_written.append(timestamped_path)
        except Exception as e:
            logger.error(
                f"S3Writer failed to write timestamped file — {str(e)}"
            )

        # Write latest.json
        try:
            self._write_to_s3(latest_path, snapshot_json)
            paths_written.append(latest_path)
        except Exception as e:
            logger.error(
                f"S3Writer failed to write latest.json — {str(e)}"
            )

        logger.info(
            f"S3Writer complete — "
            f"{len(paths_written)} files written to s3://{self.bucket}"
        )

        return self._build_result(
            status="success",
            paths_written=paths_written,
            reason=None
        )

    # ============================================================
    # Write a single file to S3
    # ============================================================
    def _write_to_s3(self, path: str, content: str) -> None:
        """
        Writes content to a single S3 path.

        Args:
            path:    S3 key path
            content: JSON string to write
        """

        self.s3.put_object(
            Bucket=self.bucket,
            Key=path,
            Body=content.encode("utf-8"),
            ContentType="application/json"
        )

        logger.info(
            f"S3Writer wrote — "
            f"s3://{self.bucket}/{path} — "
            f"{len(content)} bytes"
        )

    # ============================================================
    # Build S3 path from snapshot timestamp
    # ============================================================
    def _build_s3_path(self, snapshot_id: str) -> str:
        """
        Builds the S3 path for a snapshot.

        Pattern: prices/YYYY/MM/DD/HH:MM.json

        Args:
            snapshot_id: ISO 8601 timestamp string

        Returns:
            S3 key path string
        """

        try:
            dt = datetime.fromisoformat(
                snapshot_id.replace("Z", "+00:00")
            )
            return (
                f"{S3_PREFIX}/"
                f"{dt.year:04d}/"
                f"{dt.month:02d}/"
                f"{dt.day:02d}/"
                f"{dt.hour:02d}:{dt.minute:02d}.json"
            )

        except Exception:
            safe_id = snapshot_id.replace(":", "-").replace("+", "-")
            return f"{S3_PREFIX}/{safe_id}.json"

    # ============================================================
    # Build standard result dict
    # ============================================================
    def _build_result(
        self,
        status:        str,
        paths_written: list,
        reason:        str
    ) -> dict:
        """
        Builds standard result dict.

        Args:
            status:        "success" / "skipped" / "failed"
            paths_written: List of S3 paths written
            reason:        Reason if skipped or failed

        Returns:
            Standard result dict
        """
        return {
            "status":        status,
            "bucket":        self.bucket,
            "paths_written": paths_written,
            "files_count":   len(paths_written),
            "reason":        reason,
            "written_at":    datetime.now(timezone.utc).isoformat()
        }
