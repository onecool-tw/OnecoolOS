import json
from pathlib import Path

from onecool_os.__main__ import main
from onecool_os.dashboard import DashboardBuilder
from onecool_os.dashboard import DashboardError
from onecool_os.dashboard import DashboardSection
from onecool_os.dashboard import DashboardView
from onecool_os.services import AnalyticsService
from onecool_os.services import LedgerService
from onecool_os.services import PortfolioService
from onecool_os.services import ValuationService


def test_dashboard_section_model() -> None:
    section = DashboardSection(
        section_id="portfolio",
        title="Portfolio",
        content={"status": "ready"},
        source_service="portfolio",
        generated_at="2026-04-01T08:00:00+08:00",
    )

    assert section.section_id == "portfolio"
    assert section.title == "Portfolio"
    assert section.content == {"status": "ready"}
    assert section.source_service == "portfolio"
    assert section.to_dict()["generated_at"] == "2026-04-01T08:00:00+08:00"


def test_dashboard_view_model() -> None:
    view = DashboardView(
        dashboard_id="dashboard-1",
        dashboard_name="Main Dashboard",
        base_currency="twd",
        portfolio_summary=DashboardSection(
            section_id="portfolio",
            title="Portfolio",
        ),
        tags=["demo"],
    )

    assert view.dashboard_id == "dashboard-1"
    assert view.base_currency == "TWD"
    assert len(view.sections()) == 1
    assert view.tags == ("demo",)
    assert view.to_dict()["sections"][0]["section_id"] == "portfolio"


def test_dashboard_view_rejects_missing_required_fields() -> None:
    try:
        DashboardView(
            dashboard_id="",
            dashboard_name="Main Dashboard",
            base_currency="TWD",
        )
    except DashboardError as exc:
        assert "dashboard_id must be a non-empty string" in str(exc)
    else:
        raise AssertionError("Missing dashboard_id should be rejected.")


def test_dashboard_section_requires_title() -> None:
    try:
        DashboardSection(section_id="summary", title="")
    except DashboardError as exc:
        assert "title must be a non-empty string" in str(exc)
    else:
        raise AssertionError("Missing section title should be rejected.")


def test_dashboard_view_rejects_duplicate_section_ids() -> None:
    section_a = DashboardSection(section_id="duplicate", title="A")
    section_b = DashboardSection(section_id="duplicate", title="B")

    try:
        DashboardView(
            dashboard_id="dashboard-1",
            dashboard_name="Main Dashboard",
            base_currency="TWD",
            portfolio_summary=section_a,
            analytics_summary=section_b,
        )
    except DashboardError as exc:
        assert "Duplicate section_id" in str(exc)
    else:
        raise AssertionError("Duplicate section_id should be rejected.")


def test_dashboard_builder_from_services() -> None:
    view = DashboardBuilder.demo()
    payload = view.to_dict()
    sections = {
        section["section_id"]: section for section in payload["sections"]
    }

    assert payload["dashboard_name"] == "Onecool Dashboard"
    assert sections["portfolio-summary"]["content"]["status"] == "ready"
    assert sections["analytics-summary"]["content"]["snapshot_count"] == 1
    assert sections["valuation-summary"]["content"]["valuation_count"] == 3
    assert sections["ledger-summary"]["content"]["transaction_count"] == 2


def test_dashboard_builder_empty_service_behavior() -> None:
    view = DashboardBuilder().build()
    sections = {
        section.section_id: section for section in view.sections()
    }

    assert sections["portfolio-summary"].content["status"] == "unavailable"
    assert sections["analytics-summary"].content["status"] == "unavailable"
    assert sections["valuation-summary"].content["status"] == "unavailable"
    assert sections["ledger-summary"].content["status"] == "unavailable"


def test_dashboard_cli_demo(capsys) -> None:
    assert main(["dashboard", "demo"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["dashboard_id"] == "dashboard-demo"
    assert payload["dashboard_name"] == "Onecool Dashboard"
    assert len(payload["sections"]) == 4


def test_dashboard_builder_does_not_modify_files(tmp_path: Path) -> None:
    portfolio_path = copy_example(
        "data/portfolio/portfolio.example.json",
        tmp_path / "portfolio.json",
    )
    analytics_path = copy_example(
        "data/analytics/analytics.example.json",
        tmp_path / "analytics.json",
    )
    valuation_path = copy_example(
        "data/valuation/valuation.example.json",
        tmp_path / "valuation.json",
    )
    ledger_path = copy_example(
        "data/transactions/ledger.example.json",
        tmp_path / "ledger.json",
    )
    before = {
        path: path.read_text(encoding="utf-8")
        for path in (
            portfolio_path,
            analytics_path,
            valuation_path,
            ledger_path,
        )
    }

    builder = DashboardBuilder(
        portfolio_service=PortfolioService().load(portfolio_path),
        analytics_service=AnalyticsService().load(analytics_path),
        valuation_service=ValuationService().load(valuation_path),
        ledger_service=LedgerService().load(ledger_path),
    )
    builder.build()

    after = {
        path: path.read_text(encoding="utf-8")
        for path in before
    }
    assert after == before


def copy_example(source: str, destination: Path) -> Path:
    destination.write_text(
        Path(source).read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return destination
