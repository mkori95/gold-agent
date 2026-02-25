"""
data_normaliser.py

Normalises price data from all sources into a single
standard format that the rest of the system expects.

Every source returns data differently:
- Different field names
- Different timestamp formats
- Some have karat prices, some don't
- Some have INR prices, some don't

This class converts everything into one standard format
so the consolidator always knows what to expect.
"""

import logging
import json
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class DataNormaliser:
    """
    Normalises raw price data from any source into
    a standard format.

    Standard price record format:
    {
        "metal":          "gold",
        "price_usd":      5213.67,
        "price_inr":      473878.0,
        "unit":           "troy_ounce",
        "source_id":      "gold_api_com",
        "source_name":    "Gold-API.com",
        "timestamp":      "2026-02-25T17:19:42+00:00",
        "karats": {
            "24K": { "price_usd": 5212.49, "price_inr": 473771.0 },
            "22K": { "price_usd": 4778.78, "price_inr": 434407.0 },
            "18K": { "price_usd": 3910.25, "price_inr": 355583.0 }
        },
        "extra": {}
    }
    """

    def __init__(self):
        """
        Loads metals config on startup so we have
        purity ratios and price ranges available.
        """
        self.metals_config = self._load_metals_config()

        # Latest INR rate — updated whenever Metals.Dev runs
        # Used to convert USD prices to INR
        self._inr_rate = None

    # ============================================================
    # Main method — normalise a single price record
    # ============================================================
    def normalise(
        self,
        metal: str,
        price_usd: float,
        source_id: str,
        source_name: str,
        timestamp: str = None,
        price_inr: float = None,
        inr_rate: float = None,
        karat_prices_usd: dict = None,
        extra: dict = None
    ) -> Optional[dict]:
        """
        Normalises a single price record into standard format.

        Args:
            metal:            Metal id — "gold", "silver" etc
            price_usd:        Raw spot price in USD
            source_id:        Source id from sources.json
            source_name:      Human readable source name
            timestamp:        Timestamp string from source
            price_inr:        INR price if source provides it
            inr_rate:         USD to INR rate if available
            karat_prices_usd: Karat prices if source provides them
                              e.g. {"24K": 167.55, "22K": 153.58}
            extra:            Any extra fields to preserve

        Returns:
            Standard price record dict
            None if normalisation fails
        """

        try:
            # Update INR rate if provided
            if inr_rate:
                self._inr_rate = inr_rate

            # Normalise the timestamp
            normalised_timestamp = self._normalise_timestamp(timestamp)

            # Calculate INR price if not provided
            if price_inr is None:
                price_inr = self._convert_to_inr(price_usd)

            # Calculate karat prices
            normalised_karats = self._normalise_karats(
                metal=metal,
                price_usd=price_usd,
                price_inr=price_inr,
                karat_prices_usd=karat_prices_usd
            )

            # Build the standard record
            record = {
                "metal": metal,
                "price_usd": round(price_usd, 4),
                "price_inr": round(price_inr, 2) if price_inr else None,
                "unit": "troy_ounce",
                "source_id": source_id,
                "source_name": source_name,
                "timestamp": normalised_timestamp,
                "karats": normalised_karats,
                "extra": extra or {}
            }

            logger.info(
                f"[{source_id}] Normalised {metal} — "
                f"USD ${price_usd} — "
                f"INR ₹{price_inr}"
            )

            return record

        except Exception as e:
            logger.error(
                f"[{source_id}] Normalisation failed for {metal} — "
                f"{str(e)}"
            )
            return None

    # ============================================================
    # Normalise timestamp — convert any format to ISO string
    # ============================================================
    def _normalise_timestamp(self, timestamp) -> str:
        """
        Converts any timestamp format to standard ISO 8601 string.

        Different sources give timestamps differently:
        - Gold-API.com: "2026-02-25T17:19:42Z" (ISO string)
        - GoldAPI.io:   1772041039 (Unix integer)
        - GoodReturns:  None (no timestamp on scraped pages)

        All get converted to: "2026-02-25T17:19:42+00:00"

        Args:
            timestamp: Timestamp in any format or None

        Returns:
            ISO 8601 timestamp string in UTC
        """

        # No timestamp provided — use current time
        if timestamp is None:
            return datetime.now(timezone.utc).isoformat()

        # Unix integer timestamp — e.g. GoldAPI.io
        if isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc
            ).isoformat()

        # ISO string timestamp — e.g. Gold-API.com
        if isinstance(timestamp, str):
            try:
                # Handle "Z" suffix — replace with "+00:00"
                clean = timestamp.replace("Z", "+00:00")
                dt = datetime.fromisoformat(clean)

                # Make sure it's UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)

                return dt.isoformat()

            except ValueError:
                logger.warning(
                    f"Could not parse timestamp: {timestamp} — "
                    f"using current time"
                )
                return datetime.now(timezone.utc).isoformat()

        # Unknown format — use current time
        logger.warning(
            f"Unknown timestamp format: {type(timestamp)} — "
            f"using current time"
        )
        return datetime.now(timezone.utc).isoformat()

    # ============================================================
    # Convert USD price to INR
    # ============================================================
    def _convert_to_inr(self, price_usd: float) -> Optional[float]:
        """
        Converts a USD price to INR using the latest rate
        from Metals.Dev.

        Metals.Dev gives us currencies.INR which is the
        value of 1 USD in INR terms expressed as a fraction.

        For example:
        INR rate = 0.0110022345
        This means 1 INR = 0.011 USD
        So 1 USD = 1 / 0.011 = 90.89 INR

        Args:
            price_usd: Price in USD

        Returns:
            Price in INR or None if no INR rate available
        """

        if self._inr_rate is None:
            logger.warning(
                "No INR rate available yet — "
                "INR price will be None until Metals.Dev runs"
            )
            return None

        # Convert fraction to full rate
        # metals.dev INR value is how much 1 USD is worth in INR fraction
        usd_to_inr = 1 / self._inr_rate

        return round(price_usd * usd_to_inr, 2)

    # ============================================================
    # Normalise karat prices
    # ============================================================
    def _normalise_karats(
        self,
        metal: str,
        price_usd: float,
        price_inr: Optional[float],
        karat_prices_usd: dict = None
    ) -> dict:
        """
        Builds normalised karat prices for gold.

        Two scenarios:
        1. Source provides karat prices (GoldAPI.io) → use them
        2. Source only has spot price → calculate from purity ratios

        For non-gold metals — returns empty dict.

        Args:
            metal:            Metal id
            price_usd:        Spot price in USD
            price_inr:        Spot price in INR
            karat_prices_usd: Karat prices if provided by source

        Returns:
            Dict of karat prices in USD and INR
            Empty dict for non-gold metals
        """

        # Only gold has karat prices
        if metal != "gold":
            return {}

        # Get karat definitions from metals config
        if metal not in self.metals_config:
            return {}

        karats_config = self.metals_config[metal].get("karats", [])

        if not karats_config:
            return {}

        normalised = {}

        for karat_def in karats_config:
            karat = karat_def["karat"]       # e.g. "24K"
            purity = karat_def["purity"]     # e.g. 0.9166

            # Scenario 1 — source provided karat prices directly
            # e.g. GoldAPI.io gives price_gram_24k, price_gram_22k
            if karat_prices_usd and karat in karat_prices_usd:
                karat_usd = karat_prices_usd[karat]

            # Scenario 2 — calculate from spot price using purity ratio
            else:
                karat_usd = round(price_usd * purity, 4)

            # Convert karat price to INR
            karat_inr = None
            if price_inr is not None:
                karat_inr = round(price_inr * purity, 2)

            normalised[karat] = {
                "price_usd": karat_usd,
                "price_inr": karat_inr
            }

        return normalised

    # ============================================================
    # Update INR rate — called when Metals.Dev runs
    # ============================================================
    def update_inr_rate(self, inr_rate: float) -> None:
        """
        Updates the stored INR rate.

        Called by the Metals.Dev scraper after every run
        so all other scrapers can use the latest rate.

        Args:
            inr_rate: Latest USD to INR rate from Metals.Dev
        """
        self._inr_rate = inr_rate
        logger.info(
            f"INR rate updated — "
            f"1 USD = ₹{round(1 / inr_rate, 2)}"
        )

    # ============================================================
    # Load metals config from config/metals.json
    # ============================================================
    def _load_metals_config(self) -> dict:
        """
        Loads metals.json and returns dict keyed by metal id.

        Returns:
            Dict of metal configs keyed by metal id
        """
        try:
            config_path = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "..", "config", "metals.json"
            )
            config_path = os.path.abspath(config_path)

            with open(config_path, "r") as f:
                data = json.load(f)

            return {
                metal["id"]: metal
                for metal in data["metals"]
            }

        except Exception as e:
            logger.warning(
                f"Could not load metals config — "
                f"karat calculation disabled — {str(e)}"
            )
            return {}