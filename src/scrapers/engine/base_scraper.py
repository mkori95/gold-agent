"""
base_scraper.py

The base class for every scraper in the Gold Agent system.
All individual scrapers (goldapi_io, metals_dev, goodreturns etc)
inherit from this class.

This class handles:
- Standard logging
- Standard error handling
- Standard result format
- Success and failure recording
"""

import time
import logging
from datetime import datetime, timezone
from abc import ABC, abstractmethod
import json
import os
from src.shared.utils.config_loader import load_json



# ============================================================
# Set up logging — every scraper uses this same logger
# ============================================================
logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.

    ABC means Abstract Base Class — it means this class
    cannot be used directly. It must be inherited by a
    child class (like GoldApiComScraper).

    Any class that inherits from BaseScraper MUST implement
    the fetch() method — otherwise Python will raise an error.
    """

    def __init__(self, source_config: dict):
        """
        Called when a scraper is created.

        Args:
            source_config: The full config block for this source
                           from sources.json — passed in by the
                           scraper Lambda handler.
        """
        self.source_id = source_config["id"]
        self.source_name = source_config["name"]
        self.base_url = source_config["url"]
        self.enabled = source_config["enabled"]
        self.metals = source_config["metals"]
        self.fields_map = source_config["fields_map"]
        self.failure_handling = source_config["failure_handling"]
        # Load metals config for price validation ranges
        self.metals_config = self._load_metals_config()

        # Track how long this scrape takes
        self.start_time = None
        self.end_time = None

    # ============================================================
    # Every child class MUST implement this method
    # ============================================================
    @abstractmethod
    def fetch(self) -> list:
        """
        Fetch price data from the source.

        Every scraper implements this differently —
        GoldAPI.com calls a REST API,
        GoodReturns.in scrapes HTML.

        But they ALL must return data in the same
        standard format — a list of price records.

        Returns:
            List of price records in standard format.
            See build_price_record() below for the format.
        """
        pass

    # ============================================================
    # Run the scraper safely — catches all errors
    # ============================================================
    def run(self) -> dict:
        """
        Safely runs the scraper and returns a result object.

        This is what the Lambda handler calls — not fetch() directly.
        It wraps fetch() in error handling so one scraper failing
        never crashes the whole system.

        Returns:
            A result dict with status, data, and metadata.
        """

        # Check if this source is enabled before doing anything
        if not self.enabled:
            logger.info(f"[{self.source_id}] Source is disabled — skipping")
            return self.build_result(
                status="skipped",
                data=[],
                error=None
            )

        # Record start time
        self.start_time = time.time()
        logger.info(f"[{self.source_id}] Starting scrape")

        try:
            # Call the child class fetch() method
            data = self.fetch()

            # Record end time
            self.end_time = time.time()
            duration = round(self.end_time - self.start_time, 2)

            logger.info(
                f"[{self.source_id}] Scrape successful — "
                f"{len(data)} records — {duration}s"
            )

            return self.build_result(
                status="success",
                data=data,
                error=None,
                duration=duration
            )

        except Exception as e:
            # Record end time even on failure
            self.end_time = time.time()
            duration = round(self.end_time - self.start_time, 2)

            logger.error(
                f"[{self.source_id}] Scrape failed — "
                f"{str(e)} — {duration}s"
            )

            return self.build_result(
                status="failed",
                data=[],
                error=str(e),
                duration=duration
            )

    # ============================================================
    # Standard result format — same structure for every scraper
    # ============================================================
    def build_result(
        self,
        status: str,
        data: list,
        error: str = None,
        duration: float = 0
    ) -> dict:
        """
        Builds a standard result object.

        Every scraper returns this exact same structure —
        this makes the consolidator's job simple because
        it always knows what to expect.

        Args:
            status:   "success", "failed", or "skipped"
            data:     List of price records (empty if failed)
            error:    Error message if failed, None if success
            duration: How long the scrape took in seconds

        Returns:
            Standard result dict
        """
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "status": status,
            "data": data,
            "error": error,
            "duration_seconds": duration,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "records_count": len(data)
        }

    # ============================================================
    # Standard price record format — same for every metal
    # ============================================================
    def build_price_record(
        self,
        metal: str,
        price_usd: float,
        currency: str = "USD",
        price_inr: float = None,
        unit: str = "troy_ounce",
        extra: dict = None
    ) -> dict:
        """
        Builds a standard price record.

        This is the standard format for a single metal price.
        The consolidator expects every scraper to return
        price records in exactly this format.

        Args:
            metal:     Metal id — "gold", "silver", "platinum", "copper"
            price_usd: Price in USD
            currency:  Currency code — default USD
            price_inr: Price in INR if available — optional
            unit:      Unit of measurement — default troy_ounce
            extra:     Any extra fields specific to this source
                       e.g. karat prices from GoldAPI.io

        Returns:
            Standard price record dict
        """
        record = {
            "metal": metal,
            "price_usd": price_usd,
            "currency": currency,
            "price_inr": price_inr,
            "unit": unit,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Add any extra fields if provided
        if extra:
            record["extra"] = extra

        return record
    
    
    # ============================================================
    # Load metals config from config/metals.json
    # ============================================================
    def _load_metals_config(self) -> dict:
        """
        Loads metals.json config file and returns a dict
        keyed by metal id for easy lookup.

        Returns:
            Dict of metal configs keyed by metal id
            e.g. {"gold": {...}, "silver": {...}}
        """
        try:
            # Find the config file relative to project root
            # config_path = os.path.join(
            #     os.path.dirname(__file__),
            #     "..", "..", "..", "config", "metals.json"
            # )
            # config_path = os.path.abspath(config_path)

            # with open(config_path, "r") as f:
            #     data = json.load(f)
            
            data = load_json("metals.json")

            # Convert list to dict keyed by metal id
            # Makes lookups like metals_config["gold"] easy
            return {
                metal["id"]: metal
                for metal in data["metals"]
            }

        except Exception as e:
            logger.warning(
                f"[{self.source_id}] Could not load metals config — "
                f"price validation disabled — {str(e)}"
            )
            return {}
    
    # ============================================================
    # Helper — validate that a price makes sense
    # ============================================================
    def is_valid_price(self, price: float, metal: str) -> bool:
        """
        Basic sanity check on a price before we accept it.

        Catches obviously wrong values — like a gold price
        of $0 or $999,999 — before they enter our system.

        Price ranges are loaded from config/metals.json —
        not hardcoded here.

        Args:
            price: The price to validate
            metal: The metal this price is for

        Returns:
            True if price looks valid, False if suspicious
        """

        # Price must be a positive number
        if not isinstance(price, (int, float)):
            return False
        if price <= 0:
            return False

        # If metals config not loaded — skip range check
        if not self.metals_config:
            logger.warning(
                f"[{self.source_id}] Metals config not loaded — "
                f"skipping range validation for {metal}"
            )
            return True

        # Metal not found in config — let it through with warning
        if metal not in self.metals_config:
            logger.warning(
                f"[{self.source_id}] Unknown metal '{metal}' — "
                f"skipping price validation"
            )
            return True

        # Get price range from config
        metal_config = self.metals_config[metal]

        # If no price range defined in config — skip check
        if "price_range_usd" not in metal_config:
            logger.warning(
                f"[{self.source_id}] No price range defined for "
                f"{metal} in metals.json — skipping validation"
            )
            return True

        price_range = metal_config["price_range_usd"]
        min_price = price_range["min"]
        max_price = price_range["max"]

        if price < min_price or price > max_price:
            logger.warning(
                f"[{self.source_id}] Suspicious price for {metal}: "
                f"${price} — outside expected range "
                f"${min_price}-${max_price} from config"
            )
            return False

        return True
  