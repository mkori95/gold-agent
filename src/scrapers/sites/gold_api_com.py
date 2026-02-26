"""
gold_api_com.py

Scraper for Gold-API.com — our primary unlimited price source.

What this source gives us:
- Live spot prices for Gold, Silver, Platinum, Copper
- No API key needed — completely free and unlimited
- Clean JSON response — very simple to parse
- Updates every few seconds

API pattern:
    GET https://api.gold-api.com/price/{symbol}

    Response:
    {
        "name": "Gold",
        "price": 5185.899902,
        "symbol": "XAU",
        "updatedAt": "2026-02-26T22:05:24Z",
        "updatedAtReadable": "a few seconds ago"
    }

This scraper:
1. Loops through all 4 metals
2. Maps metal id → API symbol (gold → XAU)
3. Calls /price/{symbol} for each metal
4. Validates the price against metals.json ranges
5. Builds a standard price record for each metal
6. Returns all 4 records as a list

Usage:
    Called by the scraper Lambda handler via run()
    Never call fetch() directly — always use run()
"""

import logging
from src.scrapers.engine.base_scraper import BaseScraper
from src.scrapers.engine.api_fetcher import APIFetcher

logger = logging.getLogger(__name__)


class GoldApiComScraper(BaseScraper):
    """
    Scraper for Gold-API.com

    Inherits from BaseScraper:
    - run()              → call this to safely execute the scraper
    - build_result()     → standard result wrapper
    - build_price_record() → standard price record format
    - is_valid_price()   → validates price against metals.json ranges
    - metals_config      → loaded from metals.json automatically

    Must implement:
    - fetch()            → our job — get prices and return records list
    """

    # Maps our internal metal ids → Gold-API.com symbols
    # These are standard ISO 4217 commodity codes
    METAL_SYMBOLS = {
        "gold":     "XAU",
        "silver":   "XAG",
        "platinum": "XPT",
        "copper":   "HG"
    }

    def __init__(self, source_config: dict):
        """
        Initialises the scraper with source config from sources.json

        Args:
            source_config: The gold_api_com block from sources.json
        """
        super().__init__(source_config)

        # Create the API fetcher — handles all HTTP calls
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
        Fetches live prices for all metals from Gold-API.com

        Loops through each metal in sources.json metals list,
        calls the API, validates the price, builds a record.

        Returns:
            List of standard price records — one per metal
            Empty list if all metals fail (handled by run())

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
                    f"metal '{metal}' — skipping"
                )
                continue

            try:
                # Call the API — returns raw JSON dict
                response = self.fetcher.fetch(
                    endpoint=f"/price/{symbol}"
                )

                # Extract price and timestamp from response
                # Using fields_map from sources.json for field names
                price_field = self.fields_map["price"]
                timestamp_field = self.fields_map["timestamp"]

                price_usd = response.get(price_field)
                timestamp = response.get(timestamp_field)
                name = response.get("name", metal)

                # Validate we actually got a price back
                if price_usd is None:
                    logger.error(
                        f"[{self.source_id}] No price in response "
                        f"for {metal} — response was: {response}"
                    )
                    continue

                # Validate price is within expected range
                if not self.is_valid_price(price_usd, metal):
                    logger.error(
                        f"[{self.source_id}] Price validation failed "
                        f"for {metal}: ${price_usd} — skipping"
                    )
                    continue

                # Build standard price record
                record = self.build_price_record(
                    metal=metal,
                    price_usd=price_usd,
                    extra={
                        "symbol": symbol,
                        "name": name,
                        "source_timestamp": timestamp,
                        "updatedAtReadable": response.get("updatedAtReadable")
                    }
                )

                records.append(record)

                logger.info(
                    f"[{self.source_id}] {metal.upper()} fetched — "
                    f"${price_usd}"
                )

            except Exception as e:
                # One metal failing does NOT stop the others
                # Log and continue to next metal
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
