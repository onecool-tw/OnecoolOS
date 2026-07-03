"""Allocation Engine foundation."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from onecool_os.business_logic.calculators import BaseCalculator
from onecool_os.business_logic.context import BusinessLogicContext
from onecool_os.business_logic.results import BusinessLogicResult


class AllocationEngine(BaseCalculator):
    """Calculate deterministic allocation weights from context values."""

    category_names = {
        "CASH": "Cash",
        "STOCK": "Equity",
        "ETF": "ETF",
        "MUTUAL_FUND": "Mutual Fund",
        "REAL_ESTATE": "Real Estate",
        "SPORTS_CARD": "Collectible",
        "COLLECTIBLE": "Collectible",
        "CRYPTO": "Crypto",
        "BOND": "Bond",
    }

    def __init__(self) -> None:
        super().__init__(engine_name="allocation", engine_version="v1")

    def supports(self, context: BusinessLogicContext) -> bool:
        """Return whether this engine can inspect the context."""

        return isinstance(context, BusinessLogicContext)

    def calculate(
        self,
        context: BusinessLogicContext,
    ) -> BusinessLogicResult:
        """Calculate allocation totals and category weights."""

        holdings = tuple(_holdings_from_source(context.ledger_data))
        categories: dict[str, Decimal] = {}
        for holding in holdings:
            category = _category_name(_asset_type(holding))
            value = _holding_value(holding)
            categories[category] = (
                categories.get(category, Decimal("0")) + value
            )

        categories = {
            category: categories[category]
            for category in sorted(categories)
        }
        total_value = sum(categories.values(), Decimal("0"))
        weights = _calculate_weights(categories, total_value)
        payload = {
            "total_value": total_value,
            "categories": categories,
            "weights": weights,
        }
        return BusinessLogicResult(
            result_id=f"{context.context_id}-allocation",
            engine_name=self.engine_name,
            engine_version=self.engine_version,
            metric_type="ALLOCATION",
            value=total_value,
            currency=context.base_currency,
            payload=payload,
            confidence="HIGH",
            note="Deterministic allocation metrics from context values.",
            tags=["allocation", "business_logic"],
        )


def _holdings_from_source(source: Any) -> tuple[Any, ...]:
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


def _asset_type(holding: Any) -> str:
    asset_type = _get_value(holding, "asset_type")
    if asset_type is not None:
        return str(asset_type).upper()
    asset = _get_value(holding, "asset")
    if asset is not None:
        asset_type = _get_value(asset, "asset_type")
        if asset_type is not None:
            return str(asset_type).upper()
    return "OTHER"


def _category_name(asset_type: str) -> str:
    normalized_type = asset_type.strip().upper()
    if normalized_type in AllocationEngine.category_names:
        return AllocationEngine.category_names[normalized_type]
    return normalized_type.replace("_", " ").title()


def _holding_value(holding: Any) -> Decimal:
    for field_name in (
        "market_value",
        "value",
        "estimated_value",
        "current_value",
    ):
        raw_value = _get_value(holding, field_name)
        value = _value_from_raw(raw_value)
        if value is not None:
            return value
    market_value = _get_value(holding, "market_value")
    if callable(market_value):
        value = _value_from_raw(market_value())
        if value is not None:
            return value
    return Decimal("0")


def _value_from_raw(raw_value: Any) -> Decimal | None:
    if raw_value in (None, "") or callable(raw_value):
        return None
    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, ValueError):
        return None
    if not value.is_finite() or value < Decimal("0"):
        return Decimal("0")
    return value


def _calculate_weights(
    categories: dict[str, Decimal],
    total_value: Decimal,
) -> dict[str, Decimal]:
    if total_value <= Decimal("0"):
        return {category: Decimal("0") for category in categories}
    weights: dict[str, Decimal] = {}
    running_total = Decimal("0")
    category_items = tuple(categories.items())
    for index, (category, value) in enumerate(category_items):
        if index == len(category_items) - 1:
            weights[category] = Decimal("1") - running_total
        else:
            weight = value / total_value
            weights[category] = weight
            running_total += weight
    return weights


def _get_value(source: Any, field_name: str) -> Any:
    if isinstance(source, dict):
        return source.get(field_name)
    return getattr(source, field_name, None)
