"""
consolidator.py

Main orchestrator for the Gold Agent data pipeline.

This is the heart of Phase 1 — it runs all scrapers,
validates results, merges prices into a consensus snapshot,
and writes to DynamoDB and S3.

Pipeline:
    1. Load sources.json — find all enabled sources
    2. Initialise scrapers for enabled sources only
    3. Run all scrapers
    4. Extract INR rate from MetalsDevScraper instance
    5. Validate all scraper results via Validator
    6. Merge valid results via Merger
    7. Build final snapshot with snapshot_id + timestamp
    8. Write to DynamoDB via DynamoWriter
    9. Write to S3 via S3Writer
    10. Return full consolidation result

Config-driven:
    Sources are loaded from config/sources.json.
    Disabling a source in sources.json automatically
    skips it here — no code changes needed.

Standalone usage (local testing):
    python src/lambdas/consolidator/consolidator.py

Lambda usage:
    handler.py calls Consolidator().run() directly.

Usage:
    consolidator = Consolidator()
    result = consolidator.run()
"""

from dotenv import load_dotenv
load_dotenv()

import json
import os
import logging
from datetime import datetime, timezone
from src.shared.utils.config_loader import load_json

from src.lambdas.consolidator.validator     import Validator
from src.lambdas.consolidator.merger        import Merger
from src.lambdas.consolidator.dynamo_writer import DynamoWriter
from src.lambdas.consolidator.s3_writer     import S3Writer

logger = logging.getLogger(__name__)

from src.scrapers.engine.secrets_manager import SecretsManager

# Map source id → scraper class
# Add new scrapers here as they are built
SCRAPER_REGISTRY = {
    "gold_api_com": "src.scrapers.sites.gold_api_com.GoldApiComScraper",
    "metals_dev":   "src.scrapers.sites.metals_dev.MetalsDevScraper",
    "goldapi_io":   "src.scrapers.sites.goldapi_io.GoldApiIoScraper",
    "goodreturns":  "src.scrapers.sites.goodreturns.GoodReturnsScraper",
}


