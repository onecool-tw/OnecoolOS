"""Validation helpers for transaction and ledger models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from onecool_os.core.exceptions import OnecoolOSError


class TransactionError(OnecoolOSError):
    """Raised for transaction and ledger validation errors."""


def require_text(value: Any, field_name: str) -> str:
    """Return a stripped non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise TransactionError(f"{field_name} must be a non-empty string.")
    return value.strip()


def optional_text(value: Any, field_name: str) -> str | None:
    """Return a stripped optional string."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise TransactionError(f"{field_name} must be a string.")
    value = value.strip()
    return value or None


def require_currency(value: Any) -> str:
    """Return an uppercase ISO-like three-letter currency code."""

    currency = require_text(value, "currency").upper()
    if len(currency) != 3 or not currency.isalpha():
        raise TransactionError(f"Invalid currency: {value}")
    return currency


def parse_date(value: Any, field_name: str) -> date:
    """Parse an ISO date."""

    if not isinstance(value, str):
        raise TransactionError(f"Invalid {field_name}: {value}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise TransactionError(f"Invalid {field_name}: {value}") from exc


def parse_optional_date(value: Any, field_name: str) -> date | None:
    """Parse an optional ISO date."""

    if value in (None, ""):
        return None
    return parse_date(value, field_name)


def parse_optional_datetime(value: Any, field_name: str) -> datetime | None:
    """Parse an optional ISO datetime."""

    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise TransactionError(f"Invalid {field_name}: {value}")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise TransactionError(f"Invalid {field_name}: {value}") from exc


def parse_optional_decimal(value: Any, field_name: str) -> Decimal | None:
    """Parse an optional Decimal."""

    if value in (None, ""):
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise TransactionError(f"Invalid {field_name}: {value}") from exc
    if not decimal_value.is_finite():
        raise TransactionError(f"Invalid {field_name}: {value}")
    return decimal_value


def parse_non_negative_decimal(value: Any, field_name: str) -> Decimal | None:
    """Parse an optional non-negative Decimal."""

    decimal_value = parse_optional_decimal(value, field_name)
    if decimal_value is not None and decimal_value < Decimal("0"):
        raise TransactionError(f"{field_name} must not be negative.")
    return decimal_value


def parse_enum(
    enum_class: type[StrEnum],
    value: Any,
    field_name: str,
) -> StrEnum:
    """Parse a StrEnum from a case-insensitive string."""

    try:
        return enum_class(str(value).upper())
    except ValueError as exc:
        raise TransactionError(f"Invalid {field_name}: {value}") from exc


def parse_tags(value: Any) -> tuple[str, ...]:
    """Parse optional tag list."""

    if value in (None, ""):
        return ()
    if not isinstance(value, list):
        raise TransactionError("tags must be a list.")
    tags: list[str] = []
    for item in value:
        tags.append(require_text(item, "tags"))
    return tuple(tags)
