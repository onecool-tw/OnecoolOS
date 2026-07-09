from copy import deepcopy
from datetime import datetime
from datetime import timezone
from decimal import Decimal

from onecool_os.dashboard import CollectibleDashboardBuilder
from onecool_os.dashboard import PerformanceDashboard
from onecool_os.dashboard import PerformanceDashboardBuilder
from onecool_os.performance import InvestmentPerformanceSnapshot
from onecool_os.performance import PerformanceStatus


REFERENCE = datetime(2026, 7, 9, tzinfo=timezone.utc)


def test_portfolio_summary() -> None:
    dashboard = PerformanceDashboardBuilder().build(
        performance_snapshots=[
            snapshot("card-1", cost="100", value="150", gain="50"),
            snapshot("card-2", cost="200", value="160", gain="-40"),
        ],
        collectible_assets=[asset("card-1"), asset("card-2")],
    )

    assert isinstance(dashboard, PerformanceDashboard)
    assert dashboard.portfolio_performance == {
        "total_cost_basis": "300.00",
        "total_market_value": "310.00",
        "total_unrealized_gain_loss": "10.00",
        "total_unrealized_percent": "0.03",
        "performing_asset_count": 2,
        "missing_valuation_count": 0,
        "missing_cost_basis_count": 0,
    }


def test_asset_table() -> None:
    dashboard = PerformanceDashboardBuilder().build(
        performance_snapshots=[snapshot("card-1", cost="100", value="150")],
        collectible_assets=[
            asset(
                "card-1",
                player="Shohei Ohtani",
                name="2018 Topps Update #US1",
                grade="PSA 10",
            )
        ],
    )

    row = dashboard.asset_performance_table[0]
    assert row["card_name"] == "2018 Topps Update #US1"
    assert row["player"] == "Shohei Ohtani"
    assert row["grade"] == "PSA 10"
    assert row["cost_basis"] == "100.00"
    assert row["market_value"] == "150.00"
    assert row["unrealized_gain_loss"] == "50.00"
    assert row["unrealized_percent"] == "0.50"
    assert row["holding_days"] == 30
    assert row["performance_status"] == "POSITIVE"


def test_warning_aggregation() -> None:
    dashboard = PerformanceDashboardBuilder().build(
        performance_snapshots=[
            snapshot(
                "card-1",
                cost=None,
                value="150",
                warnings=("Missing Cost Basis", "Insufficient Data"),
            ),
            snapshot(
                "card-2",
                cost="100",
                value=None,
                warnings=("Missing Market Value", "Insufficient Data"),
            ),
        ],
    )

    assert dashboard.warnings == (
        "Missing Cost Basis",
        "Insufficient Data",
        "Missing Market Value",
    )


def test_missing_values() -> None:
    dashboard = PerformanceDashboardBuilder().build(
        performance_snapshots=[
            snapshot("card-1", cost=None, value="150"),
            snapshot("card-2", cost="100", value=None),
        ],
    )

    assert dashboard.portfolio_performance["total_cost_basis"] == "100.00"
    assert dashboard.portfolio_performance["total_market_value"] == "150.00"
    assert dashboard.portfolio_performance["performing_asset_count"] == 0
    assert dashboard.portfolio_performance["missing_valuation_count"] == 1
    assert dashboard.portfolio_performance["missing_cost_basis_count"] == 1


def test_summary() -> None:
    dashboard = PerformanceDashboardBuilder().build(
        performance_snapshots=[
            snapshot("card-1", cost="100", value="175", gain="75", days=20),
            snapshot("card-2", cost="200", value="150", gain="-50", days=60),
            snapshot("card-3", cost="50", value="125", gain="75", days=5),
        ],
        collectible_assets=[
            asset("card-1", name="Card One"),
            asset("card-2", name="Card Two"),
            asset("card-3", name="Card Three"),
        ],
    )

    assert dashboard.summary["top_gainers"][0]["asset_id"] == "card-3"
    assert dashboard.summary["top_losers"][0]["asset_id"] == "card-2"
    assert dashboard.summary["largest_position"]["asset_id"] == "card-1"
    assert dashboard.summary["oldest_holding"]["asset_id"] == "card-2"
    assert dashboard.summary["newest_holding"]["asset_id"] == "card-3"


def test_collectible_dashboard_integration() -> None:
    dashboard = CollectibleDashboardBuilder().build(
        performance_snapshots=[snapshot("card-1", cost="100", value="150")],
        collectible_assets=[asset("card-1")],
    )

    section_ids = tuple(section.section_id for section in dashboard.sections)
    assert "portfolio-performance" in section_ids
    assert "asset-performance-table" in section_ids
    assert "performance-summary" in section_ids


def test_deterministic_replay() -> None:
    builder = PerformanceDashboardBuilder()
    snapshots = [snapshot("card-1", cost="100", value="150")]
    assets = [asset("card-1")]

    first = builder.build(
        performance_snapshots=snapshots,
        collectible_assets=assets,
    ).to_dict()
    second = builder.build(
        performance_snapshots=snapshots,
        collectible_assets=assets,
    ).to_dict()

    assert first == second


def test_no_mutation() -> None:
    snapshots = [snapshot("card-1", cost="100", value="150")]
    assets = [asset("card-1")]
    before_snapshots = deepcopy(snapshots)
    before_assets = deepcopy(assets)

    PerformanceDashboardBuilder().build(
        performance_snapshots=snapshots,
        collectible_assets=assets,
    )

    assert snapshots == before_snapshots
    assert assets == before_assets


def snapshot(
    asset_id: str,
    *,
    cost: str | None,
    value: str | None,
    gain: str | None = None,
    percent: str | None = None,
    days: int | None = 30,
    warnings: tuple[str, ...] = (),
) -> InvestmentPerformanceSnapshot:
    cost_decimal = Decimal(cost) if cost is not None else None
    value_decimal = Decimal(value) if value is not None else None
    if gain is None and cost_decimal is not None and value_decimal is not None:
        gain_decimal = value_decimal - cost_decimal
    else:
        gain_decimal = Decimal(gain) if gain is not None else None
    if percent is None and cost_decimal not in (None, Decimal("0")):
        percent_decimal = (
            gain_decimal / cost_decimal
            if gain_decimal is not None
            else None
        )
    else:
        percent_decimal = Decimal(percent) if percent is not None else None
    return InvestmentPerformanceSnapshot(
        asset_id=asset_id,
        cost_basis=cost_decimal,
        cost_currency="USD" if cost_decimal is not None else None,
        market_value=value_decimal,
        market_currency="USD" if value_decimal is not None else None,
        unrealized_gain=gain_decimal,
        unrealized_gain_percent=percent_decimal,
        holding_days=days,
        performance_status=_status(gain_decimal),
        warnings=warnings,
        generated_at=REFERENCE,
    )


def asset(
    asset_id: str,
    *,
    player: str = "Shohei Ohtani",
    name: str = "2018 Topps Update #US1",
    grade: str = "PSA 10",
) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "player": player,
        "name": name,
        "grade": grade,
    }


def _status(gain: Decimal | None) -> PerformanceStatus:
    if gain is None:
        return PerformanceStatus.INSUFFICIENT_DATA
    if gain > Decimal("0"):
        return PerformanceStatus.POSITIVE
    if gain < Decimal("0"):
        return PerformanceStatus.NEGATIVE
    return PerformanceStatus.BREAKEVEN
