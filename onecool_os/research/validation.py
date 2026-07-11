"""Validation helpers for the Onecool Research Framework."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation
import re
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse

from onecool_os.core.exceptions import OnecoolOSError
from onecool_os.research.enums import ResearchCapability
from onecool_os.research.enums import ResearchConfidence
from onecool_os.research.enums import ResearchProviderType
from onecool_os.research.enums import ResearchStatus
from onecool_os.research.enums import ResearchType

_VERSION_RE = re.compile(r"^v?\d+(?:\.\d+){0,2}(?:[-.][A-Za-z0-9]+)?$")


class ResearchError(OnecoolOSError):
    """Raised when research framework data is invalid."""


@dataclass(frozen=True)
class ResearchValidationIssue:
    """One deterministic validation issue."""

    field: str
    message: str


@dataclass(frozen=True)
class ResearchValidationResult:
    """Validation output that does not mutate the source object."""

    valid: bool
    issues: tuple[ResearchValidationIssue, ...] = ()


def require_text(value: Any, field_name: str) -> str:
    """Return a stripped non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise ResearchError(f"{field_name} must be a non-empty string.")
    return value.strip()


def optional_text(value: Any, field_name: str) -> str | None:
    """Return a stripped optional string."""

    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ResearchError(f"{field_name} must be a string.")
    return value.strip() or None


def parse_enum(
    enum_class: type[StrEnum],
    value: Any,
    field_name: str,
) -> StrEnum:
    """Parse a StrEnum from a case-insensitive string."""

    try:
        return enum_class(str(value).upper())
    except ValueError as exc:
        raise ResearchError(f"Invalid {field_name}: {value}") from exc


def parse_enum_tuple(
    enum_class: type[StrEnum],
    value: Any,
    field_name: str,
) -> tuple[StrEnum, ...]:
    """Parse a list of StrEnum values."""

    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise ResearchError(f"{field_name} must be a list.")
    return tuple(parse_enum(enum_class, item, field_name) for item in value)


def parse_string_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    """Parse a list/tuple of strings."""

    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise ResearchError(f"{field_name} must be a list.")
    return tuple(require_text(item, field_name) for item in value)


def parse_dict(value: Any, field_name: str) -> dict[str, Any]:
    """Parse an optional metadata dictionary."""

    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ResearchError(f"{field_name} must be a dictionary.")
    return dict(value)


def parse_date(value: Any, field_name: str) -> date:
    """Parse an ISO date."""

    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ResearchError(f"Invalid {field_name}: {value}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ResearchError(f"Invalid {field_name}: {value}") from exc


def parse_optional_date(value: Any, field_name: str) -> date | None:
    """Parse an optional ISO date."""

    if value in (None, ""):
        return None
    return parse_date(value, field_name)


def parse_datetime(value: Any, field_name: str) -> datetime:
    """Parse an ISO datetime."""

    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ResearchError(f"Invalid {field_name}: {value}")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ResearchError(f"Invalid {field_name}: {value}") from exc


def parse_optional_datetime(value: Any, field_name: str) -> datetime | None:
    """Parse an optional ISO datetime."""

    if value in (None, ""):
        return None
    return parse_datetime(value, field_name)


def parse_optional_decimal(value: Any, field_name: str) -> Decimal | None:
    """Parse an optional non-negative Decimal."""

    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ResearchError(f"Invalid {field_name}: {value}") from exc
    if not parsed.is_finite() or parsed < Decimal("0"):
        raise ResearchError(f"Invalid {field_name}: {value}")
    return parsed


def parse_optional_bool(value: Any, field_name: str) -> bool | None:
    """Parse an optional boolean."""

    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    raise ResearchError(f"{field_name} must be a boolean.")


def require_currency(value: Any) -> str:
    """Return an uppercase ISO-like three-letter currency code."""

    currency = require_text(value, "currency").upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ResearchError(f"Invalid currency: {value}")
    return currency


def parse_optional_currency(value: Any) -> str | None:
    """Parse an optional currency code."""

    if value in (None, ""):
        return None
    return require_currency(value)


def parse_optional_url(value: Any, field_name: str) -> str | None:
    """Parse an optional HTTP(S) URL."""

    url = optional_text(value, field_name)
    if url is None:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ResearchError(f"Invalid {field_name}: {value}")
    return url


def validate_provider_version(provider_version: str) -> str:
    """Validate provider version format."""

    version = require_text(provider_version, "provider_version")
    if not _VERSION_RE.fullmatch(version):
        raise ResearchError(f"Invalid provider_version: {provider_version}")
    return version


def validate_research_result(result: Any) -> ResearchValidationResult:
    """Validate a ResearchResult-like object without mutating it."""

    issues: list[ResearchValidationIssue] = []
    _issue_if_missing(issues, result.provider_name, "provider_name")
    _issue_if_missing(issues, result.provider_version, "provider_version")
    if not result.provider_metadata:
        issues.append(
            ResearchValidationIssue(
                "provider_metadata",
                "provider_metadata is required.",
            )
        )
    try:
        parse_enum(ResearchProviderType, result.provider_type, "provider_type")
        parse_enum(ResearchType, result.research_type, "research_type")
        parse_enum(ResearchStatus, result.status, "status")
        parse_enum(ResearchConfidence, result.confidence, "confidence")
        for capability in result.capabilities:
            parse_enum(ResearchCapability, capability, "capabilities")
        validate_provider_version(result.provider_version)
    except ResearchError as exc:
        issues.append(ResearchValidationIssue("enum", str(exc)))

    evidence_ids: set[str] = set()
    trusted_evidence_count = 0
    for evidence in result.evidence:
        if evidence.evidence_id in evidence_ids:
            issues.append(
                ResearchValidationIssue(
                    "evidence",
                    f"Duplicate evidence_id: {evidence.evidence_id}",
                )
            )
        evidence_ids.add(evidence.evidence_id)
        if evidence.status == ResearchStatus.COMPLETED:
            trusted_evidence_count += 1
        if evidence.source_url:
            try:
                parse_optional_url(evidence.source_url, "source_url")
            except ResearchError as exc:
                issues.append(ResearchValidationIssue("source_url", str(exc)))

    if result.status == ResearchStatus.PARTIAL and not result.warnings:
        issues.append(
            ResearchValidationIssue(
                "warnings",
                "PARTIAL results must carry warnings.",
            )
        )
    if result.status in {ResearchStatus.FAILED, ResearchStatus.NO_MATCH} and trusted_evidence_count:
        issues.append(
            ResearchValidationIssue(
                "evidence",
                "FAILED and NO_MATCH results must not contain trusted evidence.",
            )
        )
    return ResearchValidationResult(not issues, tuple(issues))


def ensure_valid_research_result(result: Any) -> None:
    """Raise ResearchError if a ResearchResult-like object is invalid."""

    validation = validate_research_result(result)
    if not validation.valid:
        messages = "; ".join(issue.message for issue in validation.issues)
        raise ResearchError(messages)


def _issue_if_missing(
    issues: list[ResearchValidationIssue],
    value: Any,
    field_name: str,
) -> None:
    if not isinstance(value, str) or not value.strip():
        issues.append(
            ResearchValidationIssue(
                field_name,
                f"{field_name} is required.",
            )
        )
