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
    def from_dynamo(cls, item: dict) -> "PriceSnapshot":
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
