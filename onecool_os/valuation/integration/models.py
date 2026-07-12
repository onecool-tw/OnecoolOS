"""Models for Fair Value to ValuationRecord integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from onecool_os.valuation.enums import ValuationSource
from onecool_os.valuation.models import ValuationRecord
from onecool_os.valuation.validation import parse_enum
from onecool_os.valuation.validation import require_text


class RuntimeValuationStatus(StrEnum):
    """Runtime status for source-specific valuation creation."""

    CREATED = "CREATED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class FairValueValuationMapping:
    """Trusted Fair Value mapping plus its canonical ValuationRecord."""

    valuation_record: ValuationRecord
    valuation_record_id: str
    asset_id: str
    cert_number: str | None
    valuation_source: ValuationSource | str
    market_value: Decimal
    currency: str
    confidence: str
    evidence_quality_score: Decimal
    latest_sold_date: Any
    sample_count: int
    freshness_status: str
    liquidity: str
    warnings: tuple[str, ...]
    reference_datetime: datetime
    generated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "valuation_record_id", require_text(self.valuation_record_id, "valuation_record_id"))
        object.__setattr__(self, "asset_id", require_text(self.asset_id, "asset_id"))
        object.__setattr__(
            self,
            "valuation_source",
            parse_enum(ValuationSource, self.valuation_source, "valuation_source"),
        )
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe mapping."""

        return {
            "valuation_record_id": self.valuation_record_id,
            "asset_id": self.asset_id,
            "cert_number": self.cert_number,
            "valuation_source": self.valuation_source.value,
            "market_value": str(self.market_value),
            "currency": self.currency,
            "confidence": self.confidence,
            "evidence_quality_score": str(self.evidence_quality_score),
            "latest_sold_date": self.latest_sold_date.isoformat() if self.latest_sold_date else None,
            "sample_count": self.sample_count,
            "freshness_status": self.freshness_status,
            "liquidity": self.liquidity,
            "warnings": list(self.warnings),
            "reference_datetime": self.reference_datetime.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "valuation_record": self.valuation_record.to_dict(),
        }


@dataclass(frozen=True)
class RuntimeValuationPlaceholder:
    """Runtime status when a trusted valuation cannot be created."""

    asset_id: str
    cert_number: str | None
    valuation_source: ValuationSource | str
    status: RuntimeValuationStatus | str
    warnings: tuple[str, ...]
    reference_datetime: datetime
    generated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_id", require_text(self.asset_id, "asset_id"))
        object.__setattr__(
            self,
            "valuation_source",
            parse_enum(ValuationSource, self.valuation_source, "valuation_source"),
        )
        object.__setattr__(
            self,
            "status",
            parse_enum(RuntimeValuationStatus, self.status, "status"),
        )
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe placeholder."""

        return {
            "asset_id": self.asset_id,
            "cert_number": self.cert_number,
            "valuation_source": self.valuation_source.value,
            "status": self.status.value,
            "warnings": list(self.warnings),
            "reference_datetime": self.reference_datetime.isoformat(),
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass(frozen=True)
class FairValueValuationIntegrationResult:
    """Result of converting Fair Value snapshots into runtime valuations."""

    valuation_records: tuple[ValuationRecord, ...]
    mappings: tuple[FairValueValuationMapping, ...]
    placeholders: tuple[RuntimeValuationPlaceholder, ...]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "valuation_records", tuple(self.valuation_records))
        object.__setattr__(self, "mappings", tuple(self.mappings))
        object.__setattr__(self, "placeholders", tuple(self.placeholders))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe integration result."""

        return {
            "valuation_records": [record.to_dict() for record in self.valuation_records],
            "mappings": [mapping.to_dict() for mapping in self.mappings],
            "placeholders": [placeholder.to_dict() for placeholder in self.placeholders],
            "warnings": list(self.warnings),
        }
