"""
goldapi_io.py

Scraper for GoldAPI.io — unique source for karat-wise gram prices.

What this source gives us that no other source does:
- Price per gram for every karat (24K, 22K, 21K, 20K, 18K, 16K, 14K, 10K)
- This is exactly how Indian jewellers quote prices
- ask and bid prices — buying vs selling spread
- Daily price movement — change and change percent

Metals covered: Gold, Silver, Platinum (no copper)
Auth: Header — x-access-token: YOUR_KEY
Limit: 100 requests/month — run twice daily only

API pattern:
    GET https://www.goldapi.io/api/{symbol}/USD
    Header: x-access-token: YOUR_KEY

    Symbols:
        XAU — Gold
        XAG — Silver
        XPT — Platinum

Response structure (same for all 3 metals):
    {
        "timestamp": 1772202528,       ← Unix integer
        "metal": "XAU",
        "currency": "USD",
        "price": 5226.19,              ← spot price per troy ounce
        "ask": 5227.3,
        "bid": 5226.6,
        "ch": 41.41,                   ← change from prev close
        "chp": 0.8,                    ← change percent
        "prev_close_price": 5184.78,
        "open_price": 5184.78,
        "low_price": 5167.105,
        "high_price": 5240.55,
        "price_gram_24k": 168.0259,    ← per gram prices
        "price_gram_22k": 154.0238,
        "price_gram_21k": 147.0227,
        "price_gram_20k": 140.0216,
        "price_gram_18k": 126.0194,
        "price_gram_16k": 112.0173,
        "price_gram_14k": 98.0151,
        "price_gram_10k": 70.0108
    }

Karat handling:
    Standard karats (24K, 22K, 18K) → stored in karats{} at top level
    Extended karats (21K, 20K, 16K, 14K, 10K) → stored in extra{}
    This keeps the standard record consistent while preserving all data.

Usage:
    Called by the scraper Lambda handler via run()
    Never call fetch() directly — always use run()
"""

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import logging
from src.scrapers.engine.base_scraper import BaseScraper
from src.scrapers.engine.api_fetcher import APIFetcher

logger = logging.getLogger(__name__)


