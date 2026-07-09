"""Collectible Radar dashboard presentation layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from onecool_os.analytics.timeline import TimelineSnapshot
from onecool_os.business_logic.results import BusinessLogicResult
from onecool_os.dashboard.performance import PerformanceDashboardBuilder
from onecool_os.dashboard.validation import DashboardError
from onecool_os.dashboard.validation import parse_optional_datetime
from onecool_os.dashboard.validation import parse_optional_dict
from onecool_os.dashboard.validation import require_text
from onecool_os.decision.models import DecisionResult
from onecool_os.performance import InvestmentPerformanceSnapshot
from onecool_os.radar.models import RadarSnapshot


@dataclass(frozen=True)
class CollectibleDashboardSection:
    """Display-only Collectible Radar section."""

    section_id: str
    title: str
    content: dict[str, Any] | None = None
    generated_at: datetime | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "section_id",
            require_text(self.section_id, "section_id"),
        )
        object.__setattr__(self, "title", require_text(self.title, "title"))
        object.__setattr__(
            self,
            "content",
            parse_optional_dict(self.content, "content"),
        )
        object.__setattr__(
            self,
            "generated_at",
            parse_optional_datetime(self.generated_at, "generated_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe section."""

        return {
            "section_id": self.section_id,
            "title": self.title,
            "content": self.content,
            "generated_at": (
                self.generated_at.isoformat()
                if self.generated_at is not None
                else None
            ),
        }


