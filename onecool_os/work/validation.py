"""Validation helpers for Onecool Work Contract bridge."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from onecool_os.core.exceptions import OnecoolOSError


class WorkContractError(OnecoolOSError):
    """Raised when Work Contract data is invalid."""


def require_text(value: Any, field_name: str) -> str:
    """Return a stripped non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise WorkContractError(f"{field_name} must be a non-empty string.")
    return value.strip()


def optional_text(value: Any, field_name: str) -> str | None:
    """Return a stripped optional string."""

    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise WorkContractError(f"{field_name} must be a string.")
    return value.strip() or None


def parse_datetime(value: Any, field_name: str) -> datetime:
    """Parse an ISO datetime value."""

    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise WorkContractError(f"Invalid {field_name}: {value}")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise WorkContractError(f"Invalid {field_name}: {value}") from exc


def parse_optional_datetime(value: Any, field_name: str) -> datetime | None:
    """Parse an optional ISO datetime value."""

    if value in (None, ""):
        return None
    return parse_datetime(value, field_name)


def parse_dict(value: Any, field_name: str) -> dict[str, Any]:
    """Parse an optional dictionary."""

    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise WorkContractError(f"{field_name} must be a dictionary.")
    return dict(value)


def parse_list(value: Any, field_name: str) -> tuple[Any, ...]:
    """Parse an optional list."""

    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise WorkContractError(f"{field_name} must be a list.")
    return tuple(value)


def parse_enum(enum_class: type[StrEnum], value: Any, field_name: str) -> StrEnum:
    """Parse a StrEnum value."""

    try:
        return enum_class(str(value).upper())
    except ValueError as exc:
        raise WorkContractError(f"Invalid {field_name}: {value}") from exc
