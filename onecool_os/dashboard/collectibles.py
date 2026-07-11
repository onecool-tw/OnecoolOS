"""Collectible Radar dashboard presentation layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
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
from onecool_os.portfolio import PortfolioNavSnapshot
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
        portfolio_nav_snapshots: tuple[PortfolioNavSnapshot, ...]
        | list[PortfolioNavSnapshot]
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
        if portfolio_nav_snapshots is not None:
            sections.extend(
                portfolio_nav_sections(
                    portfolio_nav_snapshots,
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


def portfolio_nav_sections(
    snapshots: tuple[PortfolioNavSnapshot, ...] | list[PortfolioNavSnapshot],
    generated_at: datetime | None = None,
) -> tuple[CollectibleDashboardSection, ...]:
    """Return presentation-only NAV dashboard sections."""

    nav_snapshots = tuple(snapshots or ())
    if not nav_snapshots:
        return (
            CollectibleDashboardSection(
                section_id="portfolio-nav",
                title="Portfolio NAV",
                content={
                    "status": "empty",
                    "message": "Portfolio NAV is not available for the current runtime session.",
                },
                generated_at=generated_at,
            ),
        )

    ordered = tuple(sorted(nav_snapshots, key=lambda snapshot: snapshot.currency))
    sections: list[CollectibleDashboardSection] = []
    for snapshot in ordered:
        sections.append(
            CollectibleDashboardSection(
                section_id=f"portfolio-nav-{snapshot.currency.lower()}",
                title=f"Portfolio NAV - {snapshot.currency}",
                content=_portfolio_nav_content(snapshot),
                generated_at=generated_at or snapshot.generated_at,
            )
        )
    sections.append(
        CollectibleDashboardSection(
            section_id="valuation-coverage",
            title="Valuation Coverage",
            content={
                "status": "ready",
                "snapshots": [
                    _valuation_coverage_content(snapshot)
                    for snapshot in ordered
                ],
            },
            generated_at=generated_at or ordered[0].generated_at,
        )
    )
    sections.append(
        CollectibleDashboardSection(
            section_id="asset-nav-review",
            title="Asset NAV Review",
            content={
                "status": "ready",
                "rows": _asset_review_rows(ordered),
            },
            generated_at=generated_at or ordered[0].generated_at,
        )
    )
    return tuple(sections)


def portfolio_nav_lines(
    snapshots: tuple[PortfolioNavSnapshot, ...] | list[PortfolioNavSnapshot],
) -> tuple[str, ...]:
    """Return deterministic terminal lines for Portfolio NAV snapshots."""

    nav_snapshots = tuple(sorted(tuple(snapshots or ()), key=lambda item: item.currency))
    if not nav_snapshots:
        return (
            "",
            "Portfolio NAV",
            "-------------",
            "Portfolio NAV is not available for the current runtime session.",
        )

    lines: list[str] = []
    for snapshot in nav_snapshots:
        title = "Portfolio NAV" if len(nav_snapshots) == 1 else f"Portfolio NAV - {snapshot.currency}"
        lines.extend(
            (
                "",
                title,
                "-" * len(title),
                f"Currency: {snapshot.currency}",
                f"Status: {snapshot.status.value}",
                f"Status Meaning: {_nav_status_explanation(snapshot.status.value)}",
                f"Total Assets: {snapshot.total_assets}",
                f"Assets With Cost Basis: {snapshot.assets_with_cost}",
                f"Assets With Market Value: {snapshot.assets_with_market_value}",
                f"Verified Assets: {snapshot.verified_assets}",
                f"Review Required Assets: {snapshot.review_required_assets}",
                f"Estimated Assets: {snapshot.estimated_assets}",
                f"Missing Value Assets: {snapshot.missing_value_assets}",
                f"Total Cost Basis: {_money(snapshot.currency, snapshot.total_cost_basis, available=snapshot.assets_with_cost > 0)}",
                f"Total Market Value: {_money(snapshot.currency, snapshot.total_market_value, available=snapshot.assets_with_market_value > 0)}",
                f"Unrealized Gain / Loss: {_money(snapshot.currency, snapshot.unrealized_gain_loss, available=snapshot.unrealized_gain_loss is not None)}",
                f"ROI: {_percent(snapshot.roi_percent)}",
                f"Valuation Coverage: {_percent(snapshot.valuation_coverage_percent)}",
                f"Verified Coverage: {_percent(snapshot.verified_coverage_percent)}",
            )
        )

    lines.extend(("", "Valuation Coverage", "------------------"))
    for snapshot in nav_snapshots:
        lines.extend(
            (
                f"{snapshot.currency}",
                f"  Verified: {snapshot.verified_assets} / {snapshot.total_assets} ({_percent(snapshot.verified_coverage_percent)})",
                f"  Review Required: {snapshot.review_required_assets} / {snapshot.total_assets}",
                f"  Estimated: {snapshot.estimated_assets} / {snapshot.total_assets}",
                f"  Missing: {snapshot.missing_value_assets} / {snapshot.total_assets}",
            )
        )

    review_rows = _asset_review_rows(nav_snapshots)
    total_review_rows = sum(
        1
        for snapshot in nav_snapshots
        for line in snapshot.asset_lines
        if _line_needs_review(line)
    )
    lines.extend(("", "Asset NAV Review", "----------------"))
    if review_rows:
        for row in review_rows:
            lines.append(
                "  "
                f"{row['asset']} | Cert: {row['cert_number'] or 'N/A'} | "
                f"Cost: {row['cost_basis']} | Market: {row['market_value']} | "
                f"Gain/Loss: {row['gain_loss']} | ROI: {row['roi']} | "
                f"Coverage: {row['coverage_status']} | Source: {row['valuation_source'] or 'N/A'} | "
                f"Date: {row['valuation_date'] or 'N/A'} | Warnings: {row['warning_summary']}"
            )
        omitted = max(total_review_rows - len(review_rows), 0)
        if omitted:
            lines.append(f"  Omitted Review Rows: {omitted}")
    else:
        lines.append("  None")
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


def _portfolio_nav_content(snapshot: PortfolioNavSnapshot) -> dict[str, Any]:
    return {
        "status": "ready",
        "currency": snapshot.currency,
        "nav_status": snapshot.status.value,
        "status_explanation": _nav_status_explanation(snapshot.status.value),
        "total_assets": snapshot.total_assets,
        "assets_with_cost_basis": snapshot.assets_with_cost,
        "assets_with_market_value": snapshot.assets_with_market_value,
        "verified_assets": snapshot.verified_assets,
        "review_required_assets": snapshot.review_required_assets,
        "estimated_assets": snapshot.estimated_assets,
        "missing_value_assets": snapshot.missing_value_assets,
        "total_cost_basis": _money_value(snapshot.total_cost_basis, snapshot.assets_with_cost > 0),
        "total_market_value": _money_value(snapshot.total_market_value, snapshot.assets_with_market_value > 0),
        "unrealized_gain_loss": _money_value(snapshot.unrealized_gain_loss, snapshot.unrealized_gain_loss is not None),
        "roi_percent": _percent_value(snapshot.roi_percent),
        "valuation_coverage_percent": _percent_value(snapshot.valuation_coverage_percent),
        "verified_coverage_percent": _percent_value(snapshot.verified_coverage_percent),
        "warnings": list(snapshot.warnings),
    }


def _valuation_coverage_content(snapshot: PortfolioNavSnapshot) -> dict[str, Any]:
    return {
        "currency": snapshot.currency,
        "total_assets": snapshot.total_assets,
        "verified": {
            "count": snapshot.verified_assets,
            "percent": _percent_value(snapshot.verified_coverage_percent),
        },
        "review_required": {
            "count": snapshot.review_required_assets,
        },
        "estimated": {
            "count": snapshot.estimated_assets,
        },
        "missing": {
            "count": snapshot.missing_value_assets,
        },
    }


def _asset_review_rows(
    snapshots: tuple[PortfolioNavSnapshot, ...],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for snapshot in snapshots:
        for line in snapshot.asset_lines:
            if not _line_needs_review(line):
                continue
            rows.append(
                {
                    "currency": snapshot.currency,
                    "asset": line.asset_name,
                    "asset_id": line.asset_id,
                    "cert_number": line.cert_number,
                    "cost_basis": _money(snapshot.currency, line.cost_basis, available=line.cost_basis is not None),
                    "market_value": _money(snapshot.currency, line.market_value, available=line.market_value is not None),
                    "gain_loss": _money(snapshot.currency, line.unrealized_gain_loss, available=line.unrealized_gain_loss is not None),
                    "roi": _percent(line.roi_percent),
                    "coverage_status": line.coverage_status.value,
                    "valuation_source": line.valuation_source,
                    "valuation_date": line.valuation_date.isoformat() if line.valuation_date else None,
                    "warning_summary": _warning_summary(line.warnings),
                }
            )
    return sorted(
        rows,
        key=lambda row: (
            row["coverage_status"],
            row["asset"],
            row["asset_id"],
        ),
    )[:limit]


def _line_needs_review(line: Any) -> bool:
    return bool(line.warnings) or line.coverage_status.value != "VERIFIED"


def _warning_summary(warnings: tuple[str, ...]) -> str:
    if not warnings:
        return "None"
    return "; ".join(warnings)


def _nav_status_explanation(status: str) -> str:
    return {
        "COMPLETE": "All assets in this currency snapshot have eligible market values.",
        "PARTIAL": "Some assets have market values; others remain missing or estimated.",
        "INSUFFICIENT_DATA": "There are not enough eligible market values for a meaningful NAV.",
        "CURRENCY_MISMATCH": "Currency differences prevent valid aggregation.",
    }.get(status, "Unknown NAV status.")


def _money(currency: str, value: Decimal | None, *, available: bool) -> str:
    if value is None or not available:
        return "N/A"
    return f"{currency} {value:,.2f}"


def _money_value(value: Decimal | None, available: bool) -> str | None:
    if value is None or not available:
        return None
    return f"{value:,.2f}"


def _percent(value: Decimal | None) -> str:
    if value is None:
        return "N/A"
    return f"{value.quantize(Decimal('0.01'))}%"


def _percent_value(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}%"


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
