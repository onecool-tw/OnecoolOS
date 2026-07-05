from copy import deepcopy
from datetime import datetime
from datetime import timezone

from onecool_os.dashboard import CollectibleDashboard
from onecool_os.dashboard import CollectibleDashboardSection
from onecool_os.report import CollectibleDailyRadarReport
from onecool_os.report import CollectibleDailyRadarReportBuilder


REFERENCE = datetime(2026, 7, 5, tzinfo=timezone.utc)


def test_empty_report() -> None:
    report = CollectibleDailyRadarReportBuilder().build(
        CollectibleDashboard(
            dashboard_id="dashboard-empty",
            asset_id="unknown",
            generated_at=REFERENCE,
            sections=(),
        ),
        reference_datetime=REFERENCE,
    )

    assert report.total_cards == 0
    assert report.market_quality is None
    assert report.warnings == ()


def test_populated_report() -> None:
    report = CollectibleDailyRadarReportBuilder().build(
        dashboard(),
        reference_datetime=REFERENCE,
    )

    assert isinstance(report, CollectibleDailyRadarReport)
    assert report.total_cards == 12
    assert report.total_market_value == 5000
    assert report.market_quality == "STRONG"
    assert report.confidence_summary["confidence_score"] == 88


def test_section_ordering() -> None:
    report = CollectibleDailyRadarReportBuilder().build(
        dashboard(),
        reference_datetime=REFERENCE,
    )

    assert report.section_order() == (
        "collection_summary",
        "market_summary",
        "todays_changes",
        "timeline_summary",
        "review_queue",
        "warnings",
    )
    assert tuple(report.to_dict()["sections"]) == report.section_order()


def test_warning_rendering() -> None:
    report = CollectibleDailyRadarReportBuilder().build(
        dashboard(warnings=("Low Confidence", "Source Conflict")),
        reference_datetime=REFERENCE,
    )

    assert report.warnings == ("Low Confidence", "Source Conflict")
    assert report.to_dict()["sections"]["warnings"]["warnings"] == [
        "Low Confidence",
        "Source Conflict",
    ]


def test_review_queue_rendering() -> None:
    report = CollectibleDailyRadarReportBuilder().build(
        dashboard(review_status="NEEDS_REVIEW"),
        reference_datetime=REFERENCE,
    )

    assert report.ready_for_review == 0
    assert report.needs_review == 1
    assert report.blocked == 0


def test_timeline_rendering() -> None:
    report = CollectibleDailyRadarReportBuilder().build(
        dashboard(trend_summary=("Market Quality Improving",)),
        reference_datetime=REFERENCE,
    )

    assert report.trend_direction == "IMPROVING"
    assert report.trend_strength == "MODERATE"
    assert report.trend_summary == ("Market Quality Improving",)


def test_deterministic_output() -> None:
    source = dashboard()
    builder = CollectibleDailyRadarReportBuilder()

    first = builder.build(source, reference_datetime=REFERENCE)
    second = builder.build(source, reference_datetime=REFERENCE)

    assert first.to_dict() == second.to_dict()


def test_replay_support() -> None:
    reference = datetime(2026, 8, 1, tzinfo=timezone.utc)

    report = CollectibleDailyRadarReportBuilder().build(
        dashboard(),
        reference_datetime=reference,
    )

    assert report.reference_datetime == reference


def test_injected_reference_datetime() -> None:
    reference = datetime(2026, 8, 2, tzinfo=timezone.utc)

    report = CollectibleDailyRadarReportBuilder().build(
        dashboard(),
        reference_datetime=reference,
    )

    assert report.reference_datetime == reference
    assert report.generated_at == REFERENCE


def test_no_mutation() -> None:
    source = dashboard()
    before = deepcopy(source.to_dict())

    CollectibleDailyRadarReportBuilder().build(
        source,
        reference_datetime=REFERENCE,
    )

    assert source.to_dict() == before


def dashboard(
    *,
    review_status: str = "READY_FOR_REVIEW",
    trend_summary: tuple[str, ...] = ("Market Quality Improving",),
    warnings: tuple[str, ...] = (),
) -> CollectibleDashboard:
    return CollectibleDashboard(
        dashboard_id="dashboard-card-001",
        asset_id="CARD-001",
        generated_at=REFERENCE,
        sections=(
            section(
                "collection-summary",
                "Collection Summary",
                {
                    "asset_id": "CARD-001",
                    "total_cards": 12,
                    "total_market_value": 5000,
                    "total_cost_basis": 3200,
                    "unrealized_gain_loss": 1800,
                    "valuation_coverage": 80,
                },
            ),
            section(
                "market-intelligence",
                "Market Intelligence",
                {
                    "market_intelligence": {
                        "confidence_score": 88,
                        "confidence_level": "HIGH",
                        "agreement_level": "GOOD",
                        "liquidity_level": "HIGH",
                    }
                },
            ),
            section(
                "market-quality",
                "Market Quality",
                {
                    "market_quality": "STRONG",
                    "source_quality": "STRONG",
                    "liquidity_quality": "NORMAL",
                },
            ),
            section(
                "timeline-summary",
                "Timeline Summary",
                {
                    "trend_direction": "IMPROVING",
                    "trend_strength": "MODERATE",
                    "trend_summary": list(trend_summary),
                },
            ),
            section(
                "radar-changes",
                "Radar Changes",
                {
                    "new_signals": [{"title": "Market Quality Improved"}],
                    "resolved_signals": [],
                    "changed_signals": [{"title": "Confidence Improved"}],
                    "escalated_signals": [],
                },
            ),
            section(
                "review-queue",
                "Review Queue",
                {
                    "review_status": review_status,
                },
            ),
            section(
                "warning-summary",
                "Warning Summary",
                {
                    "warnings": list(warnings),
                },
            ),
        ),
    )


def section(
    section_id: str,
    title: str,
    content: dict,
) -> CollectibleDashboardSection:
    return CollectibleDashboardSection(
        section_id=section_id,
        title=title,
        content=content,
        generated_at=REFERENCE,
    )
