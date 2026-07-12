"""Validation helpers for valuation integration."""

from __future__ import annotations

from typing import Any

from onecool_os.valuation.validation import ValuationError


class ValuationIntegrationError(ValuationError):
    """Raised when runtime valuation integration fails validation."""


def require_snapshot_asset(snapshot: Any) -> str:
    """Return a required snapshot asset id."""

    asset_id = str(getattr(snapshot, "asset_id", "") or "").strip()
    if not asset_id:
        raise ValuationIntegrationError("missing asset")
    return asset_id


def require_market_value(snapshot: Any) -> Any:
    """Return a required snapshot market value."""

    value = getattr(snapshot, "fair_value", None)
    if value is None:
        raise ValuationIntegrationError("missing market value")
    return value


def require_currency(snapshot: Any) -> str:
    """Return a required snapshot currency."""

    currency = str(getattr(snapshot, "currency", "") or "").strip().upper()
    if not currency:
        raise ValuationIntegrationError("missing currency")
    return currency


def ensure_unique(items: list[str] | tuple[str, ...], message: str) -> None:
    """Ensure all string ids are unique."""

    seen: set[str] = set()
    for item in items:
        if item in seen:
            raise ValuationIntegrationError(message)
        seen.add(item)
