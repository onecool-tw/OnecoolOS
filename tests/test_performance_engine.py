from decimal import Decimal

from onecool_os.business_logic import BusinessLogicContext
from onecool_os.business_logic import BusinessLogicRegistry
from onecool_os.business_logic import MetricType
from onecool_os.business_logic import PerformanceEngine
from onecool_os.portfolio.models import Holding
from onecool_os.portfolio.models import Portfolio


def test_performance_engine_supports_context() -> None:
    engine = PerformanceEngine()
    context = BusinessLogicContext(context_id="performance-supports")

    assert engine.engine_name == "performance"
    assert engine.engine_version == "v1"
    assert engine.supports(context) is True


def test_performance_engine_empty_context() -> None:
    result = PerformanceEngine().calculate(
        BusinessLogicContext(
            context_id="performance-empty",
            base_currency="TWD",
        )
    )

    assert result.metric_type == MetricType.PERFORMANCE
    assert result.value is None
    assert result.payload["cost_basis"] == Decimal("0")
    assert result.payload["market_value"] == Decimal("0")
    assert result.payload["unrealized_gain"] == Decimal("0")
    assert result.payload["unrealized_return"] is None
    assert result.payload["position_count"] == 0


def test_performance_engine_zero_cost() -> None:
    context = BusinessLogicContext(
        context_id="performance-zero-cost",
        portfolio_data={
            "holdings": [
                holding("cash", "CASH", "1", "0", "100"),
            ]
        },
    )

    result = PerformanceEngine().calculate(context)

    assert result.payload["cost_basis"] == Decimal("0")
    assert result.payload["market_value"] == Decimal("100")
    assert result.payload["unrealized_gain"] == Decimal("100")
    assert result.payload["unrealized_return"] is None
    assert result.value is None


def test_performance_engine_missing_valuation() -> None:
    context = BusinessLogicContext(
        context_id="performance-missing-valuation",
        portfolio_data={
            "holdings": [
                holding("spy", "ETF", "2", "50", None),
            ]
        },
        valuation_data=None,
    )

    result = PerformanceEngine().calculate(context)

    assert result.payload["cost_basis"] == Decimal("100")
    assert result.payload["market_value"] == Decimal("0")
    assert result.payload["unrealized_gain"] == Decimal("-100")
    assert result.payload["unrealized_return"] == Decimal("-1")


def test_performance_engine_positive_return() -> None:
    context = BusinessLogicContext(
        context_id="performance-positive",
        portfolio_data={
            "holdings": [
                holding("spy", "ETF", "2", "50", "120"),
            ]
        },
    )

    result = PerformanceEngine().calculate(context)

    assert result.payload["cost_basis"] == Decimal("100")
    assert result.payload["market_value"] == Decimal("120")
    assert result.payload["unrealized_gain"] == Decimal("20")
    assert result.payload["unrealized_return"] == Decimal("0.2")
    assert result.value == Decimal("0.2")


def test_performance_engine_negative_return() -> None:
    context = BusinessLogicContext(
        context_id="performance-negative",
        portfolio_data={
            "holdings": [
                holding("spy", "ETF", "2", "50", "80"),
            ]
        },
    )

    result = PerformanceEngine().calculate(context)

    assert result.payload["unrealized_gain"] == Decimal("-20")
    assert result.payload["unrealized_return"] == Decimal("-0.2")
    assert result.value == Decimal("-0.2")


def test_performance_engine_multiple_positions() -> None:
    portfolio = Portfolio(
        portfolio_id="portfolio-1",
        portfolio_name="Portfolio",
        base_currency="TWD",
        holdings=[
            Holding("cash", "CASH", "1", "100", "100"),
            Holding("spy", "ETF", "2", "50", "140"),
        ],
    )
    context = BusinessLogicContext(
        context_id="performance-multiple",
        base_currency="TWD",
        portfolio_data=portfolio,
    )

    result = PerformanceEngine().calculate(context)

    assert result.currency == "TWD"
    assert result.payload["cost_basis"] == Decimal("200")
    assert result.payload["market_value"] == Decimal("240")
    assert result.payload["unrealized_gain"] == Decimal("40")
    assert result.payload["unrealized_return"] == Decimal("0.2")
    assert result.payload["position_count"] == 2


def test_performance_engine_uses_valuation_when_market_value_missing() -> None:
    context = BusinessLogicContext(
        context_id="performance-valuation",
        portfolio_data={
            "holdings": [
                holding("spy", "ETF", "2", "50", None),
            ]
        },
        valuation_data={
            "valuations": [
                {
                    "asset_id": "spy",
                    "market_value": "130",
                }
            ]
        },
    )

    result = PerformanceEngine().calculate(context)

    assert result.payload["cost_basis"] == Decimal("100")
    assert result.payload["market_value"] == Decimal("130")
    assert result.payload["unrealized_return"] == Decimal("0.3")


def test_performance_engine_registry() -> None:
    registry = BusinessLogicRegistry()
    engine = PerformanceEngine()

    registry.register_calculator(engine)

    assert registry.get_calculator("performance") is engine


def test_performance_engine_result_metric_type() -> None:
    result = PerformanceEngine().calculate(
        BusinessLogicContext(context_id="performance-metric")
    )

    assert result.metric_type == MetricType.PERFORMANCE
    assert result.payload["realized_gain"] is None
    assert result.payload["realized_return"] is None


def holding(
    asset_id: str,
    asset_type: str,
    quantity: str,
    average_cost: str,
    market_value: str | None,
) -> dict[str, str]:
    payload = {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "quantity": quantity,
        "average_cost": average_cost,
    }
    if market_value is not None:
        payload["market_value"] = market_value
    return payload
