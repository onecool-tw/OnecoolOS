"""Validation helpers for portfolio history snapshots."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation
from enum import StrEnum
from typing import Any

from onecool_os.core.exceptions import OnecoolOSError


class PortfolioHistoryError(OnecoolOSError):
    """Raised when portfolio history validation fails."""


def require_text(value: Any, field_name: str) -> str:
    """Return a stripped non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise PortfolioHistoryError(f"{field_name} must be a non-empty string.")
    return value.strip()


def optional_text(value: Any) -> str | None:
    """Return optional stripped text."""

    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise PortfolioHistoryError("optional text fields must be strings.")
    return value.strip() or None


def parse_enum(enum_type: type[StrEnum], value: Any, field_name: str) -> StrEnum:
    """Parse a StrEnum value."""

    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value).upper())
    except ValueError as exc:
        raise PortfolioHistoryError(f"Invalid {field_name}: {value}") from exc


def parse_datetime(value: Any, field_name: str) -> datetime:
    """Parse an ISO datetime."""

    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise PortfolioHistoryError(f"Invalid {field_name}: {value}")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise PortfolioHistoryError(f"Invalid {field_name}: {value}") from exc


def parse_date(value: Any, field_name: str) -> date:
    """Parse an ISO date."""

    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise PortfolioHistoryError(f"Invalid {field_name}: {value}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise PortfolioHistoryError(f"Invalid {field_name}: {value}") from exc


def parse_optional_decimal(value: Any, field_name: str) -> Decimal | None:
    """Parse an optional Decimal without float conversion."""

    if value in (None, ""):
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise PortfolioHistoryError(f"Invalid {field_name}: {value}") from exc
    if not decimal_value.is_finite():
        raise PortfolioHistoryError(f"Invalid {field_name}: {value}")
    return decimal_value


def parse_non_negative_int(value: Any, field_name: str) -> int:
    """Parse a non-negative integer."""

    if isinstance(value, bool):
        raise PortfolioHistoryError(f"Invalid {field_name}: {value}")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise PortfolioHistoryError(f"Invalid {field_name}: {value}") from exc
    if parsed < 0:
        raise PortfolioHistoryError(f"{field_name} must not be negative.")
    return parsed


def parse_string_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    """Parse strings into an immutable tuple."""

    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise PortfolioHistoryError(f"{field_name} must be a list.")
    return tuple(str(item) for item in value)


def parse_dict(value: Any, field_name: str) -> dict[str, Any]:
    """Parse a dictionary."""

    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise PortfolioHistoryError(f"{field_name} must be a dictionary.")
    return dict(value)


def validate_percent(value: Decimal | None, field_name: str) -> None:
    """Validate an optional 0-100 percentage."""

    if value is None:
        return
    if value < Decimal("0") or value > Decimal("100"):
        raise PortfolioHistoryError(f"{field_name} must be between 0 and 100.")
