from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone


@dataclass
class AlertPreference:
    phone_number: str
    metal: str               # gold | silver | platinum
    direction: str           # below | above
    threshold_inr: float     # price per gram in INR
    karat: str = "22K"
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_triggered: Optional[str] = None
    trigger_count: int = 0

    @property
    def alert_id(self) -> str:
        return f"{self.phone_number}#{self.metal}#{self.direction}"

    def to_dynamo(self) -> dict:
        return {
            "phone_number": self.phone_number,
            "alert_id": self.alert_id,
            "metal": self.metal,
            "direction": self.direction,
            "threshold_inr": str(self.threshold_inr),
            "karat": self.karat,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "last_triggered": self.last_triggered or "",
            "trigger_count": self.trigger_count,
        }

    @classmethod
    def from_dynamo(cls, item: dict) -> "AlertPreference":
        return cls(
            phone_number=item["phone_number"],
            metal=item["metal"],
            direction=item["direction"],
            threshold_inr=float(item["threshold_inr"]),
            karat=item.get("karat", "22K"),
            is_active=item.get("is_active", True),
            created_at=item.get("created_at", ""),
            last_triggered=item.get("last_triggered") or None,
            trigger_count=int(item.get("trigger_count", 0)),
        )
