"""
s3_writer.py

Writes consolidated price snapshot to S3 as JSON.

Currently a STUB — logs what it would do but makes no
real AWS calls. Real implementation added in Phase 1
deployment when AWS infrastructure is ready.

S3 path pattern:
    /prices/{metal}/YYYY/MM/DD/HH:MM.json
    e.g. /prices/gold/2026/03/01/14:00.json

Also writes a latest.json for quick access:
    /prices/latest.json

Real implementation will:
    - Serialise snapshot to JSON
    - Write to S3 with timestamped path
    - Write to S3 latest.json (overwrite)
    - Set correct Content-Type header

Usage:
    writer = S3Writer()
    result = writer.write(snapshot)
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# S3 bucket name — will be read from environment in real implementation
S3_BUCKET = "gold-agent-prices"

# S3 path prefix for price snapshots
S3_PREFIX = "prices"


class S3Writer:
    """
    Writes consolidated snapshot to S3 as JSON.

    STUB — no real AWS calls yet.
    Real implementation added when AWS infrastructure is ready.
    """

    def __init__(self):
        """
        Initialises S3Writer.

        Real implementation will initialise boto3 S3 client here:
            import boto3
            self.s3     = boto3.client("s3", region_name="ap-south-1")
            self.bucket = os.environ.get("S3_BUCKET_NAME", S3_BUCKET)
        """
        self.bucket = S3_BUCKET

        logger.info(
            f"S3Writer initialised — "
            f"bucket: {self.bucket} — "
            f"[STUB — no real AWS connection]"
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

        # Build the timestamped S3 path from snapshot_id
        snapshot_id  = snapshot.get("snapshot_id", datetime.now(timezone.utc).isoformat())
        timestamped_path = self._build_s3_path(snapshot_id)
        latest_path      = f"{S3_PREFIX}/latest.json"

        # Serialise snapshot to JSON
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
            f"{len(paths_written)} files written — "
            f"[STUB]"
        )

        return self._build_result(
            status="stub",
            paths_written=paths_written,
            reason=None
        )

    # ============================================================
    # Write a single file to S3
    # ============================================================
    def _write_to_s3(self, path: str, content: str) -> None:
        """
        Writes content to a single S3 path.

        Real implementation will call:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=path,
                Body=content.encode("utf-8"),
                ContentType="application/json"
            )

        Args:
            path:    S3 key path
            content: JSON string to write
        """

        # STUB — log what would be written
        logger.info(
            f"[STUB] Would write to S3 — "
            f"bucket: {self.bucket} — "
            f"path: {path} — "
            f"size: {len(content)} bytes"
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
            # Parse snapshot_id as datetime
            dt = datetime.fromisoformat(
                snapshot_id.replace("Z", "+00:00")
            )
            path = (
                f"{S3_PREFIX}/"
                f"{dt.year:04d}/"
                f"{dt.month:02d}/"
                f"{dt.day:02d}/"
                f"{dt.hour:02d}:{dt.minute:02d}.json"
            )
            return path

        except Exception:
            # Fallback — use raw snapshot_id as filename
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
            status:        "stub" / "success" / "skipped" / "failed"
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