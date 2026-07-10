"""Collection synchronization report models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


DIFFERENCE_TYPES = frozenset(
    {
        "NEW_CARD",
        "MISSING_IN_IMPORT",
        "MISSING_IN_ASSET_MASTER",
        "DUPLICATE_CERT",
        "DUPLICATE_ASSET",
        "GRADE_CHANGED",
        "GRADE_ISSUER_CHANGED",
        "VARIETY_CHANGED",
        "COST_OVERRIDE",
        "EBAY_URL_MISSING",
        "PSA_URL_MISSING",
        "TARGET_PRICE_MISSING",
        "NOTES_CHANGED",
    }
)
SYNC_SEVERITIES = frozenset(("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"))


@dataclass(frozen=True)
class CollectionDifference:
    """One deterministic difference found during collection sync."""

    cert_number: str
    difference_type: str
    severity: str
    source_value: Any
    target_value: Any
    description: str
    asset_id: str | None = None

    def __post_init__(self) -> None:
        if self.difference_type not in DIFFERENCE_TYPES:
            raise ValueError(f"Invalid difference_type: {self.difference_type}")
        if self.severity not in SYNC_SEVERITIES:
            raise ValueError(f"Invalid severity: {self.severity}")
        object.__setattr__(self, "cert_number", str(self.cert_number or ""))
        object.__setattr__(self, "asset_id", _optional_text(self.asset_id))
        object.__setattr__(self, "description", str(self.description))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary."""

        return {
            "cert_number": self.cert_number,
            "asset_id": self.asset_id,
            "difference_type": self.difference_type,
            "severity": self.severity,
            "source_value": self.source_value,
            "target_value": self.target_value,
            "description": self.description,
        }


@dataclass(frozen=True)
class SyncReport:
    """Deterministic collection synchronization report."""

    imported_records: int
    asset_master_records: int
    matched_records: int
    differences: tuple[CollectionDifference, ...]
    warnings: tuple[str, ...]
    collection_health: int
    generated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.generated_at, datetime):
            raise ValueError("generated_at must be a datetime.")
        object.__setattr__(self, "differences", tuple(self.differences))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(
            self,
            "collection_health",
            max(0, min(100, int(self.collection_health))),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary."""

        return {
            "imported_records": self.imported_records,
            "asset_master_records": self.asset_master_records,
            "matched_records": self.matched_records,
            "differences": [
                difference.to_dict() for difference in self.differences
            ],
            "warnings": list(self.warnings),
            "collection_health": self.collection_health,
            "generated_at": self.generated_at.isoformat(),
        }


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
