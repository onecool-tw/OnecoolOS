"""Validation helpers for dashboard view models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from onecool_os.core.exceptions import OnecoolOSError


class DashboardError(OnecoolOSError):
    """Raised for dashboard validation errors."""


def require_text(value: Any, field_name: str) -> str:
    """Return a stripped non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise DashboardError(f"{field_name} must be a non-empty string.")
    return value.strip()


def optional_text(value: Any, field_name: str) -> str | None:
    """Return a stripped optional string."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise DashboardError(f"{field_name} must be a string.")
    value = value.strip()
    return value or None


def require_currency(value: Any) -> str:
    """Return an uppercase ISO-like three-letter currency code."""

    currency = require_text(value, "base_currency").upper()
    if len(currency) != 3 or not currency.isalpha():
        raise DashboardError(f"Invalid currency: {value}")
    return currency


def parse_optional_datetime(value: Any, field_name: str) -> datetime | None:
    """Parse an optional ISO datetime."""

    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise DashboardError(f"Invalid {field_name}: {value}")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise DashboardError(f"Invalid {field_name}: {value}") from exc


def parse_optional_dict(value: Any, field_name: str) -> dict[str, Any]:
    """Parse optional dictionary content."""

    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise DashboardError(f"{field_name} must be a dictionary.")
    return dict(value)


def parse_tags(value: Any) -> tuple[str, ...]:
    """Parse optional tag list."""

    if value in (None, ""):
        return ()
    if not isinstance(value, list):
        raise DashboardError("tags must be a list.")
    tags: list[str] = []
    for item in value:
        tags.append(require_text(item, "tags"))
    return tuple(tags)
