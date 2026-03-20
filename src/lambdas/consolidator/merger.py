"""
merger.py

Merges validated scraper results into a single metals dict
ready for the final snapshot.

This is the core of the consolidator — it orchestrates
AnomalyDetector and TrimmedMean to produce one trusted
price per metal from all sources.

What this file does:
    1. Groups all price records by metal across all sources
    2. Separates GoodReturns city rates from spot price records
    3. Runs anomaly detection on all spot price records
    4. Runs trimmed mean on validated prices per metal
    5. Attaches INR prices using the provided INR rate
    6. Attaches karat prices from GoldAPI.io
    7. Attaches extra fields (MCX, IBJA, LBMA) from Metals.Dev
    8. Attaches city rates from GoodReturns
    9. Returns merged metals dict

INR rate is passed in explicitly by the consolidator —
it is extracted from the MetalsDevScraper instance after run().

GoodReturns records are identified by unit == "gram" —
they go directly into city_rates{} and never enter the
trimmed mean calculation.

Usage:
    merger = Merger()
    merged = merger.merge(validated_results, inr_rate=0.01099)
"""

import logging
from src.lambdas.consolidator.anomaly_detector import AnomalyDetector
from src.lambdas.consolidator.trimmed_mean import TrimmedMean

logger = logging.getLogger(__name__)

# Metals we expect to process
KNOWN_METALS = ["gold", "silver", "platinum", "copper"]


