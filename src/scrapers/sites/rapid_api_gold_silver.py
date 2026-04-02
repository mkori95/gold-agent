"""
rapid_api_gold_silver.py

Scraper for RapidAPI Gold Silver Rates India (soralapps).
Replaces GoodReturns.in — provides city-wise gold and silver
rates for Indian cities and international locations.

What this source gives us:
- Gold rates per 10gm in local currency — all karats (24K, 22K, 18K)
- Silver rates per kg in local currency — multiple purities (999, 925)
- 71 Indian cities + 6 international locations
- No Cloudflare issues — runs perfectly from Lambda

API pattern:
    GET https://gold-silver-live-prices.p.rapidapi.com/getGoldRate?place={place}
    GET https://gold-silver-live-prices.p.rapidapi.com/getSilverRate?place={place}

    Auth headers:
        x-rapidapi-key: YOUR_KEY
        x-rapidapi-host: gold-silver-live-prices.p.rapidapi.com

Gold response (Indian city):
    {
        "location": "MUMBAI",
        "variations per 10g": {
            "Gold 24 Karat (Rs ₹)": "139,720",
            "Gold 22 Karat (Rs ₹)": "128,077",
            "Gold 18 Karat (Rs ₹)": "104,790"
        },
        "GOLD": {
            "price": "139,720.00",
            "change": "+0.00 (+0.000%)",
            "per value": "Rs ₹ / 10gm"
        }
    }

Gold response (International):
    {
        "location": "DUBAI",
        "variations per 10g": {
            "Gold 24 Karat (AED د.إ)": "467",
            "Gold 22 Karat (AED د.إ)": "428"
        },
        "GOLD": {
            "price": "466.75",
            "change": "+5.75 (+1.250%)",
            "per value": "AED د.إ / 10gm"
        }
    }

Silver response (Indian city):
    {
        "location": "MUMBAI",
        "variations per Kg": {
            "Silver 999 Fine (Rs ₹)": "225,530",
            "Silver 925 Sterling (Rs ₹)": "208,615"
        },
        "SILVER": {
            "price": "225,530.00",
            "change": "+0.00 (+0.000%)",
            "per value": "Rs ₹ / 1kg"
        }
    }

Price record notes:
    price_usd  = None — consolidator handles USD conversion
    price_inr  = primary price (22K for gold, 999 Fine for silver) — INR only
    unit       = "gram_10" for gold, "kg" for silver
    extra      = all karat/purity breakdowns + location + currency + change

Active locations driven by sources.json locations.active list.
To enable all locations — update sources.json only, no code change needed.

Usage:
    Called by the scraper Lambda handler via run()
    Never call fetch() directly — always use run()
"""

from dotenv import load_dotenv
load_dotenv()

import logging
import re
import time
from src.scrapers.engine.base_scraper import BaseScraper
from src.scrapers.engine.api_fetcher import APIFetcher

logger = logging.getLogger(__name__)


