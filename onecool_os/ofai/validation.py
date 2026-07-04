"""Validation helpers for OFAI foundation."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from onecool_os.core.exceptions import OnecoolOSError


class OFAIError(OnecoolOSError):
    """Raised for OFAI validation errors."""


def require_text(value: Any, field_name: str) -> str:
    """Return a stripped non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise OFAIError(f"{field_name} must be a non-empty string.")
    return value.strip()


def optional_text(value: Any, field_name: str) -> str | None:
    """Return a stripped optional string."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise OFAIError(f"{field_name} must be a string.")
    value = value.strip()
    return value or None


def parse_enum(
    enum_class: type[StrEnum],
    value: Any,
    field_name: str,
) -> StrEnum:
    """Parse a StrEnum from a case-insensitive string."""

    try:
        return enum_class(str(value).upper())
    except ValueError as exc:
        raise OFAIError(f"Invalid {field_name}: {value}") from exc


def parse_optional_enum(
    enum_class: type[StrEnum],
    value: Any,
    field_name: str,
) -> StrEnum | None:
    """Parse an optional StrEnum."""

    if value in (None, ""):
        return None
    return parse_enum(enum_class, value, field_name)


def parse_optional_datetime(value: Any, field_name: str) -> datetime | None:
    """Parse an optional ISO datetime."""

    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise OFAIError(f"Invalid {field_name}: {value}")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise OFAIError(f"Invalid {field_name}: {value}") from exc


def parse_optional_dict(value: Any, field_name: str) -> dict[str, Any]:
    """Parse an optional dictionary."""

    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise OFAIError(f"{field_name} must be a dictionary.")
    return dict(value)


def parse_text_list(value: Any, field_name: str) -> tuple[str, ...]:
    """Parse an optional list of text values."""

    if value in (None, ""):
        return ()
    if not isinstance(value, list):
        raise OFAIError(f"{field_name} must be a list.")
    return tuple(require_text(item, field_name) for item in value)
