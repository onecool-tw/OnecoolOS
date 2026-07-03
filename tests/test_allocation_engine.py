from decimal import Decimal

from onecool_os.business_logic import AllocationEngine
from onecool_os.business_logic import BusinessLogicContext
from onecool_os.business_logic import MetricType
from onecool_os.portfolio.models import Holding


def test_allocation_engine_supports_context() -> None:
    engine = AllocationEngine()
    context = BusinessLogicContext(context_id="context-1")

    assert engine.engine_name == "allocation"
    assert engine.engine_version == "v1"
    assert engine.supports(context) is True


def test_allocation_engine_empty_portfolio() -> None:
    result = AllocationEngine().calculate(
        BusinessLogicContext(context_id="empty", base_currency="TWD")
    )

    assert result.metric_type == MetricType.ALLOCATION
    assert result.value == Decimal("0")
    assert result.currency == "TWD"
    assert result.payload["total_value"] == Decimal("0")
    assert result.payload["categories"] == {}
    assert result.payload["weights"] == {}


def test_allocation_engine_single_asset() -> None:
    context = BusinessLogicContext(
        context_id="single",
        ledger_data={
            "holdings": [
                holding("SPY", "ETF", "100"),
            ]
        },
    )

    result = AllocationEngine().calculate(context)

    assert result.payload["total_value"] == Decimal("100")
    assert result.payload["categories"] == {"ETF": Decimal("100")}
    assert result.payload["weights"] == {"ETF": Decimal("1")}
    assert result.value == Decimal("100")


def test_allocation_engine_multiple_categories() -> None:
    context = BusinessLogicContext(
        context_id="multi",
        ledger_data={
            "holdings": [
                holding("cash", "CASH", "30"),
                holding("spy", "ETF", "40"),
                holding("card", "SPORTS_CARD", "30"),
            ]
        },
    )

    result = AllocationEngine().calculate(context)

    assert result.payload["categories"] == {
        "Cash": Decimal("30"),
        "Collectible": Decimal("30"),
        "ETF": Decimal("40"),
    }
    assert result.payload["weights"]["Cash"] == Decimal("0.3")
    assert result.payload["weights"]["Collectible"] == Decimal("0.3")
    assert result.payload["weights"]["ETF"] == Decimal("0.4")


def test_allocation_engine_multiple_assets_same_category() -> None:
    context = BusinessLogicContext(
        context_id="same-category",
        ledger_data={
            "holdings": [
                holding("spy", "ETF", "40"),
                holding("qqq", "ETF", "60"),
            ]
        },
    )

    result = AllocationEngine().calculate(context)

    assert result.payload["categories"] == {"ETF": Decimal("100")}
    assert result.payload["weights"] == {"ETF": Decimal("1")}


def test_allocation_engine_weights_total_one() -> None:
    context = BusinessLogicContext(
        context_id="weights",
        ledger_data={
            "holdings": [
                holding("cash", "CASH", "1"),
                holding("bond", "BOND", "2"),
            ]
        },
    )

    result = AllocationEngine().calculate(context)
    total_weight = sum(result.payload["weights"].values(), Decimal("0"))

    assert abs(total_weight - Decimal("1")) <= Decimal("0.0000000001")


def test_allocation_engine_deterministic_output() -> None:
    context = BusinessLogicContext(
        context_id="deterministic",
        ledger_data={
            "holdings": [
                holding("z", "CRYPTO", "5"),
                holding("a", "CASH", "5"),
                holding("m", "ETF", "10"),
            ]
        },
    )

    first = AllocationEngine().calculate(context).payload
    second = AllocationEngine().calculate(context).payload

    assert first == second
    assert tuple(first["categories"]) == ("Cash", "Crypto", "ETF")


def test_allocation_engine_edge_cases() -> None:
    context = BusinessLogicContext(
        context_id="edge",
        ledger_data={
            "holdings": [
                holding("zero", "CASH", "0"),
                holding("missing", "ETF", None),
                holding("negative", "CRYPTO", "-10"),
            ]
        },
    )

    result = AllocationEngine().calculate(context)

    assert result.payload["total_value"] == Decimal("0")
    assert result.payload["categories"]["Cash"] == Decimal("0")
    assert result.payload["categories"]["ETF"] == Decimal("0")
    assert result.payload["categories"]["Crypto"] == Decimal("0")
    assert result.payload["weights"]["Cash"] == Decimal("0")


def test_allocation_engine_uses_model_objects_from_context() -> None:
    context = BusinessLogicContext(
        context_id="model-objects",
        ledger_data=[
            Holding("cash", "CASH", "1", market_value="25"),
            Holding("house", "REAL_ESTATE", "1", market_value="75"),
        ],
    )

    result = AllocationEngine().calculate(context)

    assert result.payload["categories"] == {
        "Cash": Decimal("25"),
        "Real Estate": Decimal("75"),
    }
    assert result.payload["weights"]["Cash"] == Decimal("0.25")
    assert result.payload["weights"]["Real Estate"] == Decimal("0.75")


def test_allocation_engine_reads_ledger_context_only() -> None:
    context = BusinessLogicContext(
        context_id="ledger-first",
        ledger_data=None,
        portfolio_data={"holdings": [holding("portfolio", "ETF", "200")]},
    )

    result = AllocationEngine().calculate(context)

    assert result.payload["total_value"] == Decimal("0")
    assert result.payload["categories"] == {}


def holding(
    asset_id: str,
    asset_type: str,
    market_value: str | None,
) -> dict[str, str]:
    payload = {
        "asset_id": asset_id,
        "asset_type": asset_type,
    }
    if market_value is not None:
        payload["market_value"] = market_value
    return payload
