from __future__ import annotations

from copy import deepcopy
from datetime import date
from datetime import datetime
from datetime import timezone
from pathlib import Path

from onecool_os.cli.launcher import DEFAULT_PSA_COLLECTION_PATH
from onecool_os.cli.launcher import OnecoolLauncher
from onecool_os.dashboard import CollectibleDashboardBuilder
from onecool_os.dashboard import portfolio_nav_lines
from onecool_os.dashboard import portfolio_nav_sections
from onecool_os.portfolio import AssetNavLine
from onecool_os.portfolio import PortfolioNavSnapshot
from onecool_os.portfolio import PortfolioNavStatus
from onecool_os.valuation.models import ValuationRecord

REFERENCE = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)


def test_dashboard_consumes_portfolio_nav_snapshot() -> None:
    snapshot = _snapshot(
        status="COMPLETE",
        assets_with_market_value=1,
        verified_assets=1,
        total_market_value="250",
        unrealized_gain_loss="130",
        roi_percent="108.3333",
        lines=[_line(coverage_status="VERIFIED", market_value="250")],
    )

    section = portfolio_nav_sections((snapshot,))[0]

    assert section.title == "Portfolio NAV - USD"
    assert section.content["nav_status"] == "COMPLETE"
    assert section.content["total_market_value"] == "250.00"
    assert section.content["roi_percent"] == "108.33%"


def test_dashboard_does_not_recalculate_nav() -> None:
    snapshot = _snapshot(
        status="COMPLETE",
        assets_with_market_value=1,
        total_cost_basis="999",
        total_market_value="1",
        unrealized_gain_loss="123",
        roi_percent="456.7890",
        lines=[_line(coverage_status="VERIFIED", market_value="250")],
    )

    content = portfolio_nav_sections((snapshot,))[0].content

    assert content["total_market_value"] == "1.00"
    assert content["unrealized_gain_loss"] == "123.00"
    assert content["roi_percent"] == "456.79%"


def test_no_valuation_records_display_na() -> None:
    snapshot = _snapshot(
        status="INSUFFICIENT_DATA",
        total_assets=50,
        assets_with_cost=50,
        assets_with_market_value=0,
        missing_value_assets=50,
        total_cost_basis="3646.75",
        total_market_value="0",
        unrealized_gain_loss=None,
        roi_percent=None,
        lines=[_line(market_value=None, warnings=("Missing Market Value",))],
    )

    lines = portfolio_nav_lines((snapshot,))

    assert "Status: INSUFFICIENT_DATA" in lines
    assert "Total Assets: 50" in lines
    assert "Assets With Cost Basis: 50" in lines
    assert "Assets With Market Value: 0" in lines
    assert "Total Cost Basis: USD 3,646.75" in lines
    assert "Total Market Value: N/A" in lines
    assert "Unrealized Gain / Loss: N/A" in lines
    assert "ROI: N/A" in lines
    assert "Valuation Coverage: 0.00%" in lines
    assert "Verified Coverage: 0.00%" in lines
    assert "Missing Value Assets: 50" in lines


def test_one_verified_asset_output() -> None:
    snapshot = _snapshot(
        status="COMPLETE",
        assets_with_market_value=1,
        verified_assets=1,
        total_market_value="250",
        unrealized_gain_loss="130",
        roi_percent="108.3333",
        lines=[_line(coverage_status="VERIFIED", market_value="250")],
    )

    lines = portfolio_nav_lines((snapshot,))

    assert "Verified Assets: 1" in lines
    assert "Total Market Value: USD 250.00" in lines
    assert "ROI: 108.33%" in lines


def test_partial_coverage() -> None:
    snapshot = _snapshot(
        status="PARTIAL",
        total_assets=2,
        assets_with_market_value=1,
        verified_assets=1,
        missing_value_assets=1,
        valuation_coverage_percent="50",
        verified_coverage_percent="50",
        lines=[
            _line(asset_id="PSA-1", coverage_status="VERIFIED", market_value="250"),
            _line(asset_id="PSA-2", coverage_status="MISSING", market_value=None, warnings=("Missing Market Value",)),
        ],
    )

    lines = portfolio_nav_lines((snapshot,))

    assert "Status: PARTIAL" in lines
    assert "Valuation Coverage: 50.00%" in lines
    assert "Verified Coverage: 50.00%" in lines
    assert "  Missing: 1 / 2" in lines


def test_estimated_asset() -> None:
    snapshot = _snapshot(
        status="PARTIAL",
        estimated_assets=1,
        lines=[_line(coverage_status="ESTIMATED", valuation_source="MANUAL", warnings=("Supporting Estimate Only",))],
    )

    rows = portfolio_nav_sections((snapshot,))[-1].content["rows"]

    assert rows[0]["coverage_status"] == "ESTIMATED"
    assert rows[0]["valuation_source"] == "MANUAL"


