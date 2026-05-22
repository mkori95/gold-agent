from dataclasses import dataclass
from typing import Optional


@dataclass
class MetalPrice:
    metal: str               # gold | silver | platinum | copper
    price_usd: float
    price_inr: Optional[float]
    inr_rate: Optional[float]
    confidence: str          # high | medium | low
    source_count: int
    spread_pct: Optional[float] = None
    price_22k_inr: Optional[float] = None
    price_24k_inr: Optional[float] = None
    city_rates: Optional[dict] = None
    karat_prices: Optional[dict] = None


@dataclass
class PriceSnapshot:
    snapshot_date: str       # YYYY-MM-DD
    timestamp: str           # ISO-8601
    metals: dict             # metal_id -> MetalPrice

    @classmethod
    def from_dynamo_rows(cls, rows: list) -> "PriceSnapshot":
        """Build a snapshot from a list of per-metal DynamoDB rows (one row per metal)."""
        TROY_OZ_TO_GRAMS = 31.1035
        metals = {}
        snapshot_date = ""
        timestamp = ""

        for row in rows:
            metal_id = row.get("metal", "")
            if not metal_id:
                continue

            snapshot_id = row.get("snapshot_id", "")
            if snapshot_id and not snapshot_date:
                snapshot_date = snapshot_id[:10]
                timestamp = snapshot_id

            price_usd = float(row.get("price_usd", 0))
            price_inr = float(row["price_inr"]) if row.get("price_inr") else None
            usd_to_inr = float(row["usd_to_inr"]) if row.get("usd_to_inr") else None
            confidence = row.get("confidence", "low")
            source_count = int(row.get("sources_count", 0))
            spread_pct = float(row["spread_percent"]) if row.get("spread_percent") else None

            # Read Indian market prices from DB (set by consolidator from RapidAPI city averages)
            price_22k_inr = float(row["price_22k_inr"]) if row.get("price_22k_inr") else None
            price_24k_inr = float(row["price_24k_inr"]) if row.get("price_24k_inr") else None

            # Fallback: derive from international spot (only when RapidAPI data is absent)
            if metal_id == "gold" and price_inr and not price_22k_inr:
                price_24k_per_gram = price_inr / TROY_OZ_TO_GRAMS
                price_22k_inr = round(price_24k_per_gram * 22 / 24, 2)
                price_24k_inr = round(price_24k_per_gram, 2)

            city_rates = row.get("city_rates") or None

            metals[metal_id] = MetalPrice(
                metal=metal_id,
                price_usd=price_usd,
                price_inr=price_inr,
                inr_rate=usd_to_inr,
                confidence=confidence,
                source_count=source_count,
                spread_pct=spread_pct,
                price_22k_inr=price_22k_inr,
                price_24k_inr=price_24k_inr,
                city_rates=city_rates,
            )

        return cls(snapshot_date=snapshot_date, timestamp=timestamp, metals=metals)

    @classmethod
    def from_dynamo(cls, item: dict) -> "PriceSnapshot":
        """Legacy: build from a single nested snapshot item."""
        metals = {}
        for key, val in item.items():
            if key in ("snapshot_date", "timestamp"):
                continue
            if isinstance(val, dict) and "price_usd" in val:
                metals[key] = MetalPrice(
                    metal=key,
                    price_usd=float(val.get("price_usd", 0)),
                    price_inr=float(val["price_inr"]) if val.get("price_inr") else None,
                    inr_rate=float(val["inr_rate"]) if val.get("inr_rate") else None,
                    confidence=val.get("confidence", "low"),
                    source_count=int(val.get("source_count", 0)),
                    spread_pct=float(val["spread_pct"]) if val.get("spread_pct") else None,
                    price_22k_inr=float(val["price_22k_inr"]) if val.get("price_22k_inr") else None,
                    price_24k_inr=float(val["price_24k_inr"]) if val.get("price_24k_inr") else None,
                    city_rates=val.get("city_rates"),
                    karat_prices=val.get("karat_prices"),
                )
        return cls(
            snapshot_date=item.get("snapshot_date", ""),
            timestamp=item.get("timestamp", ""),
            metals=metals,
        )
