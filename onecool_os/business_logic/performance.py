"""Performance Engine foundation."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from onecool_os.business_logic.calculators import BaseCalculator
from onecool_os.business_logic.context import BusinessLogicContext
from onecool_os.business_logic.results import BusinessLogicResult


class PerformanceEngine(BaseCalculator):
    """Calculate deterministic unrealized performance metrics."""

    def __init__(self) -> None:
        super().__init__(engine_name="performance", engine_version="v1")

    def supports(self, context: BusinessLogicContext) -> bool:
        """Return whether this engine can inspect the context."""

        return isinstance(context, BusinessLogicContext)

    def calculate(
        self,
        context: BusinessLogicContext,
    ) -> BusinessLogicResult:
        """Calculate unrealized performance from context data."""

        positions = _positions_from_context(context)
        valuation_values = _valuation_values(context.valuation_data)
        cost_basis = _cost_basis(context.portfolio_data, positions)
        market_value = _market_value(
            context.portfolio_data,
            positions,
            valuation_values,
        )
        unrealized_gain = market_value - cost_basis
        unrealized_return = None
        if cost_basis > Decimal("0"):
            unrealized_return = unrealized_gain / cost_basis
        payload = {
            "cost_basis": cost_basis,
            "market_value": market_value,
            "unrealized_gain": unrealized_gain,
            "unrealized_return": unrealized_return,
            "realized_gain": None,
            "realized_return": None,
            "currency": context.base_currency,
            "position_count": len(positions),
        }
        return BusinessLogicResult(
            result_id=f"{context.context_id}-performance",
            engine_name=self.engine_name,
            engine_version=self.engine_version,
            metric_type="PERFORMANCE",
            value=unrealized_return,
            currency=context.base_currency,
            payload=payload,
            confidence="HIGH",
            note="Deterministic unrealized performance metrics.",
            tags=["performance", "business_logic"],
        )


def _positions_from_context(context: BusinessLogicContext) -> tuple[Any, ...]:
    for source in (
        context.portfolio_data,
        context.ledger_data,
        context.analytics_data,
    ):
        positions = _positions_from_source(source)
        if positions:
            return positions
    return ()


def _positions_from_source(source: Any) -> tuple[Any, ...]:
    if source in (None, ""):
        return ()
    if hasattr(source, "list_holdings"):
        return tuple(source.list_holdings())
    if hasattr(source, "list_positions"):
        return tuple(source.list_positions())
    if hasattr(source, "holdings"):
        return tuple(getattr(source, "holdings") or ())
    if hasattr(source, "positions"):
        return tuple(getattr(source, "positions") or ())
    if isinstance(source, dict):
        for key in ("holdings", "positions"):
            values = source.get(key)
            if values:
                return tuple(values)
    if isinstance(source, (list, tuple)):
        return tuple(source)
    return ()


def _valuation_values(source: Any) -> dict[str, Decimal]:
    values: dict[str, Decimal] = {}
    for valuation in _valuations_from_source(source):
        asset_id = _get_value(valuation, "asset_id")
        if asset_id is None:
            continue
        value = _valuation_value(valuation)
        if value is not None:
            values[str(asset_id)] = value
    return values


def _valuations_from_source(source: Any) -> tuple[Any, ...]:
    if source in (None, ""):
        return ()
    if hasattr(source, "valuations"):
        return tuple(getattr(source, "valuations") or ())
    if isinstance(source, dict):
        return tuple(source.get("valuations") or ())
    if isinstance(source, (list, tuple)):
        return tuple(source)
    return ()


def _cost_basis(source: Any, positions: tuple[Any, ...]) -> Decimal:
    total_cost = _method_decimal(source, "total_cost")
    if total_cost is not None:
        return total_cost
    total_cost = _decimal_or_none(_get_value(source, "total_cost"))
    if total_cost is not None:
        return max(total_cost, Decimal("0"))
    return sum(
        (_position_cost(position) for position in positions),
        Decimal("0"),
    )


def _market_value(
    source: Any,
    positions: tuple[Any, ...],
    valuation_values: dict[str, Decimal],
) -> Decimal:
    total_value = _method_decimal(source, "total_market_value")
    if total_value is not None:
        return total_value
    total_value = _decimal_or_none(_get_value(source, "total_market_value"))
    if total_value is not None:
        return max(total_value, Decimal("0"))
    return sum(
        (
            _position_market_value(position, valuation_values)
            for position in positions
        ),
        Decimal("0"),
    )


def _position_cost(position: Any) -> Decimal:
    total_cost = _method_decimal(position, "total_cost")
    if total_cost is not None:
        return total_cost
    cost = _decimal_or_none(_get_value(position, "cost"))
    if cost is not None:
        return max(cost, Decimal("0"))
    quantity = _decimal_or_none(_get_value(position, "quantity"))
    average_cost = _decimal_or_none(_get_value(position, "average_cost"))
    if quantity is None or average_cost is None:
        return Decimal("0")
    return max(quantity * average_cost, Decimal("0"))


def _position_market_value(
    position: Any,
    valuation_values: dict[str, Decimal],
) -> Decimal:
    market_value = _method_decimal(position, "market_value")
    if market_value is not None:
        return market_value
    market_value = _decimal_or_none(_get_value(position, "market_value"))
    if market_value is not None:
        return max(market_value, Decimal("0"))
    asset_id = _asset_id(position)
    if asset_id in valuation_values:
        return valuation_values[asset_id]
    quantity = _decimal_or_none(_get_value(position, "quantity"))
    current_price = _decimal_or_none(_get_value(position, "current_price"))
    if quantity is None or current_price is None:
        return Decimal("0")
    return max(quantity * current_price, Decimal("0"))


def _valuation_value(valuation: Any) -> Decimal | None:
    for field_name in (
        "market_value",
        "estimated_value",
        "high_value",
        "low_value",
    ):
        value = _decimal_or_none(_get_value(valuation, field_name))
        if value is not None:
            return max(value, Decimal("0"))
    return None


def _asset_id(position: Any) -> str:
    asset_id = _get_value(position, "asset_id")
    if asset_id is not None:
        return str(asset_id)
    asset = _get_value(position, "asset")
    if asset is not None:
        asset_id = _get_value(asset, "asset_id")
        if asset_id is not None:
            return str(asset_id)
    return ""


def _method_decimal(source: Any, method_name: str) -> Decimal | None:
    method = getattr(source, method_name, None)
    if not callable(method):
        return None
    value = _decimal_or_none(method())
    if value is None:
        return None
    return max(value, Decimal("0"))


def _get_value(source: Any, field_name: str) -> Any:
    if source is None:
        return None
    if isinstance(source, dict):
        return source.get(field_name)
    return getattr(source, field_name, None)


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, "") or callable(value):
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not decimal_value.is_finite():
        return None
    return decimal_value
