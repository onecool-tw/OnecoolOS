from datetime import datetime
from datetime import timezone

from onecool_os.analytics import TimelineSnapshot
from onecool_os.analytics import TrendDirection
from onecool_os.analytics import TrendStrength
from onecool_os.business_logic import BusinessLogicResult
from onecool_os.dashboard import CollectibleDashboard
from onecool_os.dashboard import CollectibleDashboardBuilder
from onecool_os.decision.models import DecisionResult
from onecool_os.radar import RadarSignal
from onecool_os.radar import RadarSnapshot


REFERENCE = datetime(2026, 7, 5, tzinfo=timezone.utc)


def test_builder() -> None:
    dashboard = CollectibleDashboardBuilder().build(
        business_logic_result=business_logic_result(),
        timeline_snapshot=timeline_snapshot(),
        radar_snapshot=radar_snapshot(),
    )

    assert isinstance(dashboard, CollectibleDashboard)
    assert dashboard.asset_id == "CARD-001"
    assert dashboard.dashboard_id == "collectible-dashboard:CARD-001"


def test_sections() -> None:
    dashboard = CollectibleDashboardBuilder().build(
        business_logic_result=business_logic_result(),
        timeline_snapshot=timeline_snapshot(),
        radar_snapshot=radar_snapshot(),
    )

    assert tuple(section.section_id for section in dashboard.sections) == (
        "collection-summary",
        "collection-health",
        "market-intelligence",
        "market-quality",
        "timeline-summary",
        "radar-changes",
        "review-queue",
        "warning-summary",
    )


def test_empty_dashboard() -> None:
    dashboard = CollectibleDashboardBuilder().build()

    assert dashboard.asset_id == "unknown"
    assert dashboard.sections[1].content["status"] == "empty"
    assert dashboard.sections[4].content["status"] == "empty"
    assert dashboard.sections[5].content["status"] == "empty"


def test_warnings() -> None:
    dashboard = CollectibleDashboardBuilder().build(
        business_logic_result=business_logic_result(
            warnings=("Low Confidence",),
        ),
        timeline_snapshot=timeline_snapshot(warnings=("Source Conflict",)),
        radar_snapshot=radar_snapshot(warnings=("Low Confidence",)),
        decision_result=decision_result(warnings=("Manual Review",)),
    )

    warning_section = section(dashboard, "warning-summary")
    assert warning_section.content["warnings"] == [
        "Low Confidence",
        "Source Conflict",
        "Manual Review",
    ]


def test_review_queue() -> None:
    dashboard = CollectibleDashboardBuilder().build(
        business_logic_result=business_logic_result(
            review_status="NEEDS_REVIEW",
        ),
        decision_result=decision_result(),
    )

    review_section = section(dashboard, "review-queue")
    assert review_section.content["review_status"] == "NEEDS_REVIEW"
    assert review_section.content["decision"]["result_id"] == "decision-1"


def test_timeline_rendering() -> None:
    dashboard = CollectibleDashboardBuilder().build(
        timeline_snapshot=timeline_snapshot(
            trend_summary=("Market Quality Improving",),
        )
    )

    timeline_section = section(dashboard, "timeline-summary")
    assert timeline_section.content["trend_direction"] == "IMPROVING"
    assert timeline_section.content["trend_summary"] == [
        "Market Quality Improving"
    ]


def test_radar_rendering() -> None:
    dashboard = CollectibleDashboardBuilder().build(
        radar_snapshot=radar_snapshot(summary=("Liquidity Deteriorated",))
    )

    radar_section = section(dashboard, "radar-changes")
    assert radar_section.content["change_summary"] == [
        "Liquidity Deteriorated"
    ]
    assert radar_section.content["escalated_signals"][0]["title"] == (
        "Liquidity Deteriorated"
    )


def test_deterministic_output() -> None:
    builder = CollectibleDashboardBuilder()
    inputs = {
        "business_logic_result": business_logic_result(),
        "timeline_snapshot": timeline_snapshot(),
        "radar_snapshot": radar_snapshot(),
        "decision_result": decision_result(),
    }

    first = builder.build(**inputs)
    second = builder.build(**inputs)

    assert first.to_dict() == second.to_dict()


def business_logic_result(
    *,
    review_status: str = "READY_FOR_REVIEW",
    warnings: tuple[str, ...] = (),
) -> BusinessLogicResult:
    return BusinessLogicResult(
        result_id="business-logic-1",
        engine_name="collectible_intelligence",
        engine_version="v1",
        metric_type="EXPOSURE",
        payload={
            "market_quality": "STRONG",
            "valuation_quality": "STRONG",
            "liquidity_quality": "NORMAL",
            "source_quality": "STRONG",
            "review_status": review_status,
            "warnings": list(warnings),
            "market_intelligence": {
                "asset_id": "CARD-001",
                "confidence_score": 88,
                "confidence_level": "HIGH",
            },
        },
        generated_at=REFERENCE,
        tags=["collectible"],
    )


def timeline_snapshot(
    *,
    trend_summary: tuple[str, ...] = ("Market Quality Improving",),
    warnings: tuple[str, ...] = (),
) -> TimelineSnapshot:
    return TimelineSnapshot(
        snapshot_id="timeline-1",
        asset_id="CARD-001",
        generated_at=REFERENCE,
        reference_datetime=REFERENCE,
        previous_snapshots=(),
        current_snapshot=radar_snapshot(),
        trend_direction=TrendDirection.IMPROVING,
        trend_strength=TrendStrength.MODERATE,
        trend_summary=trend_summary,
        signal_count=1,
        new_signal_count=1,
        resolved_signal_count=0,
        escalated_signal_count=1,
        changed_signal_count=1,
        confidence_trend=TrendDirection.IMPROVING,
        liquidity_trend=TrendDirection.DETERIORATING,
        agreement_trend=TrendDirection.STABLE,
        warnings=warnings,
        radar_snapshot_ids=("radar-1",),
    )


def radar_snapshot(
    *,
    summary: tuple[str, ...] = ("Liquidity Deteriorated",),
    warnings: tuple[str, ...] = (),
) -> RadarSnapshot:
    signal = RadarSignal(
        signal_id="signal-1",
        signal_type="LIQUIDITY_CHANGED",
        severity="HIGH",
        title="Liquidity Deteriorated",
        description="Liquidity changed from STRONG to WEAK.",
        created_at=REFERENCE,
        payload={"field": "liquidity_quality"},
    )
    return RadarSnapshot(
        snapshot_id="radar-1",
        asset_id="CARD-001",
        generated_at=REFERENCE,
        reference_datetime=REFERENCE,
        current_signals=(signal,),
        previous_signals=(),
        new_signals=(),
        resolved_signals=(),
        changed_signals=(signal,),
        escalated_signals=(signal,),
        change_summary=summary,
        warning_summary=warnings,
        source_snapshot_ids=("business-logic-1",),
    )


def decision_result(
    *,
    warnings: tuple[str, ...] = (),
) -> DecisionResult:
    return DecisionResult(
        result_id="decision-1",
        context_id="ctx-1",
        candidates=(),
        summary="Decision context ready.",
        warnings=list(warnings),
        generated_at=REFERENCE,
    )


def section(dashboard: CollectibleDashboard, section_id: str):
    return next(
        item for item in dashboard.sections
        if item.section_id == section_id
    )