class Merger:
    """
    Merges validated scraper results into a single metals dict.

    Orchestrates AnomalyDetector and TrimmedMean.
    Handles routing of GoodReturns city rates separately.
    Attaches extra fields from Metals.Dev and GoldAPI.io.
    """

    def __init__(self):
        """
        Initialises with AnomalyDetector and TrimmedMean instances.
        """
        self.anomaly_detector = AnomalyDetector()
        self.trimmed_mean     = TrimmedMean()

    # ============================================================
    # Main method — merge all scraper results
    # ============================================================
    def merge(self, validated_results: list, inr_rate: float = None) -> dict:
        """
        Merges validated scraper results into a single metals dict.

        Args:
            validated_results: List of valid scraper result dicts
                               from Validator.filter_valid()
            inr_rate:          INR rate from MetalsDevScraper.inr_rate
                               e.g. 0.01099 means 1 INR = 0.01099 USD
                               None if Metals.Dev did not run

        Returns:
            Dict with inr_rate, usd_to_inr, and metals{}
        """

        # Calculate USD to INR conversion rate
        usd_to_inr = round(1 / inr_rate, 4) if inr_rate else None

        logger.info(
            f"Merger starting — "
            f"{len(validated_results)} sources — "
            f"INR rate: {inr_rate} — "
            f"1 USD = ₹{usd_to_inr}"
        )

        # --------------------------------------------------------
        # Step 1 — collect all records grouped by metal
        # --------------------------------------------------------
        spot_records_by_metal = self._group_spot_records(validated_results)
        city_rates_by_city    = self._extract_city_rates(validated_results)

        # --------------------------------------------------------
        # Step 2 — collect extra fields per metal from all sources
        # --------------------------------------------------------
        extra_by_metal  = self._extract_extra_fields(validated_results)
        karats_by_metal = self._extract_karat_prices(validated_results)

        # --------------------------------------------------------
        # Step 3 — build consensus per metal
        # --------------------------------------------------------
        metals = {}

        for metal in KNOWN_METALS:
            records = spot_records_by_metal.get(metal, [])

            if not records:
                logger.warning(
                    f"No spot price records found for {metal} — skipping"
                )
                continue

            metal_result = self._build_metal_result(
                metal=metal,
                records=records,
                inr_rate=inr_rate,
                usd_to_inr=usd_to_inr,
                extra=extra_by_metal.get(metal, {}),
                karats=karats_by_metal.get(metal, {}),
                city_rates=city_rates_by_city if metal == "gold" else {}
            )

            if metal_result:
                metals[metal] = metal_result

        logger.info(
            f"Merger complete — "
            f"{len(metals)} metals processed: {list(metals.keys())}"
        )

        return {
            "inr_rate":   inr_rate,
            "usd_to_inr": usd_to_inr,
            "metals":     metals
        }

    # ============================================================
    # Build consensus result for a single metal
    # ============================================================
    def _build_metal_result(
        self,
        metal:      str,
        records:    list,
        inr_rate:   float,
        usd_to_inr: float,
        extra:      dict,
        karats:     dict,
        city_rates: dict
    ) -> dict:
        """
        Builds the consensus result for a single metal.

        Runs anomaly detection, then trimmed mean, then
        attaches INR price, karats, city rates and extra fields.

        Args:
            metal:      Metal id — "gold", "silver" etc
            records:    List of spot price records for this metal
            inr_rate:   INR rate for conversion
            usd_to_inr: Precomputed USD to INR rate
            extra:      Extra fields dict (MCX, IBJA, LBMA)
            karats:     Karat prices dict from GoldAPI.io
            city_rates: City rates dict from GoodReturns (gold only)

        Returns:
            Metal result dict or None if no valid prices
        """

        # Run anomaly detection — filter out bad prices
        valid_records = self.anomaly_detector.filter(records)

        if not valid_records:
            logger.warning(
                f"All {metal} records rejected by anomaly detection"
            )
            return None

        # Build source_prices dict for trimmed mean
        source_prices = {
            record["source_id"]: record["price_usd"]
            for record in valid_records
        }

        # Run trimmed mean
        consensus = self.trimmed_mean.calculate(source_prices)

        consensus_price_usd = consensus["consensus_price"]

        # Calculate INR price
        price_inr = None
        if consensus_price_usd is not None and inr_rate:
            price_inr = round(consensus_price_usd / inr_rate, 2)

        # Calculate karat prices if not provided by GoldAPI.io
        # Use purity ratios — 24K=0.9999, 22K=0.9166, 18K=0.75
        if not karats and metal == "gold" and consensus_price_usd:
            karats = self._calculate_karats(
                price_usd=consensus_price_usd,
                price_inr=price_inr
            )

        logger.info(
            f"{metal.upper()} consensus — "
            f"${consensus_price_usd} — "
            f"₹{price_inr} — "
            f"confidence: {consensus['confidence']} — "
            f"sources: {consensus['sources_used']}"
        )

        return {
            "price_usd":      consensus_price_usd,
            "price_inr":      price_inr,
            "unit":           "troy_ounce",
            "confidence":     consensus["confidence"],
            "sources_used":   consensus["sources_used"],
            "sources_count":  consensus["sources_count"],
            "source_prices":  consensus["source_prices"],
            "spread_percent": consensus["spread_percent"],
            "spread_flagged": consensus["spread_flagged"],
            "karats":         karats,
            "city_rates":     city_rates,
            "extra":          extra
        }

    # ============================================================
    # Group spot price records by metal
    # ============================================================
    def _group_spot_records(self, validated_results: list) -> dict:
        """
        Groups all spot price records by metal across all sources.

        Excludes GoodReturns records (unit == "gram") —
        those go to city_rates, not the trimmed mean.

        Args:
            validated_results: List of valid scraper result dicts

        Returns:
            Dict of metal → list of price records
            e.g. {"gold": [...], "silver": [...]}
        """

        records_by_metal = {}

        for result in validated_results:
            source_id = result.get("source_id", "unknown")

            for record in result.get("data", []):
                # Skip GoodReturns records — unit is "gram" not "troy_ounce"
                if record.get("unit") == "gram":
                    continue

                # Skip records with no USD price
                if record.get("price_usd") is None:
                    continue

                metal = record.get("metal")

                if not metal:
                    logger.warning(
                        f"[{source_id}] Record missing metal field — skipping"
                    )
                    continue

                if metal not in records_by_metal:
                    records_by_metal[metal] = []

                records_by_metal[metal].append(record)

        for metal, records in records_by_metal.items():
            logger.info(
                f"Grouped {len(records)} spot records for {metal}"
            )

        return records_by_metal

    # ============================================================
    # Extract city rates from GoodReturns records
    # ============================================================
    def _extract_city_rates(self, validated_results: list) -> dict:
        """
        Extracts city-wise INR gold rates from GoodReturns records.

        GoodReturns records are identified by unit == "gram".
        Each record has extra.city and extra.karat_prices.

        Args:
            validated_results: List of valid scraper result dicts

        Returns:
            Dict of city → karat prices
            e.g. {"mumbai": {"24K": 9780.0, "22K": 8950.0, "18K": 7340.0}}
        """

        city_rates = {}

        for result in validated_results:
            for record in result.get("data", []):
                if record.get("unit") != "gram":
                    continue

                extra = record.get("extra", {})
                city  = extra.get("city")

                if not city:
                    continue

                karat_prices = extra.get("karat_prices", {})

                if karat_prices:
                    city_rates[city] = karat_prices

        if city_rates:
            logger.info(
                f"Extracted city rates for {len(city_rates)} cities: "
                f"{list(city_rates.keys())}"
            )

        return city_rates

    # ============================================================
    # Extract extra fields per metal from Metals.Dev records
    # ============================================================
    def _extract_extra_fields(self, validated_results: list) -> dict:
        """
        Extracts extra fields (MCX, IBJA, LBMA) from Metals.Dev records.

        These fields are stored in record.extra{} by MetalsDevScraper.
        We collect them per metal and attach to the final snapshot.

        Args:
            validated_results: List of valid scraper result dicts

        Returns:
            Dict of metal → extra fields dict
        """

        extra_by_metal = {}

        for result in validated_results:
            if result.get("source_id") != "metals_dev":
                continue

            for record in result.get("data", []):
                metal = record.get("metal")
                extra = record.get("extra", {})

                if metal and extra:
                    # Merge extra fields — metals_dev may have multiple
                    # records per metal in edge cases
                    if metal not in extra_by_metal:
                        extra_by_metal[metal] = {}
                    extra_by_metal[metal].update(extra)

        return extra_by_metal

    # ============================================================
    # Extract karat prices from GoldAPI.io records
    # ============================================================
    def _extract_karat_prices(self, validated_results: list) -> dict:
        """
        Extracts karat gram prices from GoldAPI.io records.

        GoldAPI.io stores karat prices in record.extra.karats{}.
        These are per-gram USD prices for 24K, 22K, 18K.

        Args:
            validated_results: List of valid scraper result dicts

        Returns:
            Dict of metal → karats dict
            e.g. {"gold": {"24K": 167.55, "22K": 153.58, "18K": 125.66}}
        """

        karats_by_metal = {}

        for result in validated_results:
            if result.get("source_id") != "goldapi_io":
                continue

            for record in result.get("data", []):
                metal  = record.get("metal")
                extra  = record.get("extra", {})
                karats = extra.get("karats", {})

                if metal and karats:
                    karats_by_metal[metal] = karats

        return karats_by_metal

    # ============================================================
    # Calculate karat prices from spot price using purity ratios
    # ============================================================
    def _calculate_karats(
        self,
        price_usd: float,
        price_inr: float
    ) -> dict:
        """
        Calculates karat prices from spot price using purity ratios.

        Used as fallback when GoldAPI.io data is not available.
        Purity ratios from metals.json:
            24K = 0.9999
            22K = 0.9166
            18K = 0.7500

        Args:
            price_usd: Consensus gold spot price in USD
            price_inr: Consensus gold spot price in INR

        Returns:
            Dict of karat → {price_usd, price_inr}
        """

        purity_ratios = {
            "24K": 0.9999,
            "22K": 0.9166,
            "18K": 0.7500
        }

        karats = {}

        for karat, purity in purity_ratios.items():
            karat_usd = round(price_usd * purity, 4)
            karat_inr = round(price_inr * purity, 2) if price_inr else None

            karats[karat] = {
                "price_usd": karat_usd,
                "price_inr": karat_inr
            }

        return karats