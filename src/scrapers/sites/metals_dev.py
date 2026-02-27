"""
metals_dev.py

Scraper for Metals.Dev — our most valuable data source.

What this source gives us in a single API call:
- Gold, Silver, Platinum spot prices in USD
- Copper spot price in USD (per pound — we convert to troy ounce)
- MCX gold and silver rates (Indian exchange rates)
- IBJA gold rate (Indian benchmark — used by jewellers)
- INR exchange rate — used by ALL other scrapers for USD→INR conversion
- LBMA official fix prices (London benchmark — stored for Phase 2)

API pattern:
    GET https://api.metals.dev/v1/latest
        ?api_key=YOUR_KEY
        &currency=USD
        &unit=toz

    Auth: query param — api_key=YOUR_KEY
    Limit: 100 requests/month — run twice daily only

Response structure:
    {
        "status": "success",
        "metals": {
            "gold": 5184.78,
            "silver": 88.308,
            "platinum": 2280.5,
            "copper": 0.4132,        ← per pound — must convert
            "mcx_gold": 5464.365,
            "mcx_silver": 88.675,
            "ibja_gold": 5401.8482,
            "lbma_gold_am": 5174.75,
            "lbma_gold_pm": 5167.35,
            ...
        },
        "currencies": {
            "INR": 0.0109905854,     ← 1 INR = X USD (fraction)
            ...
        },
        "timestamps": {
            "metal": "2026-02-26T22:35:07.586Z"
        }
    }

Copper unit note:
    Metals.Dev returns copper per pound not per troy ounce.
    We convert to troy ounce for system consistency.
    Both values are stored — converted at top level, original in extra{}.

    1 troy ounce = 0.0685714 pounds
    copper_per_toz = copper_per_lb / 0.0685714

INR rate note:
    currencies.INR = 0.0109905854 means 1 INR = 0.011 USD
    So 1 USD = 1 / 0.0109905854 = ~91.0 INR
    This rate is stored and used by data_normaliser for all conversions.

Usage:
    Called by the scraper Lambda handler via run()
    Never call fetch() directly — always use run()
"""

from dotenv import load_dotenv
load_dotenv()

import logging
from src.scrapers.engine.base_scraper import BaseScraper
from src.scrapers.engine.api_fetcher import APIFetcher

logger = logging.getLogger(__name__)


