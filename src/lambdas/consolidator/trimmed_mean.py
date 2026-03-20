"""
trimmed_mean.py

Calculates consensus price from multiple source prices
using a trimmed mean algorithm.

This is the core math behind the consolidator. It takes
raw prices from all sources and produces one trusted price.

Rules (based on VALIDATED source count — after anomaly detection):
    0 sources  →  confidence: "unavailable"
    1 source   →  use as-is, confidence: "low"
    2 sources  →  simple average, confidence: "medium"
    3+ sources →  drop highest + lowest, average rest, confidence: "high"

Spread monitoring (post-consensus):
    < 1%   →  normal
    1-2%   →  log warning
    > 2%   →  log warning + flagged in result

Usage:
    trimmed_mean = TrimmedMean()
    result = trimmed_mean.calculate({
        "gold_api_com": 3100.00,
        "metals_dev":   3098.00,
        "goldapi_io":   3106.50
    })
"""

import logging

logger = logging.getLogger(__name__)

# Spread thresholds — percentage
SPREAD_WARNING_THRESHOLD  = 1.0   # log warning above this
SPREAD_CRITICAL_THRESHOLD = 2.0   # flag in result above this


class TrimmedMean:
    """
    Calculates consensus price from multiple source prices.

    Pure math — no external dependencies, no API calls, no config files.
    Takes a dict of source prices, returns a consensus result dict.
    """

    # ============================================================
    # Main method — calculate consensus from source prices
    # ============================================================
    def calculate(self, source_prices: dict) -> dict:
        """
        Calculates consensus price from a dict of source prices.

        Args:
            source_prices: Dict of source_id → price (float)
                           e.g. {"gold_api_com": 3100.00, "metals_dev": 3098.00}
                           Only include sources that PASSED anomaly detection.

        Returns:
            Dict with consensus price, confidence, spread and metadata.
            See module docstring for full structure.
        """

        # --------------------------------------------------------
        # 0 sources — no data at all
        # --------------------------------------------------------
        if not source_prices:
            logger.warning("No source prices provided — cannot calculate consensus")
            return self._build_result(
                consensus_price=None,
                confidence="unavailable",
                sources_used=[],
                sources_count=0,
                spread_percent=None,
                spread_flagged=False,
                source_prices={}
            )

        # Extract source ids and prices as clean lists
        sources = list(source_prices.keys())
        prices  = list(source_prices.values())
        count   = len(prices)

        # --------------------------------------------------------
        # 1 source — use as-is, flag low confidence
        # --------------------------------------------------------
        if count == 1:
            consensus = prices[0]
            logger.info(
                f"Single source consensus: ${consensus} — "
                f"confidence: low"
            )
            return self._build_result(
                consensus_price=consensus,
                confidence="low",
                sources_used=sources,
                sources_count=count,
                spread_percent=0.0,
                spread_flagged=False,
                source_prices=source_prices
            )

        # --------------------------------------------------------
        # 2 sources — simple average, medium confidence
        # --------------------------------------------------------
        if count == 2:
            consensus = round(sum(prices) / 2, 4)
            spread    = self._calculate_spread(prices, consensus)

            logger.info(
                f"Two-source consensus: ${consensus} — "
                f"confidence: medium — "
                f"spread: {spread}%"
            )

            return self._build_result(
                consensus_price=consensus,
                confidence="medium",
                sources_used=sources,
                sources_count=count,
                spread_percent=spread,
                spread_flagged=spread > SPREAD_CRITICAL_THRESHOLD,
                source_prices=source_prices
            )

        # --------------------------------------------------------
        # 3+ sources — trimmed mean, high confidence
        # Drop single highest and single lowest price
        # Average the remaining prices
        # --------------------------------------------------------
        sorted_prices   = sorted(prices)
        trimmed_prices  = sorted_prices[1:-1]   # drop first (lowest) and last (highest)

        # Map trimmed prices back to their source ids
        # Sort sources by price to align with sorted_prices
        sorted_pairs    = sorted(source_prices.items(), key=lambda x: x[1])
        trimmed_pairs   = sorted_pairs[1:-1]
        trimmed_sources = [pair[0] for pair in trimmed_pairs]

        consensus = round(sum(trimmed_prices) / len(trimmed_prices), 4)
        spread    = self._calculate_spread(prices, consensus)

        logger.info(
            f"Trimmed mean consensus ({count} sources): ${consensus} — "
            f"confidence: high — "
            f"spread: {spread}% — "
            f"dropped: lowest=${sorted_prices[0]}, highest=${sorted_prices[-1]}"
        )

        return self._build_result(
            consensus_price=consensus,
            confidence="high",
            sources_used=trimmed_sources,
            sources_count=count,
            spread_percent=spread,
            spread_flagged=spread > SPREAD_CRITICAL_THRESHOLD,
            source_prices=source_prices
        )

    # ============================================================
    # Calculate spread percentage
    # ============================================================
    def _calculate_spread(self, prices: list, consensus: float) -> float:
        """
        Calculates spread percentage across all prices.

        Formula: (max - min) / consensus * 100

        Args:
            prices:    List of all prices (before trimming)
            consensus: The calculated consensus price

        Returns:
            Spread as a percentage rounded to 4 decimal places
            0.0 if consensus is 0 (avoid division by zero)
        """

        if consensus == 0:
            return 0.0

        spread = (max(prices) - min(prices)) / consensus * 100
        spread = round(spread, 4)

        # Log based on spread severity
        if spread > SPREAD_CRITICAL_THRESHOLD:
            logger.warning(
                f"SPREAD ALERT: {spread}% — sources diverging significantly "
                f"(threshold: {SPREAD_CRITICAL_THRESHOLD}%)"
            )
        elif spread > SPREAD_WARNING_THRESHOLD:
            logger.warning(
                f"Spread warning: {spread}% — sources diverging slightly "
                f"(threshold: {SPREAD_WARNING_THRESHOLD}%)"
            )

        return spread

    # ============================================================
    # Build standard result dict
    # ============================================================
    def _build_result(
        self,
        consensus_price,
        confidence:     str,
        sources_used:   list,
        sources_count:  int,
        spread_percent,
        spread_flagged: bool,
        source_prices:  dict
    ) -> dict:
        """
        Builds the standard result dict returned by calculate().

        Args:
            consensus_price: Final consensus price or None
            confidence:      "high" / "medium" / "low" / "unavailable"
            sources_used:    List of source ids that contributed to consensus
            sources_count:   Total number of sources provided (before trimming)
            spread_percent:  Spread as percentage or None
            spread_flagged:  True if spread exceeded critical threshold
            source_prices:   Original source prices dict — always preserved

        Returns:
            Standard result dict
        """
        return {
            "consensus_price": consensus_price,
            "confidence":      confidence,
            "sources_used":    sources_used,
            "sources_count":   sources_count,
            "spread_percent":  spread_percent,
            "spread_flagged":  spread_flagged,
            "source_prices":   source_prices
        }