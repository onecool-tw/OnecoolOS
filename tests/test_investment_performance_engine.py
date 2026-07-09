from copy import deepcopy
from datetime import datetime
from datetime import timezone
from decimal import Decimal

from onecool_os.performance import InvestmentPerformanceEngine
from onecool_os.performance import InvestmentPerformanceSnapshot
from onecool_os.performance import PerformanceStatus


REFERENCE = datetime(2026, 7, 9, tzinfo=timezone.utc)


def test_investment_performance_positive_gain() -> None:
    snapshot = calculate(cost="100", market_value="150")

    assert isinstance(snapshot, InvestmentPerformanceSnapshot)
    assert snapshot.performance_status == PerformanceStatus.POSITIVE
    assert snapshot.unrealized_gain == Decimal("50")
    assert snapshot.unrealized_gain_percent == Decimal("0.5")


def test_investment_performance_negative_gain() -> None:
    snapshot = calculate(cost="100", market_value="80")

    assert snapshot.performance_status == PerformanceStatus.NEGATIVE
    assert snapshot.unrealized_gain == Decimal("-20")
    assert snapshot.unrealized_gain_percent == Decimal("-0.2")


def test_investment_performance_breakeven() -> None:
    snapshot = calculate(cost="100", market_value="100")

    assert snapshot.performance_status == PerformanceStatus.BREAKEVEN
    assert snapshot.unrealized_gain == Decimal("0")
    assert snapshot.unrealized_gain_percent == Decimal("0")


def test_investment_performance_missing_cost() -> None:
    snapshot = InvestmentPerformanceEngine().calculate(
        asset=asset(cost=""),
        valuation=valuation("120"),
        reference_datetime=REFERENCE,
    )

    assert snapshot.performance_status == PerformanceStatus.INSUFFICIENT_DATA
    assert snapshot.cost_basis is None
    assert snapshot.unrealized_gain is None
    assert "Missing Cost Basis" in snapshot.warnings


def test_investment_performance_missing_valuation() -> None:
    snapshot = InvestmentPerformanceEngine().calculate(
        asset=asset(cost="100"),
        valuation=None,
        reference_datetime=REFERENCE,
    )

    assert snapshot.performance_status == PerformanceStatus.INSUFFICIENT_DATA
    assert snapshot.market_value is None
    assert "Missing Valuation" in snapshot.warnings


def test_investment_performance_holding_days() -> None:
    snapshot = calculate(
        cost="100",
        market_value="150",
        purchase_date="2026-07-01",
    )

    assert snapshot.holding_days == 8


def test_investment_performance_uses_explicit_opening_cost_basis() -> None:
    snapshot = InvestmentPerformanceEngine().calculate(
        asset=asset(cost="100"),
        valuation=valuation("150"),
        opening_cost_basis="120",
        reference_datetime=REFERENCE,
    )

    assert snapshot.cost_basis == Decimal("120")
    assert snapshot.unrealized_gain == Decimal("30")


def test_investment_performance_currency_conversion_warning() -> None:
    snapshot = InvestmentPerformanceEngine().calculate(
        asset=asset(cost="100", currency="USD"),
        valuation=valuation("3200", currency="TWD"),
        reference_datetime=REFERENCE,
    )

    assert snapshot.cost_currency == "USD"
    assert snapshot.market_currency == "TWD"
    assert "Currency Conversion Not Applied" in snapshot.warnings


def test_investment_performance_to_dict() -> None:
    payload = calculate(cost="100", market_value="150").to_dict()

    assert payload["cost_basis"] == "100.00"
    assert payload["market_value"] == "150.00"
    assert payload["unrealized_gain"] == "50.00"
    assert payload["unrealized_gain_percent"] == "0.50"
    assert payload["performance_status"] == "POSITIVE"


def test_investment_performance_deterministic_replay() -> None:
    engine = InvestmentPerformanceEngine()
    source_asset = asset(cost="100")
    source_valuation = valuation("150")

    first = engine.calculate(
        asset=source_asset,
        valuation=source_valuation,
        reference_datetime=REFERENCE,
    ).to_dict()
    second = engine.calculate(
        asset=source_asset,
        valuation=source_valuation,
        reference_datetime=REFERENCE,
    ).to_dict()

    assert first == second


def test_investment_performance_no_mutation() -> None:
    source_asset = asset(cost="100")
    source_valuation = valuation("150")
    before_asset = deepcopy(source_asset)
    before_valuation = deepcopy(source_valuation)

    InvestmentPerformanceEngine().calculate(
        asset=source_asset,
        valuation=source_valuation,
        reference_datetime=REFERENCE,
    )

    assert source_asset == before_asset
    assert source_valuation == before_valuation


def calculate(
    *,
    cost: str,
    market_value: str,
    purchase_date: str = "2026-07-01",
) -> InvestmentPerformanceSnapshot:
    return InvestmentPerformanceEngine().calculate(
        asset=asset(cost=cost, purchase_date=purchase_date),
        valuation=valuation(market_value),
        reference_datetime=REFERENCE,
    )


def asset(
    *,
    cost: str,
    currency: str = "USD",
    purchase_date: str = "2026-07-01",
) -> dict[str, str]:
    return {
        "asset_id": "card-1",
        "cost": cost,
        "currency": currency,
        "purchase_date": purchase_date,
    }


def valuation(value: str, *, currency: str = "USD") -> dict[str, str]:
    return {
        "asset_id": "card-1",
        "market_value": value,
        "currency": currency,
    }

