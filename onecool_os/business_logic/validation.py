"""Validation helpers for business logic framework."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from onecool_os.core.exceptions import OnecoolOSError


class BusinessLogicError(OnecoolOSError):
    """Raised for business logic framework errors."""


def require_text(value: Any, field_name: str) -> str:
    """Return a stripped non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise BusinessLogicError(f"{field_name} must be a non-empty string.")
    return value.strip()


def optional_text(value: Any, field_name: str) -> str | None:
    """Return a stripped optional string."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise BusinessLogicError(f"{field_name} must be a string.")
    value = value.strip()
    return value or None


def optional_currency(value: Any) -> str | None:
    """Return an optional uppercase ISO-like three-letter currency code."""

    if value in (None, ""):
        return None
    currency = require_text(value, "currency").upper()
    if len(currency) != 3 or not currency.isalpha():
        raise BusinessLogicError(f"Invalid currency: {value}")
    return currency


def parse_optional_decimal(value: Any, field_name: str) -> Decimal | None:
    """Parse an optional Decimal."""

    if value in (None, ""):
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise BusinessLogicError(f"Invalid {field_name}: {value}") from exc
    if not decimal_value.is_finite():
        raise BusinessLogicError(f"Invalid {field_name}: {value}")
    return decimal_value


def parse_optional_datetime(value: Any, field_name: str) -> datetime | None:
    """Parse an optional ISO datetime."""

    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise BusinessLogicError(f"Invalid {field_name}: {value}")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise BusinessLogicError(f"Invalid {field_name}: {value}") from exc


def parse_optional_dict(value: Any, field_name: str) -> dict[str, Any]:
    """Parse an optional dictionary."""

    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise BusinessLogicError(f"{field_name} must be a dictionary.")
    return dict(value)


def parse_enum(
    enum_class: type[StrEnum],
    value: Any,
    field_name: str,
) -> StrEnum:
    """Parse a StrEnum from a case-insensitive string."""

    try:
        return enum_class(str(value).upper())
    except ValueError as exc:
        raise BusinessLogicError(f"Invalid {field_name}: {value}") from exc


def parse_optional_enum(
    enum_class: type[StrEnum],
    value: Any,
    field_name: str,
) -> StrEnum | None:
    """Parse an optional StrEnum from a case-insensitive string."""

    if value in (None, ""):
        return None
    return parse_enum(enum_class, value, field_name)


def parse_tags(value: Any) -> tuple[str, ...]:
    """Parse optional tag list."""

    if value in (None, ""):
        return ()
    if not isinstance(value, list):
        raise BusinessLogicError("tags must be a list.")
    tags: list[str] = []
    for item in value:
        tags.append(require_text(item, "tags"))
    return tuple(tags)
