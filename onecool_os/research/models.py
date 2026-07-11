"""Immutable public models for the Onecool Research Framework."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any

from onecool_os.research.enums import ResearchCapability
from onecool_os.research.enums import ResearchConfidence
from onecool_os.research.enums import ResearchProviderType
from onecool_os.research.enums import ResearchStatus
from onecool_os.research.enums import ResearchType
from onecool_os.research.validation import optional_text
from onecool_os.research.validation import parse_dict
from onecool_os.research.validation import parse_enum
from onecool_os.research.validation import parse_enum_tuple
from onecool_os.research.validation import parse_optional_bool
from onecool_os.research.validation import parse_optional_currency
from onecool_os.research.validation import parse_optional_date
from onecool_os.research.validation import parse_optional_datetime
from onecool_os.research.validation import parse_optional_decimal
from onecool_os.research.validation import parse_optional_url
from onecool_os.research.validation import parse_string_tuple
from onecool_os.research.validation import require_text
from onecool_os.research.validation import validate_provider_version


@dataclass(frozen=True)
class ResearchRequest:
    """A provider-independent research request."""

    request_id: str
    research_type: ResearchType | str
    asset_id: str | None = None
    cert_number: str | None = None
    provider_name: str | None = None
    query: str | None = None
    source_url: str | None = None
    requested_fields: tuple[str, ...] | list[str] = ()
    reference_datetime: datetime | str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", require_text(self.request_id, "request_id"))
        object.__setattr__(self, "research_type", parse_enum(ResearchType, self.research_type, "research_type"))
        object.__setattr__(self, "asset_id", optional_text(self.asset_id, "asset_id"))
        object.__setattr__(self, "cert_number", optional_text(self.cert_number, "cert_number"))
        object.__setattr__(self, "provider_name", optional_text(self.provider_name, "provider_name"))
        object.__setattr__(self, "query", optional_text(self.query, "query"))
        object.__setattr__(self, "source_url", parse_optional_url(self.source_url, "source_url"))
        object.__setattr__(self, "requested_fields", parse_string_tuple(self.requested_fields, "requested_fields"))
        object.__setattr__(
            self,
            "reference_datetime",
            parse_optional_datetime(self.reference_datetime, "reference_datetime"),
        )
        object.__setattr__(self, "metadata", parse_dict(self.metadata, "metadata"))
        object.__setattr__(self, "created_at", parse_optional_datetime(self.created_at, "created_at"))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "request_id": self.request_id,
            "research_type": self.research_type.value,
            "asset_id": self.asset_id,
            "cert_number": self.cert_number,
            "provider_name": self.provider_name,
            "query": self.query,
            "source_url": self.source_url,
            "requested_fields": list(self.requested_fields),
            "reference_datetime": _format_datetime(self.reference_datetime),
            "metadata": dict(self.metadata),
            "created_at": _format_datetime(self.created_at),
        }


@dataclass(frozen=True)
class ResearchEvidence:
    """One normalized provider observation."""

    evidence_id: str
    evidence_type: ResearchType | str
    source_name: str
    source_url: str | None = None
    item_id: str | None = None
    observed_value: Decimal | str | int | float | None = None
    currency: str | None = None
    observed_date: date | str | None = None
    title: str | None = None
    exact_match: bool | None = None
    matched_fields: tuple[str, ...] | list[str] = ()
    mismatched_fields: tuple[str, ...] | list[str] = ()
    confidence: ResearchConfidence | str = ResearchConfidence.UNVERIFIED
    status: ResearchStatus | str = ResearchStatus.NEEDS_REVIEW
    warnings: tuple[str, ...] | list[str] = ()
    raw_metadata: dict[str, Any] | None = None
    created_at: datetime | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", require_text(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "evidence_type", parse_enum(ResearchType, self.evidence_type, "evidence_type"))
        object.__setattr__(self, "source_name", require_text(self.source_name, "source_name"))
        object.__setattr__(self, "source_url", parse_optional_url(self.source_url, "source_url"))
        object.__setattr__(self, "item_id", optional_text(self.item_id, "item_id"))
        object.__setattr__(self, "observed_value", parse_optional_decimal(self.observed_value, "observed_value"))
        object.__setattr__(self, "currency", parse_optional_currency(self.currency))
        object.__setattr__(self, "observed_date", parse_optional_date(self.observed_date, "observed_date"))
        object.__setattr__(self, "title", optional_text(self.title, "title"))
        object.__setattr__(self, "exact_match", parse_optional_bool(self.exact_match, "exact_match"))
        object.__setattr__(self, "matched_fields", _normalize_fields(self.matched_fields, "matched_fields"))
        object.__setattr__(self, "mismatched_fields", _normalize_fields(self.mismatched_fields, "mismatched_fields"))
        object.__setattr__(self, "confidence", parse_enum(ResearchConfidence, self.confidence, "confidence"))
        object.__setattr__(self, "status", parse_enum(ResearchStatus, self.status, "status"))
        object.__setattr__(self, "warnings", parse_string_tuple(self.warnings, "warnings"))
        object.__setattr__(self, "raw_metadata", parse_dict(self.raw_metadata, "raw_metadata"))
        object.__setattr__(self, "created_at", parse_optional_datetime(self.created_at, "created_at"))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type.value,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "item_id": self.item_id,
            "observed_value": _format_decimal(self.observed_value),
            "currency": self.currency,
            "observed_date": _format_date(self.observed_date),
            "title": self.title,
            "exact_match": self.exact_match,
            "matched_fields": list(self.matched_fields),
            "mismatched_fields": list(self.mismatched_fields),
            "confidence": self.confidence.value,
            "status": self.status.value,
            "warnings": list(self.warnings),
            "raw_metadata": dict(self.raw_metadata),
            "created_at": _format_datetime(self.created_at),
        }


@dataclass(frozen=True)
class ResearchResult:
    """A normalized provider research result."""

    result_id: str
    request_id: str
    provider_name: str
    provider_type: ResearchProviderType | str
    provider_version: str
    capabilities: tuple[ResearchCapability | str, ...] | list[ResearchCapability | str]
    research_type: ResearchType | str
    status: ResearchStatus | str
    confidence: ResearchConfidence | str
    evidence: tuple[ResearchEvidence | dict[str, Any], ...] | list[ResearchEvidence | dict[str, Any]]
    asset_id: str | None = None
    cert_number: str | None = None
    normalized_payload: dict[str, Any] | None = None
    warnings: tuple[str, ...] | list[str] = ()
    provider_metadata: dict[str, Any] | None = None
    generated_at: datetime | str | None = None
    reference_datetime: datetime | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "result_id", require_text(self.result_id, "result_id"))
        object.__setattr__(self, "request_id", require_text(self.request_id, "request_id"))
        object.__setattr__(self, "provider_name", require_text(self.provider_name, "provider_name"))
        object.__setattr__(self, "provider_type", parse_enum(ResearchProviderType, self.provider_type, "provider_type"))
        object.__setattr__(self, "provider_version", validate_provider_version(self.provider_version))
        object.__setattr__(self, "capabilities", parse_enum_tuple(ResearchCapability, self.capabilities, "capabilities"))
        object.__setattr__(self, "research_type", parse_enum(ResearchType, self.research_type, "research_type"))
        object.__setattr__(self, "asset_id", optional_text(self.asset_id, "asset_id"))
        object.__setattr__(self, "cert_number", optional_text(self.cert_number, "cert_number"))
        object.__setattr__(self, "status", parse_enum(ResearchStatus, self.status, "status"))
        object.__setattr__(self, "confidence", parse_enum(ResearchConfidence, self.confidence, "confidence"))
        object.__setattr__(self, "evidence", tuple(_coerce_evidence(item) for item in self.evidence))
        object.__setattr__(self, "normalized_payload", parse_dict(self.normalized_payload, "normalized_payload"))
        object.__setattr__(self, "warnings", parse_string_tuple(self.warnings, "warnings"))
        object.__setattr__(self, "provider_metadata", parse_dict(self.provider_metadata, "provider_metadata"))
        object.__setattr__(self, "generated_at", parse_optional_datetime(self.generated_at, "generated_at"))
        object.__setattr__(
            self,
            "reference_datetime",
            parse_optional_datetime(self.reference_datetime, "reference_datetime"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "result_id": self.result_id,
            "request_id": self.request_id,
            "provider_name": self.provider_name,
            "provider_type": self.provider_type.value,
            "provider_version": self.provider_version,
            "capabilities": [capability.value for capability in self.capabilities],
            "research_type": self.research_type.value,
            "asset_id": self.asset_id,
            "cert_number": self.cert_number,
            "status": self.status.value,
            "confidence": self.confidence.value,
            "evidence": [item.to_dict() for item in self.evidence],
            "normalized_payload": dict(self.normalized_payload),
            "warnings": list(self.warnings),
            "provider_metadata": dict(self.provider_metadata),
            "generated_at": _format_datetime(self.generated_at),
            "reference_datetime": _format_datetime(self.reference_datetime),
        }


@dataclass(frozen=True)
class ResearchBatch:
    """A deterministic group of normalized research results."""

    batch_id: str
    provider_name: str
    results: tuple[ResearchResult | dict[str, Any], ...] | list[ResearchResult | dict[str, Any]]
    warnings: tuple[str, ...] | list[str] = ()
    generated_at: datetime | str | None = None
    reference_datetime: datetime | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "batch_id", require_text(self.batch_id, "batch_id"))
        object.__setattr__(self, "provider_name", require_text(self.provider_name, "provider_name"))
        object.__setattr__(self, "results", tuple(_coerce_result(item) for item in self.results))
        object.__setattr__(self, "warnings", parse_string_tuple(self.warnings, "warnings"))
        object.__setattr__(self, "generated_at", parse_optional_datetime(self.generated_at, "generated_at"))
        object.__setattr__(
            self,
            "reference_datetime",
            parse_optional_datetime(self.reference_datetime, "reference_datetime"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "batch_id": self.batch_id,
            "provider_name": self.provider_name,
            "results": [item.to_dict() for item in self.results],
            "warnings": list(self.warnings),
            "generated_at": _format_datetime(self.generated_at),
            "reference_datetime": _format_datetime(self.reference_datetime),
        }


def _coerce_evidence(item: ResearchEvidence | dict[str, Any]) -> ResearchEvidence:
    if isinstance(item, ResearchEvidence):
        return item
    if isinstance(item, dict):
        return ResearchEvidence(**item)
    raise TypeError("evidence items must be dictionaries or ResearchEvidence.")


def _coerce_result(item: ResearchResult | dict[str, Any]) -> ResearchResult:
    if isinstance(item, ResearchResult):
        return item
    if isinstance(item, dict):
        return ResearchResult(**item)
    raise TypeError("results must be dictionaries or ResearchResult.")


def _normalize_fields(value: Any, field_name: str) -> tuple[str, ...]:
    return tuple(field.strip().upper() for field in parse_string_tuple(value, field_name))


def _format_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}"


def _format_date(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
