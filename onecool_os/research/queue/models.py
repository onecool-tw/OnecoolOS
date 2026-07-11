"""Immutable Research Queue models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from onecool_os.research.enums import ResearchCapability
from onecool_os.research.enums import ResearchType
from onecool_os.research.queue.enums import ResearchQueuePriority
from onecool_os.research.queue.enums import ResearchQueueReason
from onecool_os.research.queue.enums import ResearchQueueStatus
from onecool_os.research.queue.validation import parse_dict
from onecool_os.research.queue.validation import parse_enum
from onecool_os.research.queue.validation import parse_enum_tuple
from onecool_os.research.queue.validation import parse_non_negative_int
from onecool_os.research.queue.validation import parse_optional_datetime
from onecool_os.research.queue.validation import parse_optional_url
from onecool_os.research.queue.validation import parse_string_tuple
from onecool_os.research.queue.validation import require_text
from onecool_os.research.validation import parse_optional_date


@dataclass(frozen=True)
class ResearchQueueItem:
    """One deterministic research work item."""

    queue_item_id: str
    asset_id: str
    asset_name: str
    priority: ResearchQueuePriority | str
    status: ResearchQueueStatus | str
    reasons: tuple[ResearchQueueReason | str, ...] | list[ResearchQueueReason | str]
    research_type: ResearchType | str
    provider_capability_required: ResearchCapability | str
    blocking_reasons: tuple[str, ...] | list[str]
    current_evidence_count: int
    verified_evidence_count: int
    review_evidence_count: int
    rejected_evidence_count: int
    valuation_coverage_status: str
    cert_number: str | None = None
    source_url: str | None = None
    latest_valuation_date: Any = None
    last_research_date: datetime | str | None = None
    metadata: dict[str, Any] | None = None
    warnings: tuple[str, ...] | list[str] = ()
    created_at: datetime | str | None = None
    reference_datetime: datetime | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "queue_item_id", require_text(self.queue_item_id, "queue_item_id"))
        object.__setattr__(self, "asset_id", require_text(self.asset_id, "asset_id"))
        object.__setattr__(self, "cert_number", _optional_text(self.cert_number))
        object.__setattr__(self, "asset_name", require_text(self.asset_name, "asset_name"))
        object.__setattr__(
            self,
            "priority",
            parse_enum(ResearchQueuePriority, self.priority, "priority"),
        )
        object.__setattr__(
            self,
            "status",
            parse_enum(ResearchQueueStatus, self.status, "status"),
        )
        object.__setattr__(
            self,
            "reasons",
            parse_enum_tuple(ResearchQueueReason, self.reasons, "reasons"),
        )
        object.__setattr__(self, "research_type", parse_enum(ResearchType, self.research_type, "research_type"))
        object.__setattr__(self, "source_url", parse_optional_url(self.source_url, "source_url"))
        object.__setattr__(
            self,
            "provider_capability_required",
            parse_enum(ResearchCapability, self.provider_capability_required, "provider_capability_required"),
        )
        object.__setattr__(self, "blocking_reasons", parse_string_tuple(self.blocking_reasons, "blocking_reasons"))
        for field_name in (
            "current_evidence_count",
            "verified_evidence_count",
            "review_evidence_count",
            "rejected_evidence_count",
        ):
            object.__setattr__(self, field_name, parse_non_negative_int(getattr(self, field_name), field_name))
        object.__setattr__(self, "valuation_coverage_status", require_text(self.valuation_coverage_status, "valuation_coverage_status"))
        object.__setattr__(self, "latest_valuation_date", parse_optional_date(self.latest_valuation_date, "latest_valuation_date"))
        object.__setattr__(self, "last_research_date", parse_optional_datetime(self.last_research_date, "last_research_date"))
        object.__setattr__(self, "metadata", parse_dict(self.metadata, "metadata"))
        object.__setattr__(self, "warnings", parse_string_tuple(self.warnings, "warnings"))
        object.__setattr__(self, "created_at", parse_optional_datetime(self.created_at, "created_at"))
        object.__setattr__(self, "reference_datetime", parse_optional_datetime(self.reference_datetime, "reference_datetime"))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe queue item."""

        return {
            "queue_item_id": self.queue_item_id,
            "asset_id": self.asset_id,
            "cert_number": self.cert_number,
            "asset_name": self.asset_name,
            "priority": self.priority.value,
            "status": self.status.value,
            "reasons": [reason.value for reason in self.reasons],
            "research_type": self.research_type.value,
            "source_url": self.source_url,
            "provider_capability_required": self.provider_capability_required.value,
            "blocking_reasons": list(self.blocking_reasons),
            "current_evidence_count": self.current_evidence_count,
            "verified_evidence_count": self.verified_evidence_count,
            "review_evidence_count": self.review_evidence_count,
            "rejected_evidence_count": self.rejected_evidence_count,
            "valuation_coverage_status": self.valuation_coverage_status,
            "latest_valuation_date": self.latest_valuation_date.isoformat() if self.latest_valuation_date else None,
            "last_research_date": self.last_research_date.isoformat() if self.last_research_date else None,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reference_datetime": self.reference_datetime.isoformat() if self.reference_datetime else None,
        }


@dataclass(frozen=True)
class ResearchQueueSnapshot:
    """A deterministic Research Queue snapshot."""

    snapshot_id: str
    reference_datetime: datetime
    total_assets: int
    total_queue_items: int
    critical_items: int
    high_items: int
    medium_items: int
    low_items: int
    informational_items: int
    ready_items: int
    blocked_items: int
    completed_items: int
    items: tuple[ResearchQueueItem, ...] | list[ResearchQueueItem]
    warnings: tuple[str, ...] | list[str] = ()
    generated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "snapshot_id", require_text(self.snapshot_id, "snapshot_id"))
        if not isinstance(self.reference_datetime, datetime):
            raise TypeError("reference_datetime must be a datetime.")
        for field_name in (
            "total_assets",
            "total_queue_items",
            "critical_items",
            "high_items",
            "medium_items",
            "low_items",
            "informational_items",
            "ready_items",
            "blocked_items",
            "completed_items",
        ):
            object.__setattr__(self, field_name, parse_non_negative_int(getattr(self, field_name), field_name))
        object.__setattr__(self, "items", tuple(self.items))
        object.__setattr__(self, "warnings", parse_string_tuple(self.warnings, "warnings"))
        if self.generated_at is not None and not isinstance(self.generated_at, datetime):
            raise TypeError("generated_at must be a datetime.")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe snapshot."""

        return {
            "snapshot_id": self.snapshot_id,
            "reference_datetime": self.reference_datetime.isoformat(),
            "total_assets": self.total_assets,
            "total_queue_items": self.total_queue_items,
            "critical_items": self.critical_items,
            "high_items": self.high_items,
            "medium_items": self.medium_items,
            "low_items": self.low_items,
            "informational_items": self.informational_items,
            "ready_items": self.ready_items,
            "blocked_items": self.blocked_items,
            "completed_items": self.completed_items,
            "items": [item.to_dict() for item in self.items],
            "warnings": list(self.warnings),
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }


def _optional_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None
