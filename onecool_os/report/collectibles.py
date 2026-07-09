"""Collectible Daily Radar Report builder."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from onecool_os.dashboard.collectibles import CollectibleDashboard
from onecool_os.report.builder import BaseReportBuilder
from onecool_os.report.models import CollectibleDailyRadarReport
from onecool_os.report.validation import ReportError


class CollectibleDailyRadarReportBuilder(BaseReportBuilder):
    """Assemble Collectible Dashboard output into a daily report."""

    builder_name = "collectible_daily_radar_report"

    def build(
        self,
        dashboard: CollectibleDashboard,
        *,
        reference_datetime: datetime | None = None,
    ) -> CollectibleDailyRadarReport:
        """Build a presentation-only Daily Radar Report."""

        if not isinstance(dashboard, CollectibleDashboard):
            raise ReportError("dashboard must be a CollectibleDashboard.")
        section_map = _sections(dashboard)
        collection = section_map.get("collection-summary", {})
        market_intelligence = section_map.get("market-intelligence", {})
        market_quality = section_map.get("market-quality", {})
        timeline = section_map.get("timeline-summary", {})
        radar = section_map.get("radar-changes", {})
        review = section_map.get("review-queue", {})
        warning = section_map.get("warning-summary", {})
        performance = section_map.get("portfolio-performance", {})
        performance_summary = section_map.get("performance-summary", {})
        market_payload = market_intelligence.get("market_intelligence") or {}
        review_status = review.get("review_status")
        return CollectibleDailyRadarReport(
            report_id=f"daily-radar:{dashboard.dashboard_id}",
            generated_at=dashboard.generated_at,
            reference_datetime=reference_datetime or dashboard.generated_at,
            total_cards=collection.get("total_cards", 0),
            total_market_value=collection.get("total_market_value", 0),
            total_cost_basis=collection.get("total_cost_basis", 0),
            unrealized_gain_loss=collection.get("unrealized_gain_loss", 0),
            valuation_coverage=collection.get("valuation_coverage", 0),
            market_quality=market_quality.get("market_quality"),
            confidence_summary={
                "confidence_score": market_payload.get("confidence_score"),
                "confidence_level": market_payload.get("confidence_level"),
            },
            agreement_summary={
                "source_quality": market_quality.get("source_quality"),
                "agreement_level": market_payload.get("agreement_level"),
            },
            liquidity_summary={
                "liquidity_quality": market_quality.get("liquidity_quality"),
                "liquidity_level": market_payload.get("liquidity_level"),
            },
            new_signals=radar.get("new_signals", ()),
            resolved_signals=radar.get("resolved_signals", ()),
            changed_signals=radar.get("changed_signals", ()),
            escalated_signals=radar.get("escalated_signals", ()),
            trend_direction=timeline.get("trend_direction"),
            trend_strength=timeline.get("trend_strength"),
            trend_summary=timeline.get("trend_summary", ()),
            ready_for_review=1 if review_status == "READY_FOR_REVIEW" else 0,
            needs_review=1 if review_status == "NEEDS_REVIEW" else 0,
            blocked=1 if review_status == "BLOCKED" else 0,
            performance_summary=_performance_summary(performance),
            top_movers=_top_movers(performance_summary),
            warnings=_warnings(warning, performance_summary),
            dashboard_snapshot_id=dashboard.dashboard_id,
        )


def _sections(dashboard: CollectibleDashboard) -> dict[str, dict[str, Any]]:
    return {
        section.section_id: dict(section.content or {})
        for section in dashboard.sections
    }


def _performance_summary(performance: dict[str, Any]) -> dict[str, Any]:
    return {
        "total_cost_basis": performance.get("total_cost_basis"),
        "total_market_value": performance.get("total_market_value"),
        "total_unrealized_gain_loss": performance.get(
            "total_unrealized_gain_loss"
        ),
        "total_unrealized_percent": performance.get(
            "total_unrealized_percent"
        ),
        "performing_assets": performance.get("performing_asset_count", 0),
        "missing_valuations": performance.get("missing_valuation_count", 0),
        "missing_cost_basis": performance.get("missing_cost_basis_count", 0),
    }


def _top_movers(performance_summary: dict[str, Any]) -> dict[str, Any]:
    summary = performance_summary.get("summary") or {}
    return {
        "top_gainers": list(summary.get("top_gainers") or ()),
        "top_losers": list(summary.get("top_losers") or ()),
    }


def _warnings(
    warning: dict[str, Any],
    performance_summary: dict[str, Any],
) -> tuple[str, ...]:
    warnings: list[str] = []
    warnings.extend(warning.get("warnings") or ())
    warnings.extend(performance_summary.get("warnings") or ())
    return tuple(dict.fromkeys(warnings))
