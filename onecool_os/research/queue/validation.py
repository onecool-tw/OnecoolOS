"""Validation helpers for the Research Queue."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse

from onecool_os.core.exceptions import OnecoolOSError


class ResearchQueueError(OnecoolOSError):
    """Raised when Research Queue data is invalid."""


@dataclass(frozen=True)
class ResearchQueueValidationIssue:
    """One deterministic Research Queue validation issue."""

    field: str
    message: str


@dataclass(frozen=True)
class ResearchQueueValidationResult:
    """Validation output that does not mutate queue objects."""

    valid: bool
    issues: tuple[ResearchQueueValidationIssue, ...] = ()


def validate_research_queue_snapshot(snapshot: Any) -> ResearchQueueValidationResult:
    """Validate queue-level invariants without mutating the snapshot."""

    from onecool_os.research.queue.enums import ResearchQueueStatus

    issues: list[ResearchQueueValidationIssue] = []
    seen_item_ids: set[str] = set()
    seen_open_keys: set[tuple[str, str]] = set()
    for item in getattr(snapshot, "items", ()):
        if item.queue_item_id in seen_item_ids:
            issues.append(
                ResearchQueueValidationIssue(
                    "queue_item_id",
                    f"Duplicate queue_item_id: {item.queue_item_id}",
                )
            )
        seen_item_ids.add(item.queue_item_id)

        if item.status == ResearchQueueStatus.READY and item.blocking_reasons:
            issues.append(
                ResearchQueueValidationIssue(
                    "status",
                    f"READY item has blocking reasons: {item.queue_item_id}",
                )
            )
        if item.status == ResearchQueueStatus.BLOCKED and not item.blocking_reasons:
            issues.append(
                ResearchQueueValidationIssue(
                    "status",
                    f"BLOCKED item has no blocking reason: {item.queue_item_id}",
                )
            )

        open_statuses = {ResearchQueueStatus.OPEN, ResearchQueueStatus.READY, ResearchQueueStatus.BLOCKED}
        if item.status in open_statuses:
            key = (item.asset_id, item.research_type.value)
            if key in seen_open_keys:
                issues.append(
                    ResearchQueueValidationIssue(
                        "items",
                        f"Duplicate open research item for asset/research type: {key[0]} {key[1]}",
                    )
                )
            seen_open_keys.add(key)

    return ResearchQueueValidationResult(valid=not issues, issues=tuple(issues))


def require_text(value: Any, field_name: str) -> str:
    """Return a stripped non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise ResearchQueueError(f"{field_name} must be a non-empty string.")
    return value.strip()


def optional_text(value: Any, field_name: str) -> str | None:
    """Return a stripped optional string."""

    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ResearchQueueError(f"{field_name} must be a string.")
    return value.strip() or None


def parse_enum(enum_class: type[StrEnum], value: Any, field_name: str) -> StrEnum:
    """Parse a StrEnum from a case-insensitive string."""

    try:
        return enum_class(str(value).upper())
    except ValueError as exc:
        raise ResearchQueueError(f"Invalid {field_name}: {value}") from exc


def parse_enum_tuple(
    enum_class: type[StrEnum],
    value: Any,
    field_name: str,
) -> tuple[StrEnum, ...]:
    """Parse a list of StrEnum values."""

    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise ResearchQueueError(f"{field_name} must be a list.")
    return tuple(parse_enum(enum_class, item, field_name) for item in value)


def parse_string_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    """Parse a list/tuple of strings."""

    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise ResearchQueueError(f"{field_name} must be a list.")
    return tuple(require_text(item, field_name) for item in value)


def parse_dict(value: Any, field_name: str) -> dict[str, Any]:
    """Parse an optional dictionary."""

    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ResearchQueueError(f"{field_name} must be a dictionary.")
    return dict(value)


def parse_non_negative_int(value: Any, field_name: str) -> int:
    """Parse a required non-negative integer."""

    if isinstance(value, bool):
        raise ResearchQueueError(f"Invalid {field_name}: {value}")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ResearchQueueError(f"Invalid {field_name}: {value}") from exc
    if parsed < 0:
        raise ResearchQueueError(f"{field_name} must not be negative.")
    return parsed


def parse_optional_datetime(value: Any, field_name: str) -> datetime | None:
    """Parse an optional ISO datetime."""

    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise ResearchQueueError(f"Invalid {field_name}: {value}") from exc
    raise ResearchQueueError(f"Invalid {field_name}: {value}")


def parse_optional_url(value: Any, field_name: str) -> str | None:
    """Parse an optional HTTP(S) URL."""

    url = optional_text(value, field_name)
    if url is None:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ResearchQueueError(f"Invalid {field_name}: {value}")
    return url
