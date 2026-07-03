"""Validation helpers for portfolio aggregation models."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from onecool_os.core.exceptions import OnecoolOSError


class PortfolioError(OnecoolOSError):
    """Raised for portfolio model errors."""


def require_text(value: Any, field_name: str) -> str:
    """Return a stripped non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise PortfolioError(f"{field_name} must be a non-empty string.")
    return value.strip()


def optional_text(value: Any, field_name: str) -> str | None:
    """Return a stripped optional string."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise PortfolioError(f"{field_name} must be a string.")
    value = value.strip()
    return value or None


def require_currency(value: Any) -> str:
    """Return an uppercase ISO-like three-letter currency code."""

    currency = require_text(value, "base_currency").upper()
    if len(currency) != 3 or not currency.isalpha():
        raise PortfolioError(f"Invalid currency: {value}")
    return currency


def parse_non_negative_decimal(value: Any, field_name: str) -> Decimal:
    """Parse a required non-negative Decimal."""

    decimal_value = _parse_decimal(value, field_name)
    if decimal_value < Decimal("0"):
        raise PortfolioError(f"{field_name} must not be negative.")
    return decimal_value


def parse_optional_non_negative_decimal(
    value: Any,
    field_name: str,
) -> Decimal | None:
    """Parse an optional non-negative Decimal."""

    if value in (None, ""):
        return None
    return parse_non_negative_decimal(value, field_name)


def parse_optional_non_negative_int(value: Any, field_name: str) -> int | None:
    """Parse an optional non-negative integer."""

    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise PortfolioError(f"Invalid {field_name}: {value}")
    try:
        int_value = int(value)
    except (TypeError, ValueError) as exc:
        raise PortfolioError(f"Invalid {field_name}: {value}") from exc
    if int_value < 0:
        raise PortfolioError(f"{field_name} must not be negative.")
    return int_value


def parse_tags(value: Any) -> tuple[str, ...]:
    """Parse optional tag list."""

    if value in (None, ""):
        return ()
    if not isinstance(value, list):
        raise PortfolioError("tags must be a list.")
    tags: list[str] = []
    for item in value:
        tags.append(require_text(item, "tags"))
    return tuple(tags)


def _parse_decimal(value: Any, field_name: str) -> Decimal:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise PortfolioError(f"Invalid {field_name}: {value}") from exc
    if not decimal_value.is_finite():
        raise PortfolioError(f"Invalid {field_name}: {value}")
    return decimal_value
