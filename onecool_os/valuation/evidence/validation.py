"""Validation helpers for eBay Sold evidence."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation
from enum import StrEnum
from typing import Any

from onecool_os.core.exceptions import OnecoolOSError


class EvidenceError(OnecoolOSError):
    """Raised when eBay Sold evidence cannot be parsed."""


def require_text(value: Any, field_name: str) -> str:
    """Return a stripped non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{field_name} must be a non-empty string.")
    return value.strip()


def optional_text(value: Any, field_name: str) -> str | None:
    """Return a stripped optional string."""

    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise EvidenceError(f"{field_name} must be a string.")
    return value.strip() or None


def require_currency(value: Any) -> str:
    """Return an uppercase ISO-like three-letter currency code."""

    currency = require_text(value, "currency").upper()
    if len(currency) != 3 or not currency.isalpha():
        raise EvidenceError(f"Invalid currency: {value}")
    return currency


def parse_enum(
    enum_class: type[StrEnum],
    value: Any,
    field_name: str,
) -> StrEnum:
    """Parse a StrEnum from a case-insensitive string."""

    try:
        return enum_class(str(value).upper())
    except ValueError as exc:
        raise EvidenceError(f"Invalid {field_name}: {value}") from exc


def parse_date(value: Any, field_name: str) -> date:
    """Parse an ISO date."""

    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise EvidenceError(f"Invalid {field_name}: {value}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise EvidenceError(f"Invalid {field_name}: {value}") from exc


def parse_datetime(value: Any, field_name: str) -> datetime:
    """Parse an ISO datetime."""

    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise EvidenceError(f"Invalid {field_name}: {value}")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise EvidenceError(f"Invalid {field_name}: {value}") from exc


def parse_optional_decimal(value: Any, field_name: str) -> Decimal | None:
    """Parse an optional non-negative Decimal."""

    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise EvidenceError(f"Invalid {field_name}: {value}") from exc
    if not parsed.is_finite() or parsed < Decimal("0"):
        raise EvidenceError(f"Invalid {field_name}: {value}")
    return parsed


def parse_required_decimal(value: Any, field_name: str) -> Decimal:
    """Parse a required non-negative Decimal."""

    parsed = parse_optional_decimal(value, field_name)
    if parsed is None:
        raise EvidenceError(f"{field_name} is required.")
    return parsed


def parse_bool(value: Any, field_name: str) -> bool:
    """Parse a required boolean."""

    if isinstance(value, bool):
        return value
    raise EvidenceError(f"{field_name} must be a boolean.")


def parse_optional_bool(value: Any, field_name: str) -> bool | None:
    """Parse an optional boolean."""

    if value in (None, ""):
        return None
    return parse_bool(value, field_name)


def parse_string_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    """Parse a list/tuple of strings."""

    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise EvidenceError(f"{field_name} must be a list.")
    return tuple(require_text(item, field_name) for item in value)


def parse_dict(value: Any, field_name: str) -> dict[str, Any]:
    """Parse an optional metadata dictionary."""

    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise EvidenceError(f"{field_name} must be a dictionary.")
    return dict(value)
