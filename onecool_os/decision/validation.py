"""Validation helpers for Decision Engine."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from onecool_os.core.exceptions import OnecoolOSError


class DecisionError(OnecoolOSError):
    """Raised for decision validation errors."""


def require_text(value: Any, field_name: str) -> str:
    """Return a stripped non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise DecisionError(f"{field_name} must be a non-empty string.")
    return value.strip()


def optional_text(value: Any, field_name: str) -> str | None:
    """Return a stripped optional string."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise DecisionError(f"{field_name} must be a string.")
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
        raise DecisionError(f"Invalid {field_name}: {value}") from exc


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
        raise DecisionError(f"Invalid {field_name}: {value}")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise DecisionError(f"Invalid {field_name}: {value}") from exc


def parse_optional_dict(value: Any, field_name: str) -> dict[str, Any]:
    """Parse an optional dictionary."""

    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise DecisionError(f"{field_name} must be a dictionary.")
    return dict(value)


def parse_text_list(value: Any, field_name: str) -> tuple[str, ...]:
    """Parse an optional list of text values."""

    if value in (None, ""):
        return ()
    if not isinstance(value, list):
        raise DecisionError(f"{field_name} must be a list.")
    return tuple(require_text(item, field_name) for item in value)


def parse_decimal_between(
    value: Any,
    field_name: str,
    lower: Decimal,
    upper: Decimal,
) -> Decimal | None:
    """Parse an optional decimal bounded by lower and upper."""

    if value in (None, ""):
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DecisionError(f"Invalid {field_name}: {value}") from exc
    if not decimal_value.is_finite():
        raise DecisionError(f"Invalid {field_name}: {value}")
    if decimal_value < lower or decimal_value > upper:
        raise DecisionError(
            f"{field_name} must be between {lower} and {upper}."
        )
    return decimal_value
