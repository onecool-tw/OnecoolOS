"""Validation helpers for Asset Master metadata."""

from __future__ import annotations

from decimal import Decimal
from decimal import InvalidOperation
from typing import Any
from urllib.parse import parse_qs
from urllib.parse import urlparse

from onecool_os.core.exceptions import OnecoolOSError


class AssetMasterError(OnecoolOSError):
    """Raised when Asset Master data is invalid."""


def normalize_required_text(value: Any, field_name: str) -> str:
    text = normalize_optional_text(value)
    if not text:
        raise AssetMasterError(f"{field_name} is required.")
    return text


def normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_optional_decimal(
    value: Any,
    field_name: str,
) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise AssetMasterError(f"Invalid {field_name}: {value}") from exc
    if not parsed.is_finite() or parsed < 0:
        raise AssetMasterError(f"Invalid {field_name}: {value}")
    return parsed


def normalize_optional_int(value: Any, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(str(value).strip())
    except ValueError as exc:
        raise AssetMasterError(f"Invalid {field_name}: {value}") from exc
    if parsed < 0:
        raise AssetMasterError(f"Invalid {field_name}: {value}")
    return parsed


def validate_ebay_sold_search_url(url: str | None) -> str | None:
    """Return an error message for invalid eBay Sold search URLs."""

    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or "ebay." not in parsed.netloc:
        return "Malformed eBay URL"
    query = parse_qs(parsed.query)
    if query.get("LH_Sold") != ["1"] or query.get("LH_Complete") != ["1"]:
        return "eBay Sold URL must include LH_Sold=1 and LH_Complete=1"
    return None


def validate_psa_url(url: str | None) -> str | None:
    """Return an error message for invalid PSA URLs."""

    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "Malformed PSA URL"
    if not (
        "psacard.com" in parsed.netloc
        or parsed.netloc.endswith("psa.com")
    ):
        return "Malformed PSA URL"
    return None