@dataclass(frozen=True)
class CollectibleDashboard:
    """Display-only Collectible Radar dashboard."""

    dashboard_id: str
    asset_id: str
    generated_at: datetime | str | None = None
    sections: tuple[CollectibleDashboardSection, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dashboard_id",
            require_text(self.dashboard_id, "dashboard_id"),
        )
        object.__setattr__(
            self,
            "asset_id",
            require_text(self.asset_id, "asset_id"),
        )
        object.__setattr__(
            self,
            "generated_at",
            parse_optional_datetime(self.generated_at, "generated_at"),
        )
        sections = tuple(self.sections or ())
        _validate_unique_sections(sections)
        object.__setattr__(self, "sections", sections)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dashboard payload."""

        return {
            "dashboard_id": self.dashboard_id,
            "asset_id": self.asset_id,
            "generated_at": (
                self.generated_at.isoformat()
                if self.generated_at is not None
                else None
            ),
            "sections": [section.to_dict() for section in self.sections],
        }


class CollectibleDashboardBuilder:
    """Assemble Collectible Radar outputs into presentation sections."""

    def build(
        self,
        business_logic_result: BusinessLogicResult | None = None,
        timeline_snapshot: TimelineSnapshot | None = None,
        radar_snapshot: RadarSnapshot | None = None,
        decision_result: DecisionResult | None = None,
        performance_snapshots: tuple[InvestmentPerformanceSnapshot, ...]
        | list[InvestmentPerformanceSnapshot]
        | None = None,
        collectible_assets: tuple[Any, ...] | list[Any] | None = None,
    ) -> CollectibleDashboard:
        """Build a display-only Collectible Radar dashboard."""

        generated_at = _generated_at(
            timeline_snapshot,
            radar_snapshot,
            business_logic_result,
            decision_result,
        )
        asset_id = _asset_id(
            business_logic_result,
            timeline_snapshot,
            radar_snapshot,
        )
        sections = [
            _collection_summary(asset_id, generated_at),
            _market_intelligence_section(business_logic_result, generated_at),
            _market_quality_section(business_logic_result, generated_at),
            _timeline_section(timeline_snapshot, generated_at),
            _radar_section(radar_snapshot, generated_at),
        ]
        if performance_snapshots is not None:
            sections.extend(
                _performance_sections(
                    performance_snapshots,
                    collectible_assets,
                    generated_at,
                )
            )
        sections.extend((
            _review_queue_section(
                business_logic_result,
                decision_result,
                generated_at,
            ),
            _warning_section(
                business_logic_result,
                timeline_snapshot,
                radar_snapshot,
                decision_result,
                generated_at,
            ),
        ))
        return CollectibleDashboard(
            dashboard_id=f"collectible-dashboard:{asset_id}",
            asset_id=asset_id,
            generated_at=generated_at,
            sections=tuple(sections),
        )


def _collection_summary(
    asset_id: str,
    generated_at: datetime | None,
) -> CollectibleDashboardSection:
    return CollectibleDashboardSection(
        section_id="collection-summary",
        title="Collection Summary",
        content={
            "asset_id": asset_id,
            "status": "ready" if asset_id != "unknown" else "empty",
        },
        generated_at=generated_at,
    )


def _market_intelligence_section(
    result: BusinessLogicResult | None,
    generated_at: datetime | None,
) -> CollectibleDashboardSection:
    payload = _payload(result)
    market_intelligence = payload.get("market_intelligence") or {}
    return CollectibleDashboardSection(
        section_id="market-intelligence",
        title="Market Intelligence",
        content={
            "status": "ready" if market_intelligence else "empty",
            "market_intelligence": dict(market_intelligence),
        },
        generated_at=generated_at,
    )


def _market_quality_section(
    result: BusinessLogicResult | None,
    generated_at: datetime | None,
) -> CollectibleDashboardSection:
    payload = _payload(result)
    return CollectibleDashboardSection(
        section_id="market-quality",
        title="Market Quality",
        content={
            "status": "ready" if payload else "empty",
            "market_quality": payload.get("market_quality"),
            "valuation_quality": payload.get("valuation_quality"),
            "liquidity_quality": payload.get("liquidity_quality"),
            "source_quality": payload.get("source_quality"),
        },
        generated_at=generated_at,
    )


def _timeline_section(
    timeline: TimelineSnapshot | None,
    generated_at: datetime | None,
) -> CollectibleDashboardSection:
    return CollectibleDashboardSection(
        section_id="timeline-summary",
        title="Timeline Summary",
        content=(
            {
                "status": "ready",
                "trend_direction": timeline.trend_direction.value,
                "trend_strength": timeline.trend_strength.value,
                "trend_summary": list(timeline.trend_summary),
                "signal_count": timeline.signal_count,
                "new_signal_count": timeline.new_signal_count,
                "resolved_signal_count": timeline.resolved_signal_count,
                "escalated_signal_count": timeline.escalated_signal_count,
                "changed_signal_count": timeline.changed_signal_count,
            }
            if timeline is not None
            else {"status": "empty"}
        ),
        generated_at=generated_at,
    )


def _radar_section(
    radar: RadarSnapshot | None,
    generated_at: datetime | None,
) -> CollectibleDashboardSection:
    return CollectibleDashboardSection(
        section_id="radar-changes",
        title="Radar Changes",
        content=(
            {
                "status": "ready",
                "change_summary": list(radar.change_summary),
                "new_signals": [signal.to_dict() for signal in radar.new_signals],
                "resolved_signals": [
                    signal.to_dict() for signal in radar.resolved_signals
                ],
                "changed_signals": [
                    signal.to_dict() for signal in radar.changed_signals
                ],
                "escalated_signals": [
                    signal.to_dict() for signal in radar.escalated_signals
                ],
            }
            if radar is not None
            else {"status": "empty"}
        ),
        generated_at=generated_at,
    )


def _review_queue_section(
    result: BusinessLogicResult | None,
    decision: DecisionResult | None,
    generated_at: datetime | None,
) -> CollectibleDashboardSection:
    payload = _payload(result)
    decision_payload = decision.to_dict() if decision is not None else None
    return CollectibleDashboardSection(
        section_id="review-queue",
        title="Review Queue",
        content={
            "status": "ready" if payload or decision_payload else "empty",
            "review_status": payload.get("review_status"),
            "decision": decision_payload,
        },
        generated_at=generated_at,
    )


def _performance_sections(
    performance_snapshots: tuple[InvestmentPerformanceSnapshot, ...]
    | list[InvestmentPerformanceSnapshot],
    collectible_assets: tuple[Any, ...] | list[Any] | None,
    generated_at: datetime | None,
) -> tuple[CollectibleDashboardSection, ...]:
    dashboard = PerformanceDashboardBuilder().build(
        performance_snapshots=performance_snapshots,
        collectible_assets=collectible_assets,
        generated_at=generated_at,
    )
    return (
        CollectibleDashboardSection(
            section_id="portfolio-performance",
            title="Portfolio Performance",
            content=dashboard.portfolio_performance,
            generated_at=dashboard.generated_at,
        ),
        CollectibleDashboardSection(
            section_id="asset-performance-table",
            title="Asset Performance Table",
            content={
                "status": (
                    "ready"
                    if dashboard.asset_performance_table
                    else "empty"
                ),
                "rows": [
                    dict(row) for row in dashboard.asset_performance_table
                ],
            },
            generated_at=dashboard.generated_at,
        ),
        CollectibleDashboardSection(
            section_id="performance-summary",
            title="Performance Summary",
            content={
                "status": "ready" if performance_snapshots else "empty",
                "summary": dashboard.summary,
                "warnings": list(dashboard.warnings),
            },
            generated_at=dashboard.generated_at,
        ),
    )


def _warning_section(
    result: BusinessLogicResult | None,
    timeline: TimelineSnapshot | None,
    radar: RadarSnapshot | None,
    decision: DecisionResult | None,
    generated_at: datetime | None,
) -> CollectibleDashboardSection:
    warnings: list[str] = []
    warnings.extend(_payload(result).get("warnings") or ())
    if timeline is not None:
        warnings.extend(timeline.warnings)
    if radar is not None:
        warnings.extend(radar.warning_summary)
    if decision is not None:
        warnings.extend(decision.warnings)
    return CollectibleDashboardSection(
        section_id="warning-summary",
        title="Warning Summary",
        content={
            "status": "ready" if warnings else "empty",
            "warnings": list(dict.fromkeys(warnings)),
        },
        generated_at=generated_at,
    )


def _payload(result: BusinessLogicResult | None) -> dict[str, Any]:
    if result is None:
        return {}
    return dict(result.payload or {})


def _generated_at(
    timeline: TimelineSnapshot | None,
    radar: RadarSnapshot | None,
    result: BusinessLogicResult | None,
    decision: DecisionResult | None,
) -> datetime | None:
    for source in (timeline, radar, result, decision):
        generated_at = getattr(source, "generated_at", None)
        if generated_at is not None:
            return generated_at
    return None


def _asset_id(
    result: BusinessLogicResult | None,
    timeline: TimelineSnapshot | None,
    radar: RadarSnapshot | None,
) -> str:
    if timeline is not None:
        return timeline.asset_id
    if radar is not None:
        return radar.asset_id
    market_intelligence = _payload(result).get("market_intelligence")
    if isinstance(market_intelligence, dict):
        asset_id = market_intelligence.get("asset_id")
        if asset_id:
            return str(asset_id)
    return "unknown"


def _validate_unique_sections(
    sections: tuple[CollectibleDashboardSection, ...],
) -> None:
    seen: set[str] = set()
    for section in sections:
        if section.section_id in seen:
            raise DashboardError(f"Duplicate section_id: {section.section_id}")
        seen.add(section.section_id)
