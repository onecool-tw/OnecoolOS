from copy import deepcopy
from datetime import datetime
from datetime import timezone
from decimal import Decimal

from onecool_os.performance import CollectiblePerformanceBuilder
from onecool_os.performance import InvestmentPerformanceSnapshot
from onecool_os.performance import PerformanceStatus


REFERENCE = datetime(2026, 7, 9, tzinfo=timezone.utc)


def test_collectible_performance_positive_gain() -> None:
    snapshot = build_one(cost="100", value="150")

    assert isinstance(snapshot, InvestmentPerformanceSnapshot)
    assert snapshot.performance_status == PerformanceStatus.POSITIVE
    assert snapshot.unrealized_gain == Decimal("50")
    assert snapshot.unrealized_gain_percent == Decimal("0.5")


def test_collectible_performance_negative_gain() -> None:
    snapshot = build_one(cost="100", value="75")

    assert snapshot.performance_status == PerformanceStatus.NEGATIVE
    assert snapshot.unrealized_gain == Decimal("-25")
    assert snapshot.unrealized_gain_percent == Decimal("-0.25")


def test_collectible_performance_breakeven() -> None:
    snapshot = build_one(cost="100", value="100")

    assert snapshot.performance_status == PerformanceStatus.BREAKEVEN
    assert snapshot.unrealized_gain == Decimal("0")
    assert snapshot.unrealized_gain_percent == Decimal("0")


def test_collectible_performance_missing_cost_basis() -> None:
    snapshot = build_one(cost="", value="100")

    assert snapshot.performance_status == PerformanceStatus.INSUFFICIENT_DATA
    assert snapshot.cost_basis is None
    assert "Missing Cost Basis" in snapshot.warnings
    assert "Insufficient Data" in snapshot.warnings


def test_collectible_performance_missing_valuation() -> None:
    snapshots = CollectiblePerformanceBuilder().build(
        collectible_assets=[card(cost="100")],
        valuation_records=[],
        reference_datetime=REFERENCE,
    )

    assert snapshots[0].performance_status == PerformanceStatus.INSUFFICIENT_DATA
    assert snapshots[0].market_value is None
    assert "Missing Market Value" in snapshots[0].warnings
    assert "Insufficient Data" in snapshots[0].warnings


def test_collectible_performance_holding_days() -> None:
    snapshot = build_one(
        cost="100",
        value="150",
        purchase_date="2026-07-01",
    )

    assert snapshot.holding_days == 8


def test_collectible_performance_preserves_cost_currency() -> None:
    snapshot = build_one(cost="100", value="150", currency="USD")

    assert snapshot.cost_currency == "USD"
    assert snapshot.market_currency == "USD"


def test_collectible_performance_does_not_parse_twd_notes_cost() -> None:
    source = card(
        cost="100",
        notes="台幣成本 3200; this must stay informational only",
    )

    snapshot = CollectiblePerformanceBuilder().build(
        collectible_assets=[source],
        valuation_records=[valuation("card-1", "150", currency="USD")],
        reference_datetime=REFERENCE,
    )[0]

    assert snapshot.cost_basis == Decimal("100")
    assert snapshot.cost_currency == "USD"
    assert snapshot.unrealized_gain == Decimal("50")


def test_collectible_performance_no_mutation() -> None:
    source_assets = [card(cost="100")]
    source_valuations = [valuation("card-1", "150")]
    before_assets = deepcopy(source_assets)
    before_valuations = deepcopy(source_valuations)

    CollectiblePerformanceBuilder().build(
        collectible_assets=source_assets,
        valuation_records=source_valuations,
        reference_datetime=REFERENCE,
    )

    assert source_assets == before_assets
    assert source_valuations == before_valuations


def test_collectible_performance_deterministic_replay() -> None:
    builder = CollectiblePerformanceBuilder()
    source_assets = [card(cost="100")]
    source_valuations = [valuation("card-1", "150")]

    first = builder.build(
        collectible_assets=source_assets,
        valuation_records=source_valuations,
        reference_datetime=REFERENCE,
    )[0].to_dict()
    second = builder.build(
        collectible_assets=source_assets,
        valuation_records=source_valuations,
        reference_datetime=REFERENCE,
    )[0].to_dict()

    assert first == second


def test_collectible_performance_multiple_assets() -> None:
    snapshots = CollectiblePerformanceBuilder().build(
        collectible_assets=[
            card(asset_id="card-1", cost="100"),
            card(asset_id="card-2", cost="200"),
        ],
        valuation_records={
            "card-1": valuation("card-1", "150"),
            "card-2": valuation("card-2", "175"),
        },
        reference_datetime=REFERENCE,
    )

    assert tuple(snapshot.asset_id for snapshot in snapshots) == (
        "card-1",
        "card-2",
    )
    assert snapshots[0].performance_status == PerformanceStatus.POSITIVE
    assert snapshots[1].performance_status == PerformanceStatus.NEGATIVE


def build_one(
    *,
    cost: str,
    value: str,
    currency: str = "USD",
    purchase_date: str = "2026-07-01",
) -> InvestmentPerformanceSnapshot:
    return CollectiblePerformanceBuilder().build(
        collectible_assets=[
            card(
                cost=cost,
                currency=currency,
                purchase_date=purchase_date,
            )
        ],
        valuation_records=[valuation("card-1", value, currency=currency)],
        reference_datetime=REFERENCE,
    )[0]


def card(
    *,
    asset_id: str = "card-1",
    cost: str,
    currency: str = "USD",
    purchase_date: str = "2026-07-01",
    notes: str = "",
) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "cert_number": "12345678",
        "cost": cost,
        "currency": currency,
        "purchase_date": purchase_date,
        "notes": notes,
    }


def valuation(
    asset_id: str,
    value: str,
    *,
    currency: str = "USD",
) -> dict[str, str]:
    return {
        "valuation_id": f"valuation-{asset_id}",
        "asset_id": asset_id,
        "market_value": value,
        "currency": currency,
        "valuation_date": "2026-07-09",
    }
