"""Models for the single-asset research pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from onecool_os.research.pipeline.validation import parse_bool
from onecool_os.research.pipeline.validation import parse_datetime
from onecool_os.research.pipeline.validation import parse_dict
from onecool_os.research.pipeline.validation import parse_enum
from onecool_os.research.pipeline.validation import parse_non_negative_int
from onecool_os.research.pipeline.validation import parse_string_tuple
from onecool_os.research.pipeline.validation import parse_url
from onecool_os.research.pipeline.validation import require_text


class PipelineStatus(StrEnum):
    """Single asset pipeline status."""

    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class SingleAssetPipelineRequest:
    """One immutable single-asset pipeline request."""

    pipeline_id: str
    asset_id: str
    cert_number: str
    asset_name: str
    ebay_sold_search_url: str
    research_request_id: str
    reference_datetime: datetime | str
    created_at: datetime | str
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "pipeline_id", require_text(self.pipeline_id, "pipeline_id"))
        object.__setattr__(self, "asset_id", require_text(self.asset_id, "asset_id"))
        object.__setattr__(self, "cert_number", require_text(self.cert_number, "cert_number"))
        object.__setattr__(self, "asset_name", require_text(self.asset_name, "asset_name"))
        object.__setattr__(self, "ebay_sold_search_url", parse_url(self.ebay_sold_search_url, "ebay_sold_search_url"))
        object.__setattr__(
            self,
            "research_request_id",
            require_text(self.research_request_id, "research_request_id"),
        )
        object.__setattr__(self, "reference_datetime", parse_datetime(self.reference_datetime, "reference_datetime"))
        object.__setattr__(self, "created_at", parse_datetime(self.created_at, "created_at"))
        object.__setattr__(self, "metadata", parse_dict(self.metadata, "metadata"))

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe request data."""

        return {
            "pipeline_id": self.pipeline_id,
            "asset_id": self.asset_id,
            "cert_number": self.cert_number,
            "asset_name": self.asset_name,
            "ebay_sold_search_url": self.ebay_sold_search_url,
            "research_request_id": self.research_request_id,
            "reference_datetime": self.reference_datetime.isoformat(),
            "created_at": self.created_at.isoformat(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SingleAssetPipelineResult:
    """Deterministic result of a single-asset research pipeline run."""

    pipeline_id: str
    asset_id: str
    cert_number: str
    asset_name: str
    request_exported: bool
    provider_result_loaded: bool
    orf_validation_passed: bool
    evidence_records_created: int
    verified_evidence_count: int
    review_required_count: int
    rejected_count: int
    no_match_count: int
    runtime_attachment_completed: bool
    warnings: tuple[str, ...] | list[str]
    status: PipelineStatus | str
    generated_at: datetime | str
    reference_datetime: datetime | str

    def __post_init__(self) -> None:
        for field_name in ("pipeline_id", "asset_id", "cert_number", "asset_name"):
            object.__setattr__(self, field_name, require_text(getattr(self, field_name), field_name))
        for field_name in (
            "request_exported",
            "provider_result_loaded",
            "orf_validation_passed",
            "runtime_attachment_completed",
        ):
            object.__setattr__(self, field_name, parse_bool(getattr(self, field_name), field_name))
        for field_name in (
            "evidence_records_created",
            "verified_evidence_count",
            "review_required_count",
            "rejected_count",
            "no_match_count",
        ):
            object.__setattr__(self, field_name, parse_non_negative_int(getattr(self, field_name), field_name))
        object.__setattr__(self, "warnings", parse_string_tuple(self.warnings, "warnings"))
        object.__setattr__(self, "status", parse_enum(PipelineStatus, self.status, "status"))
        object.__setattr__(self, "generated_at", parse_datetime(self.generated_at, "generated_at"))
        object.__setattr__(self, "reference_datetime", parse_datetime(self.reference_datetime, "reference_datetime"))

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe result data."""

        return {
            "pipeline_id": self.pipeline_id,
            "asset_id": self.asset_id,
            "cert_number": self.cert_number,
            "asset_name": self.asset_name,
            "request_exported": self.request_exported,
            "provider_result_loaded": self.provider_result_loaded,
            "orf_validation_passed": self.orf_validation_passed,
            "evidence_records_created": self.evidence_records_created,
            "verified_evidence_count": self.verified_evidence_count,
            "review_required_count": self.review_required_count,
            "rejected_count": self.rejected_count,
            "no_match_count": self.no_match_count,
            "runtime_attachment_completed": self.runtime_attachment_completed,
            "warnings": list(self.warnings),
            "status": self.status.value,
            "generated_at": self.generated_at.isoformat(),
            "reference_datetime": self.reference_datetime.isoformat(),
        }


@dataclass(frozen=True)
class SingleAssetPipelineOutcome:
    """Pipeline execution output with the updated runtime session."""

    request: SingleAssetPipelineRequest | None
    result: SingleAssetPipelineResult
    runtime_session: Any
    request_output_path: str | None = None
    provider_result_path: str | None = None
