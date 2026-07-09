"""Reusable investment performance engine."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from onecool_os.performance.enums import PerformanceStatus
from onecool_os.performance.models import InvestmentPerformanceSnapshot
from onecool_os.performance.validation import PerformanceError
from onecool_os.performance.validation import parse_currency
from onecool_os.performance.validation import parse_datetime
from onecool_os.performance.validation import parse_non_negative_decimal
from onecool_os.performance.validation import parse_optional_date
from onecool_os.performance.validation import require_text


class InvestmentPerformanceEngine:
    """Calculate deterministic one-asset investment performance."""

    engine_name = "investment_performance"
    engine_version = "v1"

    def calculate(
        self,
        *,
        asset: Any,
        valuation: Any | None = None,
        reference_datetime: datetime | str,
        opening_cost_basis: Decimal | str | int | float | None = None,
        cost_currency: str | None = None,
        acquired_date: Any | None = None,
    ) -> InvestmentPerformanceSnapshot:
        """Calculate a deterministic performance snapshot."""

        generated_at = parse_datetime(reference_datetime, "reference_datetime")
        asset_id = _asset_id(asset)
        cost_basis = _cost_basis(asset, opening_cost_basis)
        resolved_cost_currency = _cost_currency(asset, cost_currency)
        market_value = _market_value(valuation)
        market_currency = _market_currency(valuation)
        holding_days = _holding_days(asset, acquired_date, generated_at)
        warnings = _warnings(
            cost_basis=cost_basis,
            cost_currency=resolved_cost_currency,
            market_value=market_value,
            market_currency=market_currency,
            holding_days=holding_days,
        )

        unrealized_gain = None
        unrealized_gain_percent = None
        status = PerformanceStatus.INSUFFICIENT_DATA
        if cost_basis is not None and market_value is not None:
            unrealized_gain = market_value - cost_basis
            if cost_basis > Decimal("0"):
                unrealized_gain_percent = unrealized_gain / cost_basis
            status = _performance_status(unrealized_gain)

        return InvestmentPerformanceSnapshot(
            asset_id=asset_id,
            cost_basis=cost_basis,
            cost_currency=resolved_cost_currency,
            market_value=market_value,
            market_currency=market_currency,
            unrealized_gain=unrealized_gain,
            unrealized_gain_percent=unrealized_gain_percent,
            holding_days=holding_days,
            performance_status=status,
            warnings=warnings,
            generated_at=generated_at,
        )


def _asset_id(asset: Any) -> str:
    asset_id = _get_value(asset, "asset_id")
    if asset_id is None:
        raise PerformanceError("asset_id is required.")
    return require_text(str(asset_id), "asset_id")


def _cost_basis(
    asset: Any,
    opening_cost_basis: Decimal | str | int | float | None,
) -> Decimal | None:
    if opening_cost_basis not in (None, ""):
        return parse_non_negative_decimal(
            opening_cost_basis,
            "opening_cost_basis",
        )
    for field_name in (
        "opening_cost_basis",
        "cost_basis",
        "cost",
        "purchase_price",
        "average_cost",
    ):
        value = _get_value(asset, field_name)
        if value not in (None, ""):
            return parse_non_negative_decimal(value, field_name)
    return None


def _cost_currency(asset: Any, cost_currency: str | None) -> str | None:
    if cost_currency:
        return parse_currency(cost_currency, "cost_currency")
    for field_name in ("cost_currency", "currency"):
        value = _get_value(asset, field_name)
        if value not in (None, ""):
            return parse_currency(value, field_name)
    return None


def _market_value(valuation: Any | None) -> Decimal | None:
    if valuation is None:
        return None
    for field_name in (
        "market_value",
        "estimated_value",
        "high_value",
        "low_value",
        "current_price",
    ):
        value = _get_value(valuation, field_name)
        if value not in (None, ""):
            return parse_non_negative_decimal(value, field_name)
    return None


def _market_currency(valuation: Any | None) -> str | None:
    if valuation is None:
        return None
    value = _get_value(valuation, "currency")
    if value not in (None, ""):
        return parse_currency(value, "market_currency")
    return None


def _holding_days(
    asset: Any,
    acquired_date: Any | None,
    reference_datetime: datetime,
) -> int | None:
    source_date = acquired_date
    if source_date in (None, ""):
        for field_name in (
            "acquired_date",
            "purchase_date",
            "date_acquired",
            "opening_date",
        ):
            source_date = _get_value(asset, field_name)
            if source_date not in (None, ""):
                break
    parsed = parse_optional_date(source_date, "acquired_date")
    if parsed is None:
        return None
    delta = reference_datetime.date() - parsed
    return max(delta.days, 0)


def _warnings(
    *,
    cost_basis: Decimal | None,
    cost_currency: str | None,
    market_value: Decimal | None,
    market_currency: str | None,
    holding_days: int | None,
) -> tuple[str, ...]:
    warnings: list[str] = []
    if cost_basis is None:
        warnings.append("Missing Cost Basis")
    if cost_currency is None:
        warnings.append("Missing Cost Currency")
    if market_value is None:
        warnings.append("Missing Valuation")
    if market_currency is None:
        warnings.append("Missing Market Currency")
    if (
        cost_currency is not None
        and market_currency is not None
        and cost_currency != market_currency
    ):
        warnings.append("Currency Conversion Not Applied")
    if holding_days is None:
        warnings.append("Missing Acquisition Date")
    return tuple(warnings)


def _performance_status(unrealized_gain: Decimal) -> PerformanceStatus:
    if unrealized_gain > Decimal("0"):
        return PerformanceStatus.POSITIVE
    if unrealized_gain < Decimal("0"):
        return PerformanceStatus.NEGATIVE
    return PerformanceStatus.BREAKEVEN


def _get_value(source: Any, field_name: str) -> Any:
    if source is None:
        return None
    if isinstance(source, dict):
        return source.get(field_name)
    return getattr(source, field_name, None)