def test_review_required_asset() -> None:
    snapshot = _snapshot(
        status="INSUFFICIENT_DATA",
        review_required_assets=1,
        lines=[_line(coverage_status="REVIEW_REQUIRED", market_value=None, warnings=("Evidence Needs Review",))],
    )

    rows = portfolio_nav_sections((snapshot,))[-1].content["rows"]

    assert rows[0]["coverage_status"] == "REVIEW_REQUIRED"
    assert "Evidence Needs Review" in rows[0]["warning_summary"]


def test_missing_market_value_review_row() -> None:
    snapshot = _snapshot(lines=[_line(market_value=None, warnings=("Missing Market Value",))])

    lines = portfolio_nav_lines((snapshot,))

    assert any("Coverage: MISSING" in line for line in lines)
    assert any("Warnings: Missing Market Value" in line for line in lines)


def test_missing_cost_basis_displayed() -> None:
    snapshot = _snapshot(lines=[_line(cost_basis=None, warnings=("Missing Cost Basis",))])

    lines = portfolio_nav_lines((snapshot,))

    assert any("Cost: N/A" in line for line in lines)
    assert any("Missing Cost Basis" in line for line in lines)


def test_status_presentations() -> None:
    for status in (
        "COMPLETE",
        "PARTIAL",
        "INSUFFICIENT_DATA",
        "CURRENCY_MISMATCH",
    ):
        lines = portfolio_nav_lines((_snapshot(status=status),))
        assert f"Status: {status}" in lines
        assert any(line.startswith("Status Meaning:") for line in lines)


def test_separate_multi_currency_sections() -> None:
    lines = portfolio_nav_lines((_snapshot(currency="USD"), _snapshot(currency="TWD")))

    assert "Portfolio NAV - TWD" in lines
    assert "Portfolio NAV - USD" in lines
    assert "Mixed-Currency Grand Total" not in "\n".join(lines)


def test_na_instead_of_zero_for_missing_values() -> None:
    snapshot = _snapshot(assets_with_market_value=0, total_market_value="0", unrealized_gain_loss=None)

    lines = portfolio_nav_lines((snapshot,))

    assert "Total Market Value: N/A" in lines
    assert "Unrealized Gain / Loss: N/A" in lines


def test_valuation_coverage_counts() -> None:
    snapshot = _snapshot(total_assets=3, verified_assets=1, review_required_assets=1, estimated_assets=1)

    lines = portfolio_nav_lines((snapshot,))

    assert any(line.startswith("  Verified: 1 / 3") for line in lines)
    assert "  Review Required: 1 / 3" in lines
    assert "  Estimated: 1 / 3" in lines


def test_verified_coverage_counts() -> None:
    snapshot = _snapshot(total_assets=2, verified_assets=1, verified_coverage_percent="50")

    section = next(section for section in portfolio_nav_sections((snapshot,)) if section.section_id == "valuation-coverage")

    assert section.content["snapshots"][0]["verified"]["count"] == 1
    assert section.content["snapshots"][0]["verified"]["percent"] == "50.00%"


def test_asset_review_list_is_concise() -> None:
    snapshot = _snapshot(
        total_assets=12,
        lines=[
            _line(asset_id=f"PSA-{index}", warnings=("Missing Market Value",))
            for index in range(12)
        ],
    )

    lines = portfolio_nav_lines((snapshot,))

    assert "  Omitted Review Rows: 2" in lines


def test_private_notes_not_displayed() -> None:
    snapshot = _snapshot(
        lines=[
            _line(
                asset_name="Demo Card",
                warnings=("Missing Market Value",),
            )
        ]
    )

    rendered = "\n".join(portfolio_nav_lines((snapshot,)))

    assert "PRIVATE NOTE" not in rendered


def test_deterministic_output() -> None:
    snapshot = _snapshot()

    assert portfolio_nav_lines((snapshot,)) == portfolio_nav_lines((snapshot,))
    assert [section.to_dict() for section in portfolio_nav_sections((snapshot,))] == [
        section.to_dict() for section in portfolio_nav_sections((snapshot,))
    ]


def test_no_mutation() -> None:
    snapshot = _snapshot()
    before = deepcopy(snapshot.to_dict())

    portfolio_nav_lines((snapshot,))
    portfolio_nav_sections((snapshot,))

    assert snapshot.to_dict() == before


def test_collectible_dashboard_builder_integration() -> None:
    dashboard = CollectibleDashboardBuilder().build(
        portfolio_nav_snapshots=(_snapshot(),),
    )

    assert any(section.section_id == "portfolio-nav-usd" for section in dashboard.sections)
    assert any(section.section_id == "valuation-coverage" for section in dashboard.sections)


