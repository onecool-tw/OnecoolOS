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
from onecool_os.runtime import RuntimeSession
from onecool_os.sync import CollectionDifference


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
        runtime_session: RuntimeSession | None = None,
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
            collection_health_section(runtime_session, generated_at),
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


def collection_health_section(
    runtime_session: RuntimeSession | None,
    generated_at: datetime | None = None,
) -> CollectibleDashboardSection:
    """Return a presentation-only collection health section."""

    if runtime_session is None:
        return CollectibleDashboardSection(
            section_id="collection-health",
            title="Collection Health",
            content={
                "status": "empty",
                "message": "Collection Sync has not run yet.",
            },
            generated_at=generated_at,
        )

    report = runtime_session.sync_report
    differences = runtime_session.collection_differences()
    return CollectibleDashboardSection(
        section_id="collection-health",
        title="Collection Health",
        content={
            "status": "ready",
            "runtime_state": _runtime_state(runtime_session),
            "collection_health_score": runtime_session.collection_health,
            "imported_records": report.imported_records,
            "asset_master_records": report.asset_master_records,
            "matched_records": report.matched_records,
            "total_differences": len(differences),
            "critical_issues": len(runtime_session.critical_sync_issues()),
            "high_priority_issues": len(
                runtime_session.high_priority_sync_issues()
            ),
            "metadata_issues": len(runtime_session.metadata_sync_issues()),
            "difference_summary": _difference_summary(differences),
            "issue_details": _issue_details(differences),
            "message": (
                "Asset Master not loaded. Collection integrity comparison is "
                "limited."
                if report.asset_master_records == 0
                else None
            ),
        },
        generated_at=generated_at or runtime_session.generated_at,
    )


def collection_health_lines(
    runtime_session: RuntimeSession | None,
) -> tuple[str, ...]:
    """Return deterministic terminal lines for runtime collection health."""

    section = collection_health_section(runtime_session)
    content = section.content or {}
    lines = [
        "",
        "Collection Health",
        "-----------------",
    ]
    if runtime_session is None:
        lines.append("Collection Sync has not run yet.")
        return tuple(lines)

    difference_summary = content.get("difference_summary") or {}
    issue_details = content.get("issue_details") or []
    lines.extend(
        (
            f"Runtime State: {content['runtime_state']}",
            f"Collection Health Score: {content['collection_health_score']}",
            f"Imported Records: {content['imported_records']}",
            f"Asset Master Records: {content['asset_master_records']}",
            f"Matched Records: {content['matched_records']}",
            f"Total Differences: {content['total_differences']}",
            f"Critical Issues: {content['critical_issues']}",
            f"High Priority Issues: {content['high_priority_issues']}",
            f"Metadata Issues: {content['metadata_issues']}",
            "Difference Summary",
        )
    )
    for difference_type in _DIFFERENCE_SUMMARY_TYPES:
        lines.append(
            f"  {_DIFFERENCE_LABELS[difference_type]}: "
            f"{difference_summary.get(difference_type, 0)}"
        )
    lines.append("Issue Details")
    if issue_details:
        lines.extend(
            (
                f"  {item['severity']} {item['difference_type']} "
                f"{item['cert_number']}: {item['description']}"
            )
            for item in issue_details
        )
    else:
        lines.append("  None")
    if content.get("message"):
        lines.append(content["message"])
    return tuple(lines)


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


_DIFFERENCE_SUMMARY_TYPES = (
    "MISSING_IN_ASSET_MASTER",
    "MISSING_IN_IMPORT",
    "NEW_CARD",
    "DUPLICATE_CERT",
    "DUPLICATE_ASSET",
    "GRADE_CHANGED",
    "GRADE_ISSUER_CHANGED",
    "EBAY_URL_MISSING",
    "PSA_URL_MISSING",
    "TARGET_PRICE_MISSING",
    "NOTES_CHANGED",
)
_DIFFERENCE_LABELS = {
    "MISSING_IN_ASSET_MASTER": "Missing in Asset Master",
    "MISSING_IN_IMPORT": "Missing in Import",
    "NEW_CARD": "New Cards",
    "DUPLICATE_CERT": "Duplicate Certs",
    "DUPLICATE_ASSET": "Duplicate Assets",
    "GRADE_CHANGED": "Grade Changes",
    "GRADE_ISSUER_CHANGED": "Grade Issuer Changes",
    "EBAY_URL_MISSING": "Missing eBay URLs",
    "PSA_URL_MISSING": "Missing PSA URLs",
    "TARGET_PRICE_MISSING": "Target Price Missing",
    "NOTES_CHANGED": "Notes Changed",
}


def _runtime_state(runtime_session: RuntimeSession) -> str:
    if runtime_session.has_critical_sync_issues():
        return "CRITICAL"
    if runtime_session.has_sync_issues():
        return "DEGRADED"
    return "HEALTHY"


def _difference_summary(
    differences: tuple[CollectionDifference, ...],
) -> dict[str, int]:
    return {
        difference_type: sum(
            1
            for difference in differences
            if difference.difference_type == difference_type
        )
        for difference_type in _DIFFERENCE_SUMMARY_TYPES
    }


def _issue_details(
    differences: tuple[CollectionDifference, ...],
) -> list[dict[str, str]]:
    return [
        {
            "severity": difference.severity,
            "difference_type": difference.difference_type,
            "cert_number": difference.cert_number,
            "description": difference.description,
        }
        for difference in sorted(
            differences,
            key=lambda item: (
                item.severity,
                item.difference_type,
                item.cert_number,
                item.description,
            ),
        )
    ]


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
