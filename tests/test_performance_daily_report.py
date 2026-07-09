from copy import deepcopy
from datetime import datetime
from datetime import timezone

from onecool_os.dashboard import CollectibleDashboard
from onecool_os.dashboard import CollectibleDashboardSection
from onecool_os.report import CollectibleDailyRadarReportBuilder


REFERENCE = datetime(2026, 7, 9, tzinfo=timezone.utc)


def test_performance_summary_included() -> None:
    report = CollectibleDailyRadarReportBuilder().build(
        dashboard(),
        reference_datetime=REFERENCE,
    )

    assert report.performance_summary == {
        "total_cost_basis": "300.00",
        "total_market_value": "390.00",
        "total_unrealized_gain_loss": "90.00",
        "total_unrealized_percent": "0.30",
        "performing_assets": 2,
        "missing_valuations": 1,
        "missing_cost_basis": 0,
    }
    assert report.to_dict()["sections"]["performance_summary"] == (
        report.performance_summary
    )


def test_top_gainers_included() -> None:
    report = CollectibleDailyRadarReportBuilder().build(
        dashboard(),
        reference_datetime=REFERENCE,
    )

    assert report.top_movers["top_gainers"][0]["asset_id"] == "card-1"
    assert report.to_dict()["sections"]["top_movers"]["top_gainers"][0][
        "card_name"
    ] == "Shohei Ohtani US1"


def test_top_losers_included() -> None:
    report = CollectibleDailyRadarReportBuilder().build(
        dashboard(),
        reference_datetime=REFERENCE,
    )

    assert report.top_movers["top_losers"][0]["asset_id"] == "card-2"
    assert report.to_dict()["sections"]["top_movers"]["top_losers"][0][
        "card_name"
    ] == "Shohei Ohtani US285"


def test_performance_warnings_included() -> None:
    report = CollectibleDailyRadarReportBuilder().build(
        dashboard(report_warnings=("Source Conflict",)),
        reference_datetime=REFERENCE,
    )

    assert report.warnings == (
        "Source Conflict",
        "Missing Cost Basis",
        "Missing Market Value",
        "Insufficient Data",
    )


def test_empty_performance_output() -> None:
    report = CollectibleDailyRadarReportBuilder().build(
        dashboard(with_performance=False),
        reference_datetime=REFERENCE,
    )

    assert report.performance_summary == {
        "total_cost_basis": None,
        "total_market_value": None,
        "total_unrealized_gain_loss": None,
        "total_unrealized_percent": None,
        "performing_assets": 0,
        "missing_valuations": 0,
        "missing_cost_basis": 0,
    }
    assert report.top_movers == {"top_gainers": [], "top_losers": []}


def test_deterministic_output() -> None:
    source = dashboard()
    builder = CollectibleDailyRadarReportBuilder()

    first = builder.build(source, reference_datetime=REFERENCE).to_dict()
    second = builder.build(source, reference_datetime=REFERENCE).to_dict()

    assert first == second


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
    with_performance: bool = True,
    report_warnings: tuple[str, ...] = (),
) -> CollectibleDashboard:
    sections = [
        section(
            "collection-summary",
            "Collection Summary",
            {"asset_id": "CARD-001"},
        ),
        section(
            "warning-summary",
            "Warning Summary",
            {"warnings": list(report_warnings)},
        ),
    ]
    if with_performance:
        sections.extend(
            [
                section(
                    "portfolio-performance",
                    "Portfolio Performance",
                    {
                        "total_cost_basis": "300.00",
                        "total_market_value": "390.00",
                        "total_unrealized_gain_loss": "90.00",
                        "total_unrealized_percent": "0.30",
                        "performing_asset_count": 2,
                        "missing_valuation_count": 1,
                        "missing_cost_basis_count": 0,
                    },
                ),
                section(
                    "performance-summary",
                    "Performance Summary",
                    {
                        "summary": {
                            "top_gainers": [
                                {
                                    "asset_id": "card-1",
                                    "card_name": "Shohei Ohtani US1",
                                    "unrealized_gain_loss": "100.00",
                                }
                            ],
                            "top_losers": [
                                {
                                    "asset_id": "card-2",
                                    "card_name": "Shohei Ohtani US285",
                                    "unrealized_gain_loss": "-10.00",
                                }
                            ],
                        },
                        "warnings": [
                            "Missing Cost Basis",
                            "Missing Market Value",
                            "Insufficient Data",
                        ],
                    },
                ),
            ]
        )
    return CollectibleDashboard(
        dashboard_id="dashboard-card-001",
        asset_id="CARD-001",
        generated_at=REFERENCE,
        sections=tuple(sections),
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
