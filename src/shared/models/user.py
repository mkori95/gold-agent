from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone


@dataclass
class User:
    phone_number: str           # E.164 format: +919876543210
    language: str = "en"        # en | hi | ta | te
    city: Optional[str] = None  # e.g. "Chennai", "Mumbai"
    name: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message_count: int = 0
    is_active: bool = True
    daily_summary: bool = False

    def to_dynamo(self) -> dict:
        return {
            "phone_number": self.phone_number,
            "language": self.language,
            "city": self.city or "",
            "name": self.name or "",
            "created_at": self.created_at,
            "last_seen": self.last_seen,
            "message_count": self.message_count,
            "is_active": self.is_active,
            "daily_summary": self.daily_summary,
        }

    @classmethod
    def from_dynamo(cls, item: dict) -> "User":
        return cls(
            phone_number=item["phone_number"],
            language=item.get("language", "en"),
            city=item.get("city") or None,
            name=item.get("name") or None,
            created_at=item.get("created_at", ""),
            last_seen=item.get("last_seen", ""),
            message_count=int(item.get("message_count", 0)),
            is_active=item.get("is_active", True),
            daily_summary=bool(item.get("daily_summary", False)),
        )
