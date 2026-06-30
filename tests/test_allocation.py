import json
from datetime import UTC, datetime
from decimal import Decimal

from onecool_os.__main__ import main
from onecool_os.intelligence.allocation.engine import AllocationEngine
from onecool_os.intelligence.allocation.models import AllocationResult
from onecool_os.intelligence.valuation.models import ValuationResult


def test_allocation_result_to_dict() -> None:
    result = AllocationResult(
        asset_type="CASH",
        asset_name="Demo Cash",
        market_value=Decimal("100000"),
        allocation_percent=Decimal("25"),
    )

    payload = result.to_dict()

    assert payload["asset_type"] == "CASH"
    assert payload["asset_name"] == "Demo Cash"
    assert payload["market_value"] == "100000.00"
    assert payload["allocation_percent"] == "25.00"


def test_allocation_engine_calculates_allocations() -> None:
    valuations = [
        _valuation("Demo Fund", "MUTUAL_FUND", "25"),
        _valuation("Demo Cash", "CASH", "75"),
    ]

    results = AllocationEngine().calculate(valuations)

    assert len(results) == 2
    assert results[0].asset_name == "Demo Fund"
    assert results[0].allocation_percent == Decimal("25.00")
    assert results[1].allocation_percent == Decimal("75.00")


def test_allocation_engine_returns_portfolio_total() -> None:
    valuations = [
        _valuation("Demo Fund", "MUTUAL_FUND", "25"),
        _valuation("Demo Cash", "CASH", "75"),
    ]

    assert AllocationEngine().portfolio_total(valuations) == Decimal("100")


def test_allocation_percentages_total_100() -> None:
    valuations = [
        _valuation("Demo Fund", "MUTUAL_FUND", "25"),
        _valuation("Demo Cash", "CASH", "75"),
    ]

    results = AllocationEngine().calculate(valuations)
    total_percent = sum(
        (result.allocation_percent for result in results),
        Decimal("0"),
    )

    assert total_percent == Decimal("100.00")


def test_allocation_engine_handles_empty_input() -> None:
    engine = AllocationEngine()

    assert engine.calculate([]) == ()
    assert engine.portfolio_total([]) == Decimal("0")


def test_allocation_engine_handles_zero_total() -> None:
    valuations = [
        _valuation("Demo Fund", "MUTUAL_FUND", "0"),
        _valuation("Demo Cash", "CASH", "0"),
    ]

    results = AllocationEngine().calculate(valuations)

    assert results[0].allocation_percent == Decimal("0")
    assert results[1].allocation_percent == Decimal("0")


def test_cli_allocation_demo_works(capsys) -> None:
    assert main(["allocation", "demo"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert len(payload["allocations"]) == 4
    assert payload["allocations"][0]["asset"] == "Demo Fund"
    assert payload["allocations"][0]["market_value"] == "10000.00"
    assert payload["allocations"][0]["allocation_percent"] == "0.03"
    assert payload["portfolio_total"] == "30115000.00"


def _valuation(
    asset_id: str,
    asset_type: str,
    estimated_value: str,
) -> ValuationResult:
    return ValuationResult(
        asset_id=asset_id,
        asset_type=asset_type,
        provider="demo",
        estimated_value=Decimal(estimated_value),
        currency="TWD",
        valuation_time=datetime(2026, 6, 30, tzinfo=UTC),
        confidence=0.5,
        notes="Mock valuation.",
    )