def test_cli_reuses_current_runtime_session(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_row(cert_number="PSA0001")])
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "2", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        runtime_valuation_records=[_valuation("PSA-PSA0001", "250")],
        cwd=tmp_path,
    ).run()

    assert "Portfolio NAV" in output
    assert "Total Market Value: N/A" in output
    assert "Status: INSUFFICIENT_DATA" in output
    assert "NAV Status" not in output  # Status is displayed directly from snapshot.


def test_cli_no_valuation_records(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_row(cert_number="PSA0001")])
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "2", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()

    assert "Status: INSUFFICIENT_DATA" in output
    assert "Total Market Value: N/A" in output
    assert "Verified Coverage: 0.00%" in output


def _snapshot(
    *,
    currency: str = "USD",
    status: str = "INSUFFICIENT_DATA",
    total_assets: int = 1,
    assets_with_cost: int = 1,
    assets_with_market_value: int = 0,
    verified_assets: int = 0,
    review_required_assets: int = 0,
    estimated_assets: int = 0,
    missing_value_assets: int = 1,
    total_cost_basis: str = "120",
    total_market_value: str = "0",
    unrealized_gain_loss: str | None = None,
    roi_percent: str | None = None,
    valuation_coverage_percent: str = "0",
    verified_coverage_percent: str = "0",
    lines: list[AssetNavLine] | None = None,
) -> PortfolioNavSnapshot:
    return PortfolioNavSnapshot(
        snapshot_id=f"nav-{currency}",
        reference_datetime=REFERENCE,
        currency=currency,
        total_assets=total_assets,
        assets_with_cost=assets_with_cost,
        assets_with_market_value=assets_with_market_value,
        verified_assets=verified_assets,
        review_required_assets=review_required_assets,
        estimated_assets=estimated_assets,
        missing_value_assets=missing_value_assets,
        total_cost_basis=total_cost_basis,
        total_market_value=total_market_value,
        unrealized_gain_loss=unrealized_gain_loss,
        roi_percent=roi_percent,
        valuation_coverage_percent=valuation_coverage_percent,
        verified_coverage_percent=verified_coverage_percent,
        status=status,
        asset_lines=tuple(lines or [_line()]),
        generated_at=REFERENCE,
    )


def _line(
    *,
    asset_id: str = "PSA-1",
    asset_name: str = "2018 Topps Update Shohei Ohtani US1 PSA 10",
    cert_number: str | None = "1",
    cost_basis: str | None = "120",
    cost_currency: str = "USD",
    market_value: str | None = None,
    market_currency: str | None = "USD",
    unrealized_gain_loss: str | None = None,
    roi_percent: str | None = None,
    valuation_source: str | None = None,
    coverage_status: str = "MISSING",
    warnings: tuple[str, ...] = ("Missing Market Value",),
) -> AssetNavLine:
    return AssetNavLine(
        asset_id=asset_id,
        cert_number=cert_number,
        asset_name=asset_name,
        cost_basis=cost_basis,
        cost_currency=cost_currency,
        market_value=market_value,
        market_currency=market_currency if market_value is not None else None,
        unrealized_gain_loss=unrealized_gain_loss,
        roi_percent=roi_percent,
        valuation_source=valuation_source,
        valuation_record_id="v1" if valuation_source else None,
        evidence_status=coverage_status,
        coverage_status=coverage_status,
        valuation_date=date(2026, 7, 10) if market_value is not None else None,
        warnings=warnings,
    )


def _valuation(asset_id: str, value: str) -> ValuationRecord:
    return ValuationRecord(
        valuation_id=f"runtime-{asset_id}",
        asset_id=asset_id,
        asset_type="SPORTS_CARD",
        source="EBAY_SOLD",
        currency="USD",
        valuation_date=date(2026, 7, 10),
        confidence="HIGH",
        market_value=value,
    )


def _inputs(*values: str):
    iterator = iter(values)

    def _input(_: str) -> str:
        return next(iterator)

    return _input


def _write_psa_collection(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    csv_path = tmp_path / DEFAULT_PSA_COLLECTION_PATH
    csv_path.parent.mkdir(parents=True)
    columns = (
        "Item",
        "Subject",
        "Year",
        "Set",
        "Card Number",
        "Grade Issuer",
        "Grade",
        "Cert Number",
        "My Cost",
        "Date Acquired",
        "Source",
        "My Notes",
    )
    lines = [",".join(columns)]
    for row in rows:
        lines.append(",".join(row[column] for column in columns))
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path


def _row(*, cert_number: str) -> dict[str, str]:
    return {
        "Item": "Demo Card Shohei Ohtani",
        "Subject": "Shohei Ohtani",
        "Year": "2018",
        "Set": "Demo Set",
        "Card Number": "1",
        "Grade Issuer": "PSA",
        "Grade": "10",
        "Cert Number": cert_number,
        "My Cost": "120.00",
        "Date Acquired": "2026-06-01",
        "Source": "PSA Collection",
        "My Notes": "PRIVATE NOTE",
    }
