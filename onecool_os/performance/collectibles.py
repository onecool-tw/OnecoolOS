"""Collectible performance integration."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from onecool_os.performance.engine import InvestmentPerformanceEngine
from onecool_os.performance.models import InvestmentPerformanceSnapshot
from onecool_os.performance.validation import PerformanceError


class CollectiblePerformanceBuilder:
    """Build performance snapshots for sports card collectible records."""

    def __init__(
        self,
        engine: InvestmentPerformanceEngine | None = None,
    ) -> None:
        self._engine = engine or InvestmentPerformanceEngine()

    def build(
        self,
        *,
        collectible_assets: Iterable[Any],
        valuation_records: Iterable[Any] | dict[str, Any] | None = None,
        reference_datetime: datetime | str,
    ) -> tuple[InvestmentPerformanceSnapshot, ...]:
        """Build deterministic performance snapshots for collectible assets."""

        valuation_map = _valuation_map(valuation_records)
        snapshots: list[InvestmentPerformanceSnapshot] = []
        for asset in tuple(collectible_assets):
            asset_id = _asset_id(asset)
            valuation = valuation_map.get(asset_id)
            snapshot = self._engine.calculate(
                asset=asset,
                valuation=valuation,
                opening_cost_basis=_opening_cost_basis(asset),
                cost_currency=_cost_currency(asset),
                acquired_date=_acquired_date(asset),
                reference_datetime=reference_datetime,
            )
            snapshots.append(_with_collectible_warnings(snapshot))
        return tuple(snapshots)


def _valuation_map(
    valuation_records: Iterable[Any] | dict[str, Any] | None,
) -> dict[str, Any]:
    if valuation_records is None:
        return {}
    if isinstance(valuation_records, dict):
        if "asset_id" in valuation_records:
            return {_asset_id(valuation_records): valuation_records}
        return {
            str(asset_id): valuation
            for asset_id, valuation in valuation_records.items()
        }

    mapped: dict[str, Any] = {}
    for valuation in tuple(valuation_records):
        mapped[_asset_id(valuation)] = valuation
    return mapped


def _opening_cost_basis(asset: Any) -> Any:
    for field_name in (
        "my_cost",
        "My Cost",
        "opening_cost_basis",
        "cost",
        "purchase_price",
    ):
        value = _get_value(asset, field_name)
        if value not in (None, ""):
            return value
    return None


def _cost_currency(asset: Any) -> str | None:
    for field_name in ("cost_currency", "currency"):
        value = _get_value(asset, field_name)
        if value not in (None, ""):
            return str(value)
    return None


def _acquired_date(asset: Any) -> Any:
    for field_name in ("date_acquired", "Date Acquired", "purchase_date"):
        value = _get_value(asset, field_name)
        if value not in (None, ""):
            return value
    return None


def _asset_id(source: Any) -> str:
    asset_id = _get_value(source, "asset_id")
    if asset_id in (None, ""):
        raise PerformanceError("asset_id is required.")
    return str(asset_id)


def _get_value(source: Any, field_name: str) -> Any:
    if source is None:
        return None
    if isinstance(source, dict):
        return source.get(field_name)
    return getattr(source, field_name, None)


def _with_collectible_warnings(
    snapshot: InvestmentPerformanceSnapshot,
) -> InvestmentPerformanceSnapshot:
    warnings = list(snapshot.warnings)
    if snapshot.market_value is None:
        warnings.append("Missing Market Value")
    if snapshot.cost_basis is None or snapshot.market_value is None:
        warnings.append("Insufficient Data")
    if (
        snapshot.cost_currency is not None
        and snapshot.market_currency is not None
        and snapshot.cost_currency != snapshot.market_currency
    ):
        warnings.append("Currency Mismatch")
    if snapshot.holding_days is None:
        warnings.append("Missing Acquired Date")

    return InvestmentPerformanceSnapshot(
        asset_id=snapshot.asset_id,
        cost_basis=snapshot.cost_basis,
        cost_currency=snapshot.cost_currency,
        market_value=snapshot.market_value,
        market_currency=snapshot.market_currency,
        unrealized_gain=snapshot.unrealized_gain,
        unrealized_gain_percent=snapshot.unrealized_gain_percent,
        holding_days=snapshot.holding_days,
        performance_status=snapshot.performance_status,
        warnings=tuple(dict.fromkeys(warnings)),
        generated_at=snapshot.generated_at,
    )