class MetalsDevScraper(BaseScraper):
    """
    Scraper for Metals.Dev

    Inherits from BaseScraper:
    - run()                → safely execute the scraper
    - build_result()       → standard result wrapper
    - build_price_record() → standard price record format
    - is_valid_price()     → validates price against metals.json ranges
    - metals_config        → loaded from metals.json automatically

    Must implement:
    - fetch()              → get all prices and return records list

    Special responsibilities:
    - Convert copper from per_pound to per_troy_ounce
    - Extract and store INR exchange rate
    - Capture MCX, IBJA, LBMA prices in extra{}
    """

    # Copper conversion factor
    # 1 troy ounce = 0.0685714 pounds
    # copper_per_toz = copper_per_lb / COPPER_LB_TO_TOZ
    COPPER_LB_TO_TOZ = 0.0685714

    # Metals.Dev field names for each of our metals
    # Maps our internal metal id → field name in API response
    METAL_FIELDS = {
        "gold":     "gold",
        "silver":   "silver",
        "platinum": "platinum",
        "copper":   "copper"
    }

    def __init__(self, source_config: dict):
        """
        Initialises the scraper with source config from sources.json

        Args:
            source_config: The metals_dev block from sources.json
        """
        super().__init__(source_config)

        # Create the API fetcher — handles all HTTP calls and auth
        self.fetcher = APIFetcher(source_config)

        # Store the latest INR rate after each run
        # Consolidator reads this and passes to data_normaliser
        self.inr_rate = None

        logger.info(
            f"[{self.source_id}] Scraper initialised — "
            f"metals: {self.metals}"
        )

    # ============================================================
    # fetch() — required by BaseScraper — must be implemented
    # ============================================================
    def fetch(self) -> list:
        """
        Fetches all prices from Metals.Dev in a single API call.

        One call gives us everything — spot prices, MCX, IBJA,
        INR rate, LBMA prices. We extract what we need and
        store the rest in extra{}.

        Returns:
            List of standard price records — one per metal
            Empty list if the call fails

        Raises:
            Exception if something unexpected happens
            (run() will catch this and return a failed result)
        """

        # Single API call — gets everything
        response = self.fetcher.fetch(
            endpoint="/latest",
            params={
                "currency": "USD",
                "unit":     "toz"
            }
        )

        # Validate top level response status
        if response.get("status") != "success":
            raise Exception(
                f"[{self.source_id}] API returned non-success status — "
                f"{response.get('status')}"
            )

        # Extract the three main sections from response
        metals_data    = response.get("metals", {})
        currencies_data = response.get("currencies", {})
        timestamps_data = response.get("timestamps", {})

        # Get the timestamp for all records
        timestamp = timestamps_data.get("metal")

        # Extract and store INR rate — critical for whole system
        self._extract_inr_rate(currencies_data)

        # Build price records for each metal
        records = []

        for metal in self.metals:
            try:
                record = self._build_metal_record(
                    metal=metal,
                    metals_data=metals_data,
                    timestamp=timestamp
                )

                if record:
                    records.append(record)

            except Exception as e:
                # One metal failing does not stop the others
                logger.error(
                    f"[{self.source_id}] Failed to build record "
                    f"for {metal} — {str(e)}"
                )
                continue

        logger.info(
            f"[{self.source_id}] Fetch complete — "
            f"{len(records)}/{len(self.metals)} metals successful — "
            f"INR rate: {self.inr_rate}"
        )

        return records

    # ============================================================
    # Build a price record for a single metal
    # ============================================================
    def _build_metal_record(
        self,
        metal: str,
        metals_data: dict,
        timestamp: str
    ) -> dict:
        """
        Builds a standard price record for one metal.

        Handles copper unit conversion separately.
        Captures MCX, IBJA, LBMA in extra{} for gold and silver.

        Args:
            metal:       Metal id — "gold", "silver" etc
            metals_data: The metals{} block from API response
            timestamp:   Timestamp string from API response

        Returns:
            Standard price record dict
            None if metal not found or price invalid
        """

        # Get the field name for this metal in the API response
        field_name = self.METAL_FIELDS.get(metal)

        if not field_name:
            logger.warning(
                f"[{self.source_id}] No field mapping for {metal} — "
                f"skipping"
            )
            return None

        # Get raw price from response
        raw_price = metals_data.get(field_name)

        if raw_price is None:
            logger.error(
                f"[{self.source_id}] No price found for {metal} "
                f"(field: {field_name}) — skipping"
            )
            return None

        # --------------------------------------------------------
        # Copper — special handling for unit conversion
        # --------------------------------------------------------
        if metal == "copper":
            return self._build_copper_record(
                price_per_lb=raw_price,
                metals_data=metals_data,
                timestamp=timestamp
            )

        # --------------------------------------------------------
        # All other metals — standard handling
        # --------------------------------------------------------

        # Validate price is within expected range
        if not self.is_valid_price(raw_price, metal):
            logger.error(
                f"[{self.source_id}] Price validation failed for "
                f"{metal}: ${raw_price} — skipping"
            )
            return None

        # Build extra fields — different per metal
        extra = self._build_extra_fields(metal, metals_data, timestamp)

        # Build and return standard record
        record = self.build_price_record(
            metal=metal,
            price_usd=raw_price,
            extra=extra
        )

        logger.info(
            f"[{self.source_id}] {metal.upper()} fetched — "
            f"${raw_price}"
        )

        return record

    # ============================================================
    # Build copper record — with unit conversion
    # ============================================================
    def _build_copper_record(
        self,
        price_per_lb: float,
        metals_data: dict,
        timestamp: str
    ) -> dict:
        """
        Builds copper price record with unit conversion.

        Converts from per_pound to per_troy_ounce for consistency.
        Stores both values — converted at top level, original in extra{}.

        Args:
            price_per_lb: Raw copper price per pound from API
            metals_data:  Full metals{} block for extra fields
            timestamp:    Timestamp from API

        Returns:
            Standard price record with both price versions
        """

        # Convert to troy ounce — system standard unit
        price_per_toz = round(price_per_lb / self.COPPER_LB_TO_TOZ, 6)

        # Validate converted price
        if not self.is_valid_price(price_per_toz, "copper"):
            logger.error(
                f"[{self.source_id}] Copper price validation failed — "
                f"per_lb: ${price_per_lb} — "
                f"per_toz: ${price_per_toz} — skipping"
            )
            return None

        # Build record — top level uses converted troy ounce price
        record = self.build_price_record(
            metal="copper",
            price_usd=price_per_toz,
            extra={
                "price_per_toz":      price_per_toz,
                "price_per_pound":    price_per_lb,
                "unit_original":      "per_pound",
                "conversion_factor":  self.COPPER_LB_TO_TOZ,
                "source_timestamp":   timestamp
            }
        )

        logger.info(
            f"[{self.source_id}] COPPER fetched — "
            f"${price_per_lb}/lb → ${price_per_toz}/toz"
        )

        return record

    # ============================================================
    # Build extra fields — MCX, IBJA, LBMA per metal
    # ============================================================
    def _build_extra_fields(
        self,
        metal: str,
        metals_data: dict,
        timestamp: str
    ) -> dict:
        """
        Builds extra{} fields for each metal.

        Gold gets MCX, IBJA, LBMA prices.
        Silver gets MCX, LBMA prices.
        Platinum gets LBMA prices.
        Others get just the timestamp.

        Args:
            metal:       Metal id
            metals_data: Full metals{} block from API response
            timestamp:   Timestamp from API

        Returns:
            Dict of extra fields
        """

        extra = {
            "source_timestamp": timestamp
        }

        if metal == "gold":
            extra.update({
                "mcx_gold":       metals_data.get("mcx_gold"),
                "mcx_gold_am":    metals_data.get("mcx_gold_am"),
                "mcx_gold_pm":    metals_data.get("mcx_gold_pm"),
                "ibja_gold":      metals_data.get("ibja_gold"),
                "lbma_gold_am":   metals_data.get("lbma_gold_am"),
                "lbma_gold_pm":   metals_data.get("lbma_gold_pm")
            })

        elif metal == "silver":
            extra.update({
                "mcx_silver":     metals_data.get("mcx_silver"),
                "mcx_silver_am":  metals_data.get("mcx_silver_am"),
                "mcx_silver_pm":  metals_data.get("mcx_silver_pm"),
                "lbma_silver":    metals_data.get("lbma_silver")
            })

        elif metal == "platinum":
            extra.update({
                "lbma_platinum_am": metals_data.get("lbma_platinum_am"),
                "lbma_platinum_pm": metals_data.get("lbma_platinum_pm")
            })

        return extra

    # ============================================================
    # Extract and store INR rate
    # ============================================================
    def _extract_inr_rate(self, currencies_data: dict) -> None:
        """
        Extracts the INR exchange rate from the currencies block.

        The rate is stored on self.inr_rate so the consolidator
        can pick it up and pass it to data_normaliser.

        currencies.INR = 0.0109905854
        This means 1 INR = 0.011 USD
        So 1 USD = 1 / 0.011 = ~91.0 INR

        Args:
            currencies_data: The currencies{} block from API response
        """

        inr_rate = currencies_data.get("INR")

        if inr_rate is None:
            logger.warning(
                f"[{self.source_id}] INR rate not found in response — "
                f"USD→INR conversion will not be available"
            )
            return

        self.inr_rate = inr_rate

        usd_to_inr = round(1 / inr_rate, 2)

        logger.info(
            f"[{self.source_id}] INR rate extracted — "
            f"1 USD = ₹{usd_to_inr} — "
            f"raw rate: {inr_rate}"
        )