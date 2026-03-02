"""
goodreturns.py

Scraper for GoodReturns.in — our primary source for city-wise
gold rates in INR.

What this source gives us that no other source does:
- Gold price per gram in INR for every major Indian city
- 24K, 22K, and 18K karat prices — exactly how jewellers quote
- City-specific rates — Mumbai, Delhi, Chennai, Hyderabad and 24 more
- Prices are baked into server-side HTML — no JavaScript rendering needed

Metals covered: Gold only (Silver and Platinum tabs exist but are JS-driven)
Auth: None required
Rate limit: None — but we scrape politely with 5 second delay between cities
Unit: per gram in INR (NOT troy ounce — this is city retail rate)

URL pattern:
    https://www.goodreturns.in/gold-rates/{city}.html

    Examples:
        /gold-rates/mumbai.html
        /gold-rates/delhi.html
        /gold-rates/chennai.html

HTML structure (confirmed from view-source):
    <span id="24K-price">&#x20b9;16,172</span>  ← 24K per gram
    <span id="22K-price">&#x20b9;14,825</span>  ← 22K per gram
    <span id="18K-price">&#x20b9;12,133</span>  ← 18K per gram

    &#x20b9; is the HTML entity for ₹ — BeautifulSoup decodes it automatically.

Price record note:
    GoodReturns gives us INR prices directly — not USD.
    price_usd = None  (consolidator will back-calculate using INR rate)
    price_inr = actual scraped value
    unit = "gram" (not troy_ounce — this is per gram retail rate)

City coverage:
    28 cities scraped — ahmedabad, ayodhya, bangalore, bhubaneswar,
    chandigarh, chennai, coimbatore, delhi, hyderabad, jaipur,
    kerala, kolkata, lucknow, madurai, mangalore, mumbai, mysore,
    nagpur, nashik, patna, pune, rajkot, salem, surat, trichy,
    vadodara, vijayawada, visakhapatnam

Usage:
    Called by the scraper Lambda handler via run()
    Never call fetch() directly — always use run()
"""

from dotenv import load_dotenv
load_dotenv()

import logging
import re
from src.scrapers.engine.base_scraper import BaseScraper
from src.scrapers.engine.html_scraper import HTMLScraper

logger = logging.getLogger(__name__)


