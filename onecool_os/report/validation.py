"""Validation helpers for report models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from onecool_os.core.exceptions import OnecoolOSError


class ReportError(OnecoolOSError):
    """Raised when report data is invalid."""


def require_text(value: Any, field_name: str) -> str:
    """Return a stripped non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise ReportError(f"{field_name} must be a non-empty string.")
    return value.strip()


def parse_optional_datetime(value: Any, field_name: str) -> datetime | None:
    """Parse an optional datetime."""

    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ReportError(f"Invalid {field_name}: {value}")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ReportError(f"Invalid {field_name}: {value}") from exc


def parse_non_negative_number(value: Any, field_name: str) -> int | float:
    """Validate a non-negative count/value."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReportError(f"{field_name} must be numeric.")
    if value < 0:
        raise ReportError(f"{field_name} must not be negative.")
    return value


def parse_optional_dict(value: Any, field_name: str) -> dict[str, Any]:
    """Parse an optional dictionary."""

    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ReportError(f"{field_name} must be a dictionary.")
    return dict(value)


def parse_list(value: Any, field_name: str) -> tuple[Any, ...]:
    """Parse a list/tuple."""

    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise ReportError(f"{field_name} must be a list or tuple.")
    return tuple(value)
