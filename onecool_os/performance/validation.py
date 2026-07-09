"""Validation helpers for investment performance."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation
from enum import StrEnum
from typing import Any

from onecool_os.core.exceptions import OnecoolOSError


class PerformanceError(OnecoolOSError):
    """Raised when performance data is invalid."""


def require_text(value: Any, field_name: str) -> str:
    """Return a required non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise PerformanceError(f"{field_name} must be a non-empty string.")
    return value.strip()


def optional_text(value: Any) -> str | None:
    """Return optional normalized text."""

    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None


def parse_currency(value: Any, field_name: str) -> str | None:
    """Return an uppercase currency code when present."""

    text = optional_text(value)
    if text is None:
        return None
    return text.upper()


def parse_non_negative_decimal(
    value: Any,
    field_name: str,
) -> Decimal | None:
    """Parse an optional non-negative Decimal."""

    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise PerformanceError(f"{field_name} must be a number.") from exc
    if not parsed.is_finite() or parsed < Decimal("0"):
        raise PerformanceError(f"{field_name} must not be negative.")
    return parsed


def parse_datetime(value: Any, field_name: str) -> datetime:
    """Parse a required datetime."""

    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    text = optional_text(value)
    if text is None:
        raise PerformanceError(f"{field_name} must be a datetime.")
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise PerformanceError(f"{field_name} must be an ISO datetime.") from exc


def parse_optional_date(value: Any, field_name: str) -> date | None:
    """Parse an optional date."""

    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = optional_text(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise PerformanceError(f"{field_name} must be an ISO date.") from exc


def parse_enum(enum_type: type[StrEnum], value: Any, field_name: str) -> StrEnum:
    """Parse a string enum value."""

    try:
        if isinstance(value, enum_type):
            return value
        return enum_type(str(value).upper())
    except ValueError as exc:
        raise PerformanceError(f"Invalid {field_name}.") from exc

