"""Dashboard Analytics display views."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from onecool_os.dashboard.validation import parse_optional_datetime
from onecool_os.dashboard.validation import parse_optional_dict
from onecool_os.dashboard.validation import require_text


@dataclass(frozen=True)
class DashboardAnalyticsSection:
    """Display-only analytics section."""

    title: str
    status: str
    summary: str
    details: dict[str, Any] | None = None
    generated_at: datetime | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", require_text(self.title, "title"))
        object.__setattr__(
            self,
            "status",
            require_text(self.status, "status"),
        )
        object.__setattr__(
            self,
            "summary",
            require_text(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "details",
            parse_optional_dict(self.details, "details"),
        )
        object.__setattr__(
            self,
            "generated_at",
            parse_optional_datetime(self.generated_at, "generated_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe analytics section."""

        return {
            "title": self.title,
            "status": self.status,
            "summary": self.summary,
            "details": self.details,
            "generated_at": _format_optional_datetime(self.generated_at),
        }


@dataclass(frozen=True)
class DashboardAnalyticsView:
    """Display-only analytics dashboard view."""

    cash_flow_summary: DashboardAnalyticsSection
    allocation_summary: DashboardAnalyticsSection
    performance_summary: DashboardAnalyticsSection
    risk_summary: DashboardAnalyticsSection
    pipeline_summary: DashboardAnalyticsSection

    @classmethod
    def from_snapshot(
        cls,
        snapshot: Any | None,
    ) -> "DashboardAnalyticsView":
        """Build display sections from analytics-compatible data."""

        payload = _snapshot_payload(snapshot)
        generated_at = _get_value(payload, "created_at")
        metadata = _metadata(payload)
        return cls(
            cash_flow_summary=_cash_flow_section(payload, generated_at),
            allocation_summary=_allocation_section(payload, generated_at),
            performance_summary=_performance_section(payload, generated_at),
            risk_summary=_risk_section(payload, generated_at),
            pipeline_summary=_pipeline_section(metadata, generated_at),
        )

    def sections(self) -> tuple[DashboardAnalyticsSection, ...]:
        """Return sections in display order."""

        return (
            self.cash_flow_summary,
            self.allocation_summary,
            self.performance_summary,
            self.risk_summary,
            self.pipeline_summary,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe analytics view."""

        return {
            "sections": [section.to_dict() for section in self.sections()],
        }


def _cash_flow_section(
    payload: dict[str, Any],
    generated_at: Any,
) -> DashboardAnalyticsSection:
    net_cash_flow = _get_value(payload, "net_cash_flow")
    cash_inflow = _get_value(payload, "cash_inflow")
    cash_outflow = _get_value(payload, "cash_outflow")
    has_data = any(value is not None for value in (
        net_cash_flow,
        cash_inflow,
        cash_outflow,
    ))
    return DashboardAnalyticsSection(
        title="Cash Flow Summary",
        status="ready" if has_data else "empty",
        summary=(
            f"Net cash flow: {net_cash_flow}"
            if has_data else "No cash flow analytics available."
        ),
        details={
            "cash_inflow": cash_inflow,
            "cash_outflow": cash_outflow,
            "net_cash_flow": net_cash_flow,
        },
        generated_at=generated_at,
    )


def _allocation_section(
    payload: dict[str, Any],
    generated_at: Any,
) -> DashboardAnalyticsSection:
    weights = _get_value(payload, "asset_class_weights") or {}
    return DashboardAnalyticsSection(
        title="Allocation Summary",
        status="ready" if weights else "empty",
        summary=(
            f"{len(weights)} asset classes available."
            if weights else "No allocation analytics available."
        ),
        details={"asset_class_weights": dict(weights)},
        generated_at=generated_at,
    )


def _performance_section(
    payload: dict[str, Any],
    generated_at: Any,
) -> DashboardAnalyticsSection:
    unrealized_gain = _get_value(payload, "unrealized_gain")
    unrealized_return = _get_value(payload, "unrealized_return")
    total_market_value = _get_value(payload, "total_market_value")
    has_data = any(value is not None for value in (
        unrealized_gain,
        unrealized_return,
        total_market_value,
    ))
    return DashboardAnalyticsSection(
        title="Performance Summary",
        status="ready" if has_data else "empty",
        summary=(
            f"Unrealized return: {unrealized_return}"
            if has_data else "No performance analytics available."
        ),
        details={
            "total_cost": _get_value(payload, "total_cost"),
            "total_market_value": total_market_value,
            "unrealized_gain": unrealized_gain,
            "unrealized_return": unrealized_return,
        },
        generated_at=generated_at,
    )


def _risk_section(
    payload: dict[str, Any],
    generated_at: Any,
) -> DashboardAnalyticsSection:
    risk_score = _get_value(payload, "risk_score")
    risk_level = _get_value(payload, "risk_level")
    has_data = risk_score is not None or risk_level is not None
    return DashboardAnalyticsSection(
        title="Risk Summary",
        status="ready" if has_data else "empty",
        summary=(
            f"Risk level: {risk_level or 'UNKNOWN'}"
            if has_data else "No risk analytics available."
        ),
        details={
            "risk_score": risk_score,
            "risk_level": risk_level,
        },
        generated_at=generated_at,
    )


def _pipeline_section(
    metadata: dict[str, Any],
    generated_at: Any,
) -> DashboardAnalyticsSection:
    source_pipeline_id = metadata.get("source_pipeline_id")
    has_data = bool(metadata)
    return DashboardAnalyticsSection(
        title="Pipeline Summary",
        status="ready" if has_data else "empty",
        summary=(
            f"Source pipeline: {source_pipeline_id}"
            if source_pipeline_id else "No pipeline metadata available."
        ),
        details=metadata,
        generated_at=generated_at,
    )


def _snapshot_payload(snapshot: Any | None) -> dict[str, Any]:
    if snapshot is None:
        return {}
    if isinstance(snapshot, dict):
        return dict(snapshot)
    if hasattr(snapshot, "to_dict"):
        return snapshot.to_dict()
    return {}


def _metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        return dict(metadata)
    return {}


def _get_value(source: dict[str, Any], field_name: str) -> Any:
    return source.get(field_name)


def _format_optional_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
