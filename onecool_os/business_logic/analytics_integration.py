"""Business Logic to Analytics integration foundation."""

from __future__ import annotations

from typing import Any

from onecool_os.business_logic.context import BusinessLogicContext
from onecool_os.business_logic.pipeline import BusinessLogicPipelineResult


class AnalyticsSnapshotBuilder:
    """Map Business Logic pipeline output to Analytics snapshot payloads."""

    default_snapshot_date = "1970-01-01"

    def build(
        self,
        pipeline_result: BusinessLogicPipelineResult,
        context: BusinessLogicContext,
    ) -> dict[str, Any]:
        """Build an AnalyticsSnapshot-compatible dictionary."""

        snapshot = {
            "snapshot_id": f"{pipeline_result.pipeline_id}-analytics",
            "portfolio_id": context.portfolio_id or context.context_id,
            "base_currency": context.base_currency or "TWD",
            "snapshot_date": _snapshot_date(context),
            "total_cost": None,
            "total_market_value": None,
            "unrealized_gain": None,
            "unrealized_return": None,
            "realized_gain": None,
            "realized_return": None,
            "asset_class_weights": {},
            "currency_weights": {},
            "account_weights": {},
            "cash_inflow": None,
            "cash_outflow": None,
            "net_cash_flow": None,
            "risk_score": None,
            "risk_level": None,
            "note": "Mapped from Business Logic pipeline result.",
            "tags": ["business_logic", "analytics_integration"],
            "metadata": {
                "source_pipeline_id": pipeline_result.pipeline_id,
                "executed_engines": list(pipeline_result.executed_engines),
                "skipped_engines": list(pipeline_result.skipped_engines),
                "errors": list(pipeline_result.errors),
            },
        }
        for result in pipeline_result.engine_results:
            _map_result(snapshot, result.engine_name, result.payload or {})
        return snapshot


def _snapshot_date(context: BusinessLogicContext) -> str:
    if context.metadata:
        value = context.metadata.get("snapshot_date")
        if value:
            return str(value)
    return AnalyticsSnapshotBuilder.default_snapshot_date


def _map_result(
    snapshot: dict[str, Any],
    engine_name: str,
    payload: dict[str, Any],
) -> None:
    if engine_name == "cash_flow":
        _map_cash_flow(snapshot, payload)
    if engine_name == "allocation":
        _map_allocation(snapshot, payload)
    if engine_name == "performance":
        _map_performance(snapshot, payload)
    if engine_name == "risk":
        _map_risk(snapshot, payload)


def _map_cash_flow(
    snapshot: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    for source_field, target_field in (
        ("cash_inflow", "cash_inflow"),
        ("cash_outflow", "cash_outflow"),
        ("net_cash_flow", "net_cash_flow"),
    ):
        if source_field in payload:
            snapshot[target_field] = payload[source_field]


def _map_allocation(
    snapshot: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    weights = payload.get("weights")
    if isinstance(weights, dict):
        snapshot["asset_class_weights"] = dict(weights)


def _map_performance(
    snapshot: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    for source_field, target_field in (
        ("cost_basis", "total_cost"),
        ("market_value", "total_market_value"),
        ("unrealized_gain", "unrealized_gain"),
        ("unrealized_return", "unrealized_return"),
    ):
        if source_field in payload:
            snapshot[target_field] = payload[source_field]


def _map_risk(
    snapshot: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    for field_name in ("risk_score", "risk_level"):
        if field_name in payload:
            snapshot[field_name] = payload[field_name]