class GoodReturnsScraper(BaseScraper):
    """
    Scraper for GoodReturns.in

    Inherits from BaseScraper:
    - run()                → safely execute the scraper
    - build_result()       → standard result wrapper
    - build_price_record() → standard price record format
    - is_valid_price()     → validates price against metals.json ranges
    - metals_config        → loaded from metals.json automatically

    Must implement:
    - fetch()              → scrape all 28 city pages and return records

    Special responsibilities:
    - Build one record per city (not per metal like other scrapers)
    - Store city name in extra{}
    - Store all 3 karat prices (24K, 22K, 18K) in extra{}
    - price_usd is always None — consolidator handles conversion
    - unit is "gram" not "troy_ounce" — these are retail per-gram rates
    """

    # All 28 cities available on GoodReturns — confirmed from page source
    # Ordered by traffic / importance for India
    CITIES = [
        "mumbai",
        "delhi",
        "chennai",
        "hyderabad",
        "bangalore",
        "kolkata",
        "ahmedabad",
        "pune",
        "jaipur",
        "lucknow",
        "kerala",
        "coimbatore",
        "madurai",
        "visakhapatnam",
        "vijayawada",
        "surat",
        "nagpur",
        "nashik",
        "chandigarh",
        "bhubaneswar",
        "patna",
        "vadodara",
        "rajkot",
        "mangalore",
        "mysore",
        "salem",
        "trichy",
        "ayodhya"
    ]

    # Span IDs in the HTML for each karat
    # Confirmed from view-source — these are stable IDs
    KARAT_IDS = {
        "24K": "24K-price",
        "22K": "22K-price",
        "18K": "18K-price"
    }

    def __init__(self, source_config: dict):
        """
        Initialises the scraper with source config from sources.json

        Args:
            source_config: The goodreturns block from sources.json
        """
        super().__init__(source_config)

        # Create the HTML scraper — handles page download and parsing
        self.scraper = HTMLScraper(source_config)

        logger.info(
            f"[{self.source_id}] Scraper initialised — "
            f"{len(self.CITIES)} cities to scrape"
        )

    # ============================================================
    # fetch() — required by BaseScraper — must be implemented
    # ============================================================
    def fetch(self) -> list:
        """
        Scrapes gold rates for all 28 cities from GoodReturns.in

        Makes one HTTP request per city — 28 requests total.
        HTMLScraper adds a polite 5 second delay between each request
        (configured in sources.json).

        Returns:
            List of standard price records — one per city
            Partial list if some cities fail — others still return

        Raises:
            Exception if something unexpected happens
            (run() will catch this and return a failed result)
        """

        # Build list of endpoints — one per city
        endpoints = [
            f"/gold-rates/{city}.html"
            for city in self.CITIES
        ]

        # Fetch all pages with polite delay between each
        # Returns list of (endpoint, BeautifulSoup or None) tuples
        pages = self.scraper.fetch_multiple(endpoints)

        records = []

        for endpoint, soup in pages:
            # Extract city name from endpoint — "/gold-rates/mumbai.html" → "mumbai"
            city = self._extract_city_from_endpoint(endpoint)

            # Skip cities where page download failed
            if soup is None:
                logger.error(
                    f"[{self.source_id}] Page download failed for "
                    f"{city} — skipping"
                )
                continue

            try:
                record = self._build_city_record(city, soup)
                if record:
                    records.append(record)

            except Exception as e:
                # One city failing does not stop the others
                logger.error(
                    f"[{self.source_id}] Failed to parse {city} — "
                    f"{str(e)}"
                )
                continue

        logger.info(
            f"[{self.source_id}] Fetch complete — "
            f"{len(records)}/{len(self.CITIES)} cities successful"
        )

        return records

    # ============================================================
    # Build a price record for a single city
    # ============================================================
    def _build_city_record(self, city: str, soup) -> dict:
        """
        Extracts gold prices from a city page and builds a
        standard price record.

        Args:
            city: City slug — "mumbai", "delhi" etc
            soup: Parsed BeautifulSoup object for the city page

        Returns:
            Standard price record dict
            None if prices cannot be extracted
        """

        # Extract all 3 karat prices from the page
        karat_prices = self._extract_karat_prices(city, soup)

        # Need at least 22K to proceed — that's the primary jewellery rate
        if "22K" not in karat_prices:
            logger.error(
                f"[{self.source_id}] Could not extract 22K price for "
                f"{city} — skipping city"
            )
            return None

        # Use 22K as the primary price_inr — most relevant for jewellery buyers
        # All karat prices stored in extra{} for full access
        price_inr_22k = karat_prices["22K"]

        # Build standard price record
        # price_usd = None — GoodReturns does not give USD prices
        # unit = "gram" — these are per gram retail rates, not troy ounce
        record = self.build_price_record(
            metal="gold",
            price_usd=None,
            price_inr=price_inr_22k,
            unit="gram",
            extra={
                "city":         city,
                "karat_prices": karat_prices,
                "primary_karat": "22K",
                "currency":     "INR"
            }
        )

        logger.info(
            f"[{self.source_id}] {city.upper()} — "
            f"22K: ₹{price_inr_22k}/g — "
            f"24K: ₹{karat_prices.get('24K', 'N/A')}/g — "
            f"18K: ₹{karat_prices.get('18K', 'N/A')}/g"
        )

        return record

    # ============================================================
    # Extract karat prices from parsed HTML
    # ============================================================
    def _extract_karat_prices(self, city: str, soup) -> dict:
        """
        Finds the price spans and extracts INR values for each karat.

        HTML structure we're parsing:
            <span id="24K-price">&#x20b9;16,172</span>
            <span id="22K-price">&#x20b9;14,825</span>
            <span id="18K-price">&#x20b9;12,133</span>

        BeautifulSoup decodes &#x20b9; → ₹ automatically.
        We then strip ₹ and commas and convert to float.

        Args:
            city: City name for logging
            soup: Parsed BeautifulSoup object

        Returns:
            Dict of karat → price in INR as float
            e.g. {"24K": 16172.0, "22K": 14825.0, "18K": 12133.0}
            Missing karats simply not included in dict
        """

        karat_prices = {}

        for karat, span_id in self.KARAT_IDS.items():
            span = soup.find("span", id=span_id)

            if span is None:
                logger.warning(
                    f"[{self.source_id}] Span id='{span_id}' not found "
                    f"on {city} page — {karat} price unavailable"
                )
                continue

            raw_text = span.get_text(strip=True)

            price = self._parse_inr_price(raw_text, city, karat)

            if price is not None:
                karat_prices[karat] = price

        return karat_prices

    # ============================================================
    # Parse INR price string to float
    # ============================================================
    def _parse_inr_price(
        self,
        raw_text: str,
        city: str,
        karat: str
    ) -> float:
        """
        Converts raw price text from HTML to a clean float.

        Input examples:
            "₹16,172"   → 16172.0
            "₹1,06,752" → 106752.0  (Indian number format)
            "₹14,825"   → 14825.0

        Steps:
        1. Strip the ₹ symbol
        2. Remove all commas (handles Indian number format)
        3. Convert to float
        4. Basic sanity check — gold per gram in INR should be > 1000

        Args:
            raw_text: Raw text from span — e.g. "₹16,172"
            city:     City name for logging
            karat:    Karat label for logging

        Returns:
            Price as float
            None if parsing fails
        """

        try:
            # Remove ₹ symbol and any whitespace
            cleaned = raw_text.replace("₹", "").strip()

            # Remove all commas — handles Indian number format (1,06,752)
            cleaned = cleaned.replace(",", "")

            # Convert to float
            price = float(cleaned)

            # Basic sanity check — gold per gram in INR
            # Should be well above ₹1000 at any realistic price
            if price < 1000:
                logger.warning(
                    f"[{self.source_id}] Suspiciously low price for "
                    f"{city} {karat}: ₹{price} — skipping"
                )
                return None

            # Upper bound — ₹1,00,000/gram would be insane
            if price > 100000:
                logger.warning(
                    f"[{self.source_id}] Suspiciously high price for "
                    f"{city} {karat}: ₹{price} — skipping"
                )
                return None

            return price

        except (ValueError, AttributeError) as e:
            logger.error(
                f"[{self.source_id}] Failed to parse price for "
                f"{city} {karat} — raw: '{raw_text}' — {str(e)}"
            )
            return None

    # ============================================================
    # Extract city name from endpoint path
    # ============================================================
    def _extract_city_from_endpoint(self, endpoint: str) -> str:
        """
        Extracts city slug from endpoint path.

        "/gold-rates/mumbai.html" → "mumbai"

        Args:
            endpoint: The endpoint path string

        Returns:
            City slug string
        """
        # Split on "/" and take last part, then remove ".html"
        return endpoint.split("/")[-1].replace(".html", "")