class RapidApiGoldSilverScraper(BaseScraper):
    """
    Scraper for RapidAPI Gold Silver Rates India.

    Inherits from BaseScraper:
    - run()                → safely execute the scraper
    - build_result()       → standard result wrapper
    - build_price_record() → standard price record format
    - is_valid_price()     → validates price against metals.json ranges
    - metals_config        → loaded from metals.json automatically

    Must implement:
    - fetch()              → fetch gold + silver for all active locations

    Special responsibilities:
    - Read active locations from sources.json locations.active
    - Parse price strings with commas — "139,720" → 139720.0
    - Extract karat prices from key names — "Gold 24 Karat (Rs ₹)"
    - Handle Indian and international currency formats
    - price_usd always None — consolidator handles conversion
    """

    def __init__(self, source_config: dict):
        """
        Initialises the scraper with source config from sources.json.

        Args:
            source_config: The rapid_api_gold_silver block from sources.json
        """
        super().__init__(source_config)

        locations = source_config.get("locations", {})
        self.active_locations        = locations.get("active", [])
        self.international_locations = set(locations.get("all_international", []))
        self.currency_map            = source_config.get("currency_map", {})
        self.rapidapi_host           = source_config["auth"]["host_header"]

        self.fetcher = APIFetcher(source_config)

        logger.info(
            f"[{self.source_id}] Scraper initialised — "
            f"{len(self.active_locations)} active locations: {self.active_locations}"
        )

    # ============================================================
    # fetch() — required by BaseScraper — must be implemented
    # ============================================================
    def fetch(self) -> list:
        """
        Fetches gold and silver rates for all active locations.

        Makes 2 API calls per location (gold + silver).
        One record per metal per location returned.

        Returns:
            List of standard price records
            Partial list if some locations fail — others continue
        """

        records = []

        for location in self.active_locations:

            # Fetch gold
            try:
                gold_record = self._fetch_gold(location)
                if gold_record:
                    records.append(gold_record)
            except Exception as e:
                logger.error(
                    f"[{self.source_id}] Failed to fetch gold for "
                    f"{location} — {str(e)}"
                )

            # Fetch silver
            try:
                silver_record = self._fetch_silver(location)
                if silver_record:
                    records.append(silver_record)
            except Exception as e:
                logger.error(
                    f"[{self.source_id}] Failed to fetch silver for "
                    f"{location} — {str(e)}"
                )

        logger.info(
            f"[{self.source_id}] Fetch complete — "
            f"{len(records)} records from {len(self.active_locations)} locations"
        )

        return records

    # ============================================================
    # Fetch with retry
    # ============================================================
    def _fetch_with_retry(self, endpoint: str, params: dict, max_retries: int = 3) -> dict:
        """
        Fetches from API with retry on timeout or failure.

        Args:
            endpoint:    API endpoint
            params:      Query params
            max_retries: Max attempts before giving up

        Returns:
            Raw JSON response or raises last exception
        """

        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                return self.fetcher.fetch(
                    endpoint=endpoint,
                    params=params,
                    headers={"x-rapidapi-host": self.rapidapi_host}
                )
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"[{self.source_id}] Attempt {attempt}/{max_retries} failed "
                    f"for {endpoint} params={params} — {str(e)}"
                )
                if attempt < max_retries:
                    time.sleep(2)

        raise last_exception

    # ============================================================
    # Fetch gold rate for a single location
    # ============================================================
    def _fetch_gold(self, location: str) -> dict:
        """
        Fetches gold rate for a single location.

        Args:
            location: Location slug — e.g. "mumbai", "dubai"

        Returns:
            Standard price record or None if fetch fails
        """

        response = self._fetch_with_retry(
            endpoint="/getGoldRate",
            params={"place": location}
        )

        return self._build_gold_record(location, response)

    # ============================================================
    # Fetch silver rate for a single location
    # ============================================================
    def _fetch_silver(self, location: str) -> dict:
        """
        Fetches silver rate for a single location.

        Args:
            location: Location slug — e.g. "mumbai", "dubai"

        Returns:
            Standard price record or None if fetch fails
        """

        response = self._fetch_with_retry(
            endpoint="/getSilverRate",
            params={"place": location}
        )

        return self._build_silver_record(location, response)

    # ============================================================
    # Build gold price record from API response
    # ============================================================
    def _build_gold_record(self, location: str, response: dict) -> dict:
        """
        Builds a standard price record from gold API response.

        Extracts primary price (22K for Indian, 24K for international)
        and all karat breakdowns.

        Args:
            location: Location slug
            response: Raw JSON response from API

        Returns:
            Standard price record or None if parsing fails
        """

        if not response:
            logger.error(f"[{self.source_id}] Empty gold response for {location}")
            return None

        variations   = response.get("variations per 10g", {})
        karat_prices = self._parse_karat_prices(variations)

        if not karat_prices:
            logger.error(
                f"[{self.source_id}] No karat prices found for gold in {location}"
            )
            return None

        currency         = self._detect_currency(variations)
        is_international = location in self.international_locations
        primary_karat    = "24K" if is_international else "22K"
        primary_price    = karat_prices.get(primary_karat)

        # Fallback to first available karat
        if primary_price is None:
            primary_price = next(iter(karat_prices.values()), None)

        # Reject zero or None price
        if not primary_price:
            logger.error(
                f"[{self.source_id}] Gold price is zero or None for {location} — skipping"
            )
            return None

        gold_block = response.get("GOLD", {})

        price_inr   = primary_price if not is_international else None
        price_local = primary_price if is_international else None

        record = self.build_price_record(
            metal="gold",
            price_usd=None,
            price_inr=price_inr,
            unit="gram_10",
            extra={
                "location":         location,
                "is_international": is_international,
                "currency":         currency,
                "primary_karat":    primary_karat,
                "karat_prices":     karat_prices,
                "price_local":      price_local,
                "change":           gold_block.get("change", ""),
                "per_value":        gold_block.get("per value", "")
            }
        )

        logger.info(
            f"[{self.source_id}] Gold {location.upper()} — "
            f"{primary_karat}: {currency}{primary_price}/10gm"
        )

        return record

    # ============================================================
    # Build silver price record from API response
    # ============================================================
    def _build_silver_record(self, location: str, response: dict) -> dict:
        """
        Builds a standard price record from silver API response.

        Primary price is Silver 999 Fine (highest purity).

        Args:
            location: Location slug
            response: Raw JSON response from API

        Returns:
            Standard price record or None if parsing fails
        """

        if not response:
            logger.error(f"[{self.source_id}] Empty silver response for {location}")
            return None

        variations    = response.get("variations per Kg", {})
        purity_prices = self._parse_karat_prices(variations)

        if not purity_prices:
            logger.error(
                f"[{self.source_id}] No purity prices found for silver in {location}"
            )
            return None

        currency         = self._detect_currency(variations)
        is_international = location in self.international_locations

        # Find 999 Fine key
        primary_purity = None
        primary_price  = None

        for key, price in purity_prices.items():
            if "999" in key:
                primary_purity = key
                primary_price  = price
                break

        # Fallback to first available purity
        if primary_price is None:
            primary_purity, primary_price = next(iter(purity_prices.items()), (None, None))

        # Reject zero or None price
        if not primary_price:
            logger.error(
                f"[{self.source_id}] Silver price is zero or None for {location} — skipping"
            )
            return None

        silver_block = response.get("SILVER", {})

        price_inr   = primary_price if not is_international else None
        price_local = primary_price if is_international else None

        record = self.build_price_record(
            metal="silver",
            price_usd=None,
            price_inr=price_inr,
            unit="kg",
            extra={
                "location":         location,
                "is_international": is_international,
                "currency":         currency,
                "primary_purity":   primary_purity,
                "purity_prices":    purity_prices,
                "price_local":      price_local,
                "change":           silver_block.get("change", ""),
                "per_value":        silver_block.get("per value", "")
            }
        )

        logger.info(
            f"[{self.source_id}] Silver {location.upper()} — "
            f"{primary_purity}: {currency}{primary_price}/kg"
        )

        return record

    # ============================================================
    # Parse karat/purity prices from variations dict
    # ============================================================
    def _parse_karat_prices(self, variations: dict) -> dict:
        """
        Parses karat or purity prices from the variations block.

        Input key format: "Gold 24 Karat (Rs ₹)" → key "24K"
                          "Silver 999 Fine (Rs ₹)" → key "999 Fine"

        Strips commas from price strings and converts to float.

        Args:
            variations: The "variations per 10g" or "variations per Kg" dict

        Returns:
            Dict of simplified key → float price
        """

        parsed = {}

        for key, value in variations.items():

            karat_match = re.search(r'(\d+)\s*Karat', key, re.IGNORECASE)
            if karat_match:
                simplified_key = f"{karat_match.group(1)}K"
            else:
                purity_match = re.search(r'Silver\s+(.+?)\s*\(', key, re.IGNORECASE)
                if purity_match:
                    simplified_key = purity_match.group(1).strip()
                else:
                    simplified_key = key

            price = self._parse_price(str(value))
            if price is not None:
                parsed[simplified_key] = price

        return parsed

    # ============================================================
    # Parse price string to float
    # ============================================================
    def _parse_price(self, price_str: str) -> float:
        """
        Converts price string to float.

        Handles Indian number format with commas:
            "139,720.00" → 139720.0
            "139,720"    → 139720.0

        Args:
            price_str: Raw price string from API

        Returns:
            Float price or None if parsing fails
        """

        try:
            cleaned = price_str.replace(",", "").strip()
            return float(cleaned)
        except (ValueError, AttributeError):
            logger.warning(
                f"[{self.source_id}] Could not parse price: '{price_str}'"
            )
            return None

    # ============================================================
    # Detect currency from variation keys
    # ============================================================
    def _detect_currency(self, variations: dict) -> str:
        """
        Detects currency from variation key names.

        Key format: "Gold 24 Karat (Rs ₹)" → "INR"
                    "Gold 24 Karat (AED د.إ)" → "AED"

        Args:
            variations: The variations dict from API response

        Returns:
            Currency code string — defaults to "INR" if not detected
        """

        for key in variations.keys():
            for symbol, code in self.currency_map.items():
                if symbol in key:
                    return code

        return "INR"