class GoldApiIoScraper(BaseScraper):
    """
    Scraper for GoldAPI.io

    Inherits from BaseScraper:
    - run()                → safely execute the scraper
    - build_result()       → standard result wrapper
    - build_price_record() → standard price record format
    - is_valid_price()     → validates price against metals.json ranges
    - metals_config        → loaded from metals.json automatically

    Must implement:
    - fetch()              → get prices for all 3 metals

    Special responsibilities:
    - Map karat gram prices to standard karats{} format
    - Preserve extended karats in extra{}
    - Store ask, bid, change data in extra{}
    """

    # Maps our internal metal ids → GoldAPI.io symbols
    METAL_SYMBOLS = {
        "gold":     "XAU",
        "silver":   "XAG",
        "platinum": "XPT"
    }

    # Standard karats — stored at top level in karats{}
    # These match what's defined in metals.json
    STANDARD_KARATS = ["24k", "22k", "18k"]

    # Extended karats — stored in extra{} only
    # Preserve the data but don't include in standard record
    EXTENDED_KARATS = ["21k", "20k", "16k", "14k", "10k"]

    def __init__(self, source_config: dict):
        """
        Initialises the scraper with source config from sources.json

        Args:
            source_config: The goldapi_io block from sources.json
        """
        super().__init__(source_config)

        # Create the API fetcher — handles header auth automatically
        self.fetcher = APIFetcher(source_config)

        logger.info(
            f"[{self.source_id}] Scraper initialised — "
            f"metals: {self.metals}"
        )

    # ============================================================
    # fetch() — required by BaseScraper — must be implemented
    # ============================================================
    def fetch(self) -> list:
        """
        Fetches prices for all 3 metals from GoldAPI.io

        Makes one API call per metal — 3 calls total per run.
        Each call costs 1 of our 100 monthly quota.

        Returns:
            List of standard price records — one per metal
            Partial list if some metals fail — others still return

        Raises:
            Exception if something unexpected happens
            (run() will catch this and return a failed result)
        """

        records = []

        for metal in self.metals:

            # Get the API symbol for this metal
            symbol = self.METAL_SYMBOLS.get(metal)

            if not symbol:
                logger.warning(
                    f"[{self.source_id}] No symbol mapping for "
                    f"'{metal}' — skipping"
                )
                continue

            try:
                # Call the API — one call per metal
                response = self.fetcher.fetch(
                    endpoint=f"/{symbol}/USD"
                )

                # Build the price record from response
                record = self._build_metal_record(metal, response)

                if record:
                    records.append(record)

            except Exception as e:
                # One metal failing does not stop the others
                logger.error(
                    f"[{self.source_id}] Failed to fetch {metal} — "
                    f"{str(e)}"
                )
                continue

        logger.info(
            f"[{self.source_id}] Fetch complete — "
            f"{len(records)}/{len(self.metals)} metals successful"
        )

        return records

    # ============================================================
    # Build a price record for a single metal
    # ============================================================
    def _build_metal_record(
        self,
        metal: str,
        response: dict
    ) -> dict:
        """
        Builds a standard price record from the API response.

        Extracts spot price, karat gram prices, ask/bid,
        and price movement data.

        Args:
            metal:    Metal id — "gold", "silver", "platinum"
            response: Raw JSON response from GoldAPI.io

        Returns:
            Standard price record dict
            None if price missing or invalid
        """

        # Extract spot price
        price_field = self.fields_map["price"]
        price_usd = response.get(price_field)

        if price_usd is None:
            logger.error(
                f"[{self.source_id}] No price in response "
                f"for {metal} — response: {response}"
            )
            return None

        # Validate price is within expected range
        if not self.is_valid_price(price_usd, metal):
            logger.error(
                f"[{self.source_id}] Price validation failed "
                f"for {metal}: ${price_usd} — skipping"
            )
            return None

        # Extract timestamp — Unix integer format
        timestamp = response.get(self.fields_map["timestamp"])

        # Build standard karats — 24K, 22K, 18K
        karats = self._extract_standard_karats(response)

        # Build extra fields — extended karats + market data
        extra = self._build_extra_fields(response, timestamp)

        # Build standard price record
        record = self.build_price_record(
            metal=metal,
            price_usd=price_usd,
            extra={
                "karats":           karats,
                **extra
            }
        )

        logger.info(
            f"[{self.source_id}] {metal.upper()} fetched — "
            f"${price_usd} — "
            f"22K/gram: ${response.get('price_gram_22k')}"
        )

        return record

    # ============================================================
    # Extract standard karat gram prices
    # ============================================================
    def _extract_standard_karats(self, response: dict) -> dict:
        """
        Extracts the 3 standard karat gram prices from the response.

        Standard karats match what's defined in metals.json:
        24K, 22K, 18K

        Args:
            response: Raw JSON response from GoldAPI.io

        Returns:
            Dict of standard karat prices
            e.g. {"24K": 168.02, "22K": 154.02, "18K": 126.02}
        """

        karats = {}

        for karat in self.STANDARD_KARATS:
            field = f"price_gram_{karat}"
            value = response.get(field)

            if value is not None:
                # Store with uppercase key — "24k" → "24K"
                karats[karat.upper()] = value

        return karats

    # ============================================================
    # Build extra fields
    # ============================================================
    def _build_extra_fields(
        self,
        response: dict,
        timestamp
    ) -> dict:
        """
        Builds extra{} fields — extended karats + market data.

        Extended karats (21K, 20K, 16K, 14K, 10K) are preserved
        here so data is not lost but standard record stays clean.

        Market data (ask, bid, change) is useful for Phase 2
        when the agent brain answers trend questions.

        Args:
            response:  Raw JSON response
            timestamp: Raw timestamp from response

        Returns:
            Dict of extra fields
        """

        extra = {
            "source_timestamp": timestamp
        }

        # Extended karat gram prices
        extended_karats = {}
        for karat in self.EXTENDED_KARATS:
            field = f"price_gram_{karat}"
            value = response.get(field)
            if value is not None:
                extended_karats[karat.upper()] = value

        if extended_karats:
            extra["extended_karats"] = extended_karats

        # Market data — ask, bid, price movement
        extra.update({
            "ask":              response.get(self.fields_map.get("ask")),
            "bid":              response.get(self.fields_map.get("bid")),
            "change":           response.get(self.fields_map.get("change")),
            "change_percent":   response.get(self.fields_map.get("change_percent")),
            "prev_close_price": response.get("prev_close_price"),
            "open_price":       response.get("open_price"),
            "high_price":       response.get("high_price"),
            "low_price":        response.get("low_price"),
            "exchange":         response.get("exchange"),
            "symbol":           response.get("symbol")
        })

        return extra