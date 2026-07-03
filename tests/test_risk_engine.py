from decimal import Decimal

from onecool_os.business_logic import BasePolicy
from onecool_os.business_logic import BusinessLogicContext
from onecool_os.business_logic import BusinessLogicRegistry
from onecool_os.business_logic import MetricType
from onecool_os.business_logic import RiskEngine
from onecool_os.business_logic import SignalSeverity


def test_risk_engine_supports_context() -> None:
    engine = RiskEngine()
    context = BusinessLogicContext(context_id="risk-supports")

    assert engine.engine_name == "risk"
    assert engine.engine_version == "v1"
    assert engine.supports(context) is True


def test_risk_engine_empty_context() -> None:
    context = BusinessLogicContext(
        context_id="risk-empty",
        base_currency="TWD",
    )

    result = RiskEngine().calculate(context)
    signals = RiskEngine().evaluate(context)

    assert result.metric_type == MetricType.RISK
    assert result.currency == "TWD"
    assert result.payload["dimensions"]["valuation"] == "missing"
    assert result.payload["dimensions"]["history"] == "missing"
    assert result.payload["dimensions"]["cash_ratio"] == "missing"
    assert result.value == Decimal("85")
    assert {signal.signal_type for signal in signals} == {
        "missing_valuation",
        "cash_ratio",
        "diversification",
        "missing_ledger_history",
    }


def test_risk_engine_missing_valuation_signal() -> None:
    context = BusinessLogicContext(
        context_id="risk-missing-valuation",
        ledger_data={
            "holdings": [
                holding("cash", "CASH", "10"),
                holding("spy", "ETF", "90"),
            ],
            "transactions": [{"transaction_id": "txn-1"}],
        },
    )

    signals = RiskEngine().evaluate(context)

    assert "missing_valuation" in {
        signal.signal_type for signal in signals
    }
    missing_signal = get_signal(signals, "missing_valuation")
    assert missing_signal.severity == SignalSeverity.HIGH


def test_risk_engine_missing_ledger_signal() -> None:
    context = BusinessLogicContext(
        context_id="risk-missing-ledger",
        ledger_data={
            "holdings": [
                holding("cash", "CASH", "20"),
                holding("spy", "ETF", "80"),
            ],
            "transactions": [],
        },
        valuation_data={"valuations": [{"valuation_id": "value-1"}]},
    )

    result = RiskEngine().calculate(context)
    signals = RiskEngine().evaluate(context)

    assert result.payload["dimensions"]["history"] == "missing"
    assert "missing_ledger_history" in {
        signal.signal_type for signal in signals
    }


def test_risk_engine_concentration_warning() -> None:
    context = BusinessLogicContext(
        context_id="risk-concentration",
        ledger_data={
            "holdings": [
                holding("cash", "CASH", "5"),
                holding("spy", "ETF", "95"),
            ],
            "transactions": [{"transaction_id": "txn-1"}],
        },
        valuation_data={"valuations": [{"valuation_id": "value-1"}]},
    )

    result = RiskEngine().calculate(context)
    signals = RiskEngine().evaluate(context)
    concentration_signal = get_signal(signals, "concentration")

    assert result.payload["dimensions"]["concentration"] == "warning"
    assert concentration_signal.severity == SignalSeverity.HIGH
    assert concentration_signal.payload["threshold"] == "0.50"


def test_risk_engine_diversification_warning() -> None:
    context = BusinessLogicContext(
        context_id="risk-diversification",
        ledger_data={
            "holdings": [
                holding("cash", "CASH", "100"),
            ],
            "transactions": [{"transaction_id": "txn-1"}],
        },
        valuation_data={"valuations": [{"valuation_id": "value-1"}]},
    )

    result = RiskEngine().calculate(context)
    signals = RiskEngine().evaluate(context)

    assert result.payload["dimensions"]["diversification"] == "warning"
    assert "diversification" in {signal.signal_type for signal in signals}


def test_risk_engine_signal_generation_for_healthy_context() -> None:
    context = BusinessLogicContext(
        context_id="risk-healthy",
        ledger_data={
            "holdings": [
                holding("cash", "CASH", "20"),
                holding("spy", "ETF", "40"),
                holding("fund", "MUTUAL_FUND", "40"),
            ],
            "transactions": [{"transaction_id": "txn-1"}],
        },
        valuation_data={"valuations": [{"valuation_id": "value-1"}]},
    )

    result = RiskEngine().calculate(context)
    signals = RiskEngine().evaluate(context)

    assert result.payload["risk_score"] == Decimal("0")
    assert result.payload["dimensions"] == {
        "concentration": "ok",
        "liquidity": "ok",
        "cash_ratio": "ok",
        "diversification": "ok",
        "valuation": "ok",
        "history": "ok",
    }
    assert signals == ()


def test_risk_engine_registry() -> None:
    registry = BusinessLogicRegistry()
    engine = RiskEngine()

    registry.register_calculator(engine)
    registry.register_evaluator(engine)

    assert registry.get_calculator("risk") is engine
    assert registry.get_evaluator("risk") is engine


def test_risk_engine_policy_thresholds() -> None:
    policy = BasePolicy(
        policy_name="risk-policy",
        policy_version="v1",
        rules={"concentration_threshold": "0.90"},
    )
    context = BusinessLogicContext(
        context_id="risk-policy",
        ledger_data={
            "holdings": [
                holding("cash", "CASH", "20"),
                holding("spy", "ETF", "80"),
            ],
            "transactions": [{"transaction_id": "txn-1"}],
        },
        valuation_data={"valuations": [{"valuation_id": "value-1"}]},
    )

    result = RiskEngine(policy=policy).calculate(context)

    assert result.payload["dimensions"]["concentration"] == "ok"


def get_signal(signals: tuple, signal_type: str):
    for signal in signals:
        if signal.signal_type == signal_type:
            return signal
    raise AssertionError(f"Signal not found: {signal_type}")


def holding(
    asset_id: str,
    asset_type: str,
    market_value: str,
) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "market_value": market_value,
    }