class Consolidator:
    """
    Orchestrates the full Gold Agent data pipeline.

    Loads sources from config, runs scrapers, validates,
    merges, and writes the final snapshot.
    """

    def __init__(self):
        """
        Initialises the consolidator.

        Loads sources config and initialises all components.
        """
        self.sources_config = self._load_sources_config()
        self.validator      = Validator()
        self.merger         = Merger()
        self.dynamo_writer  = DynamoWriter()
        self.s3_writer      = S3Writer()

        logger.info(
            f"Consolidator initialised — "
            f"{len(self.sources_config)} sources in config"
        )

    # ============================================================
    # Main entry point
    # ============================================================
    def run(self) -> dict:
        """
        Runs the full consolidation pipeline.

        Returns:
            Dict with full pipeline result including snapshot,
            scraper results, and writer results.
        """

        # Load secrets from AWS Secrets Manager (lazy load)
        # Cached for Lambda container lifetime — only fetches once
        # Skipped if .env keys are already in os.environ (local testing)
        SecretsManager.load()

        started_at = datetime.now(timezone.utc)
        logger.info("Consolidator pipeline starting")

        # --------------------------------------------------------
        # Step 1 — initialise scrapers for enabled sources
        # --------------------------------------------------------
        scrapers = self._initialise_scrapers()

        if not scrapers:
            logger.error("No scrapers initialised — aborting")
            return self._build_result(
                status="failed",
                snapshot=None,
                scraper_results=[],
                error="No scrapers could be initialised",
                started_at=started_at
            )

        # --------------------------------------------------------
        # Step 2 — run all scrapers
        # --------------------------------------------------------
        scraper_results, inr_rate = self._run_scrapers(scrapers)

        # --------------------------------------------------------
        # Step 3 — validate scraper results
        # --------------------------------------------------------
        valid_results = self.validator.filter_valid(scraper_results)

        if not valid_results:
            logger.error("No valid scraper results — aborting")
            return self._build_result(
                status="failed",
                snapshot=None,
                scraper_results=scraper_results,
                error="No valid scraper results after validation",
                started_at=started_at
            )

        # --------------------------------------------------------
        # Step 4 — merge into consensus snapshot
        # --------------------------------------------------------
        merged = self.merger.merge(valid_results, inr_rate=inr_rate)

        # --------------------------------------------------------
        # Step 5 — build final snapshot
        # --------------------------------------------------------
        snapshot = self._build_snapshot(merged, started_at)

        # --------------------------------------------------------
        # Step 6 — write to DynamoDB
        # --------------------------------------------------------
        dynamo_result = self.dynamo_writer.write(snapshot)

        # --------------------------------------------------------
        # Step 7 — write to S3
        # --------------------------------------------------------
        s3_result = self.s3_writer.write(snapshot)

        # --------------------------------------------------------
        # Done
        # --------------------------------------------------------
        completed_at = datetime.now(timezone.utc)
        duration     = round(
            (completed_at - started_at).total_seconds(), 2
        )

        logger.info(
            f"Consolidator pipeline complete — "
            f"{len(merged['metals'])} metals — "
            f"{duration}s"
        )

        return self._build_result(
            status="success",
            snapshot=snapshot,
            scraper_results=scraper_results,
            error=None,
            started_at=started_at,
            completed_at=completed_at,
            duration=duration,
            dynamo_result=dynamo_result,
            s3_result=s3_result
        )

    # ============================================================
    # Initialise scrapers for all enabled sources
    # ============================================================
    def _initialise_scrapers(self) -> dict:
        """
        Initialises scraper instances for all enabled sources
        that have a registered scraper class.

        Returns:
            Dict of source_id → scraper instance
            Only includes sources that are enabled AND registered
        """

        scrapers = {}

        for source_config in self.sources_config:
            source_id = source_config.get("id")

            # Skip disabled sources
            if not source_config.get("enabled", False):
                logger.info(f"[{source_id}] Disabled in sources.json — skipping")
                continue

            # Skip sources with no registered scraper
            if source_id not in SCRAPER_REGISTRY:
                logger.info(
                    f"[{source_id}] No scraper registered — skipping"
                )
                continue

            # Dynamically import and initialise scraper class
            try:
                scraper_class = self._import_scraper(source_id)
                scrapers[source_id] = scraper_class(source_config)

                logger.info(
                    f"[{source_id}] Scraper initialised"
                )

            except Exception as e:
                # One scraper failing does not stop others
                logger.error(
                    f"[{source_id}] Failed to initialise scraper — {str(e)}"
                )
                continue

        logger.info(
            f"Scrapers initialised: {list(scrapers.keys())}"
        )

        return scrapers

    # ============================================================
    # Run all scrapers and extract INR rate
    # ============================================================
    def _run_scrapers(self, scrapers: dict) -> tuple:
        """
        Runs all scrapers and collects results.

        Also extracts the INR rate from MetalsDevScraper
        after it runs — this is our single source of truth
        for USD to INR conversion.

        Args:
            scrapers: Dict of source_id → scraper instance

        Returns:
            Tuple of (scraper_results list, inr_rate float or None)
        """

        scraper_results = []
        inr_rate        = None

        for source_id, scraper in scrapers.items():
            try:
                logger.info(f"[{source_id}] Running scraper")
                result = scraper.run()
                scraper_results.append(result)

                # Extract INR rate from MetalsDevScraper
                # This is the only source we trust for exchange rates
                if source_id == "metals_dev" and result["status"] == "success":
                    inr_rate = getattr(scraper, "inr_rate", None)
                    if inr_rate:
                        logger.info(
                            f"INR rate extracted from metals_dev: "
                            f"{inr_rate} — "
                            f"1 USD = ₹{round(1 / inr_rate, 2)}"
                        )
                    else:
                        logger.warning(
                            "metals_dev ran successfully but inr_rate is None"
                        )

            except Exception as e:
                # One scraper crashing does not stop others
                logger.error(
                    f"[{source_id}] Scraper crashed — {str(e)}"
                )
                scraper_results.append({
                    "source_id":        source_id,
                    "source_name":      source_id,
                    "status":           "failed",
                    "data":             [],
                    "error":            str(e),
                    "duration_seconds": 0,
                    "scraped_at":       datetime.now(timezone.utc).isoformat(),
                    "records_count":    0
                })
                continue

        logger.info(
            f"All scrapers complete — "
            f"{len(scraper_results)} results — "
            f"INR rate: {inr_rate}"
        )

        return scraper_results, inr_rate

    # ============================================================
    # Build final snapshot
    # ============================================================
    def _build_snapshot(self, merged: dict, started_at: datetime) -> dict:
        """
        Builds the final snapshot dict from merged metal data.

        Adds snapshot_id (ISO timestamp) and consolidated_at.

        Args:
            merged:     Merged metals dict from Merger.merge()
            started_at: Pipeline start datetime

        Returns:
            Full snapshot dict ready for DynamoDB and S3
        """

        snapshot_id = started_at.isoformat()

        snapshot = {
            "snapshot_id":     snapshot_id,
            "consolidated_at": datetime.now(timezone.utc).isoformat(),
            "inr_rate":        merged.get("inr_rate"),
            "usd_to_inr":      merged.get("usd_to_inr"),
            "metals":          merged.get("metals", {})
        }

        logger.info(
            f"Snapshot built — "
            f"id: {snapshot_id} — "
            f"metals: {list(snapshot['metals'].keys())}"
        )

        return snapshot

    # ============================================================
    # Dynamically import scraper class from registry
    # ============================================================
    def _import_scraper(self, source_id: str):
        """
        Dynamically imports a scraper class from the registry.

        Args:
            source_id: Source id from sources.json

        Returns:
            Scraper class (not instance)

        Raises:
            ImportError if class cannot be imported
        """

        module_path = SCRAPER_REGISTRY[source_id]

        # Split into module path and class name
        # e.g. "src.scrapers.sites.gold_api_com.GoldApiComScraper"
        # → module: "src.scrapers.sites.gold_api_com"
        # → class:  "GoldApiComScraper"
        parts      = module_path.rsplit(".", 1)
        module_str = parts[0]
        class_str  = parts[1]

        import importlib
        module = importlib.import_module(module_str)
        return getattr(module, class_str)

    # ============================================================
    # Load sources config from sources.json
    # ============================================================
    def _load_sources_config(self) -> list:
        """
        Loads sources.json and returns the sources list.

        Returns:
            List of source config dicts
            Empty list if file cannot be loaded
        """

        try:
            # config_path = os.path.join(
            #     os.path.dirname(__file__),
            #     "..", "..", "..", "config", "sources.json"
            # )
            # config_path = os.path.abspath(config_path)

            # with open(config_path, "r") as f:
            #     data = json.load(f)

            data = load_json("sources.json")

            sources = data.get("sources", [])

            logger.info(
                f"Sources config loaded — "
                f"{len(sources)} sources found"
            )

            return sources

        except Exception as e:
            logger.error(
                f"Failed to load sources config — {str(e)}"
            )
            return []

    # ============================================================
    # Build standard pipeline result
    # ============================================================
    def _build_result(
        self,
        status:          str,
        snapshot:        dict,
        scraper_results: list,
        error:           str        = None,
        started_at:      datetime   = None,
        completed_at:    datetime   = None,
        duration:        float      = 0,
        dynamo_result:   dict       = None,
        s3_result:       dict       = None
    ) -> dict:
        """
        Builds the standard pipeline result dict.

        Args:
            status:          "success" or "failed"
            snapshot:        Final snapshot dict or None
            scraper_results: List of all scraper results
            error:           Error message if failed
            started_at:      Pipeline start datetime
            completed_at:    Pipeline end datetime
            duration:        Total duration in seconds
            dynamo_result:   DynamoWriter result dict
            s3_result:       S3Writer result dict

        Returns:
            Standard pipeline result dict
        """

        metals_count = len(snapshot.get("metals", {})) if snapshot else 0

        return {
            "status":          status,
            "error":           error,
            "snapshot":        snapshot,
            "metals_count":    metals_count,
            "scraper_results": scraper_results,
            "dynamo_result":   dynamo_result,
            "s3_result":       s3_result,
            "started_at":      started_at.isoformat() if started_at else None,
            "completed_at":    completed_at.isoformat() if completed_at else None,
            "duration_seconds": duration
        }


# ============================================================
# Standalone entry point — run locally for testing
# ============================================================
if __name__ == "__main__":
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s — %(name)s — %(levelname)s — %(message)s"
    )

    print("\n" + "="*55)
    print("  Running Consolidator locally")
    print("="*55 + "\n")

    consolidator = Consolidator()
    result       = consolidator.run()

    print("\n" + "="*55)
    print(f"  Status: {result['status']}")
    print(f"  Metals: {result['metals_count']}")
    print(f"  Duration: {result['duration_seconds']}s")
    print("="*55 + "\n")

    print(json.dumps(result, indent=2, default=str))