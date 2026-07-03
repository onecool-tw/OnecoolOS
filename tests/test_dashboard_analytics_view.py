from copy import deepcopy
from decimal import Decimal

from onecool_os.analytics.models import AnalyticsSnapshot
from onecool_os.dashboard import DashboardAnalyticsView
from onecool_os.dashboard import DashboardBuilder
from onecool_os.services import AnalyticsService


def test_dashboard_analytics_view_empty_analytics() -> None:
    view = DashboardAnalyticsView.from_snapshot(None)
    sections = section_map(view)

    assert sections["Cash Flow Summary"]["status"] == "empty"
    assert sections["Allocation Summary"]["status"] == "empty"
    assert sections["Performance Summary"]["status"] == "empty"
    assert sections["Risk Summary"]["status"] == "empty"
    assert sections["Pipeline Summary"]["status"] == "empty"


def test_dashboard_analytics_view_cash_flow_summary() -> None:
    view = DashboardAnalyticsView.from_snapshot({
        "cash_inflow": Decimal("100"),
        "cash_outflow": Decimal("40"),
        "net_cash_flow": Decimal("60"),
    })

    section = section_map(view)["Cash Flow Summary"]

    assert section["status"] == "ready"
    assert section["summary"] == "Net cash flow: 60"
    assert section["details"]["cash_inflow"] == Decimal("100")
    assert section["details"]["cash_outflow"] == Decimal("40")


def test_dashboard_analytics_view_allocation_summary() -> None:
    view = DashboardAnalyticsView.from_snapshot({
        "asset_class_weights": {
            "Cash": Decimal("0.25"),
            "ETF": Decimal("0.75"),
        }
    })

    section = section_map(view)["Allocation Summary"]

    assert section["status"] == "ready"
    assert section["summary"] == "2 asset classes available."
    assert section["details"]["asset_class_weights"]["ETF"] == Decimal("0.75")


def test_dashboard_analytics_view_performance_summary() -> None:
    view = DashboardAnalyticsView.from_snapshot({
        "total_cost": Decimal("100"),
        "total_market_value": Decimal("120"),
        "unrealized_gain": Decimal("20"),
        "unrealized_return": Decimal("0.2"),
    })

    section = section_map(view)["Performance Summary"]

    assert section["status"] == "ready"
    assert section["summary"] == "Unrealized return: 0.2"
    assert section["details"]["unrealized_gain"] == Decimal("20")


def test_dashboard_analytics_view_risk_summary() -> None:
    view = DashboardAnalyticsView.from_snapshot({
        "risk_score": Decimal("42"),
        "risk_level": "MEDIUM",
    })

    section = section_map(view)["Risk Summary"]

    assert section["status"] == "ready"
    assert section["summary"] == "Risk level: MEDIUM"
    assert section["details"]["risk_score"] == Decimal("42")


def test_dashboard_analytics_view_pipeline_metadata() -> None:
    view = DashboardAnalyticsView.from_snapshot({
        "metadata": {
            "source_pipeline_id": "pipeline-1",
            "executed_engines": ["cash_flow:calculator"],
            "skipped_engines": [],
            "errors": [],
        }
    })

    section = section_map(view)["Pipeline Summary"]

    assert section["status"] == "ready"
    assert section["summary"] == "Source pipeline: pipeline-1"
    assert section["details"]["executed_engines"] == [
        "cash_flow:calculator"
    ]


def test_dashboard_builder_analytics_view_integration() -> None:
    view = DashboardBuilder(
        analytics_service=AnalyticsService().load(
            "data/analytics/analytics.example.json"
        ),
    ).build()
    sections = {
        section.section_id: section
        for section in view.sections()
    }

    analytics_view = sections["analytics-summary"].content["analytics_view"]
    analytics_sections = {
        section["title"]: section
        for section in analytics_view["sections"]
    }

    assert analytics_sections["Cash Flow Summary"]["status"] == "ready"
    assert analytics_sections["Allocation Summary"]["status"] == "ready"
    assert analytics_sections["Performance Summary"]["status"] == "ready"
    assert analytics_sections["Risk Summary"]["status"] == "ready"
    assert analytics_sections["Pipeline Summary"]["status"] == "empty"


def test_dashboard_analytics_view_read_only_behavior() -> None:
    snapshot = {
        "cash_inflow": Decimal("100"),
        "metadata": {
            "source_pipeline_id": "pipeline-1",
            "executed_engines": ["cash_flow:calculator"],
        },
    }
    before = deepcopy(snapshot)

    DashboardAnalyticsView.from_snapshot(snapshot)

    assert snapshot == before


def test_dashboard_analytics_view_accepts_snapshot_model() -> None:
    snapshot = AnalyticsSnapshot(
        snapshot_id="snapshot-1",
        portfolio_id="portfolio-1",
        base_currency="TWD",
        snapshot_date="2026-01-01",
        cash_inflow="100",
        cash_outflow="40",
        net_cash_flow="60",
    )

    view = DashboardAnalyticsView.from_snapshot(snapshot)

    assert section_map(view)["Cash Flow Summary"]["status"] == "ready"


def section_map(view: DashboardAnalyticsView) -> dict:
    return {
        section["title"]: section
        for section in view.to_dict()["sections"]
    }
