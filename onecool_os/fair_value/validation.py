"""Validation helpers for Onecool Fair Value."""

from __future__ import annotations

from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation
from enum import Enum
from typing import Any


class FairValueError(ValueError):
    """Raised when fair value inputs are invalid."""


def require_text(value: Any, field_name: str) -> str:
    """Return a required non-empty string."""

    if value is None:
        raise FairValueError(f"{field_name} is required.")
    text = str(value).strip()
    if not text:
        raise FairValueError(f"{field_name} is required.")
    return text


def optional_text(value: Any) -> str | None:
    """Return normalized optional text."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_decimal(value: Any, field_name: str) -> Decimal | None:
    """Parse an optional Decimal without using float internally."""

    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise FairValueError(f"{field_name} must be a decimal.") from exc


def parse_date(value: Any, field_name: str) -> date | None:
    """Parse an optional date."""

    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise FairValueError(f"{field_name} must be an ISO date.") from exc


def parse_datetime(value: Any, field_name: str) -> datetime:
    """Parse a datetime, defaulting to UTC for naive values."""

    if value is None:
        return datetime.now(UTC)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise FairValueError(f"{field_name} must be an ISO datetime.") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def parse_enum(enum_type: type[Enum], value: Any, field_name: str) -> Enum:
    """Parse an enum value."""

    if isinstance(value, enum_type):
        return value
    try:
        return enum_type[str(value)]
    except (KeyError, TypeError):
        try:
            return enum_type(str(value))
        except (ValueError, TypeError) as exc:
            raise FairValueError(f"{field_name} is invalid.") from exc
