from decimal import Decimal

from onecool_os.business_logic import BaseCalculator
from onecool_os.business_logic import BaseEvaluator
from onecool_os.business_logic import BasePolicy
from onecool_os.business_logic import BusinessLogicContext
from onecool_os.business_logic import BusinessLogicError
from onecool_os.business_logic import BusinessLogicRegistry
from onecool_os.business_logic import BusinessLogicResult
from onecool_os.business_logic import MetricType
from onecool_os.business_logic import SignalResult
from onecool_os.business_logic import SignalSeverity


def test_business_logic_context_creation() -> None:
    context = BusinessLogicContext(
        context_id="context-1",
        portfolio_id="portfolio-1",
        base_currency="twd",
        ledger_data={"transactions": []},
        valuation_data={"valuations": []},
        portfolio_data={"holdings": []},
        analytics_data={"snapshots": []},
        metadata={"source": "test"},
    )

    assert context.context_id == "context-1"
    assert context.portfolio_id == "portfolio-1"
    assert context.base_currency == "TWD"
    assert context.metadata == {"source": "test"}


def test_business_logic_context_requires_context_id() -> None:
    try:
        BusinessLogicContext(context_id="")
    except BusinessLogicError as exc:
        assert "context_id must be a non-empty string" in str(exc)
    else:
        raise AssertionError("Missing context_id should be rejected.")


def test_business_logic_result_creation() -> None:
    result = BusinessLogicResult(
        result_id="result-1",
        engine_name="demo-calculator",
        engine_version="0.1.0",
        metric_type="roi",
        value="0.25",
        currency="twd",
        payload={"sample": True},
        confidence="high",
        generated_at="2026-04-01T08:00:00+08:00",
        note="Demo result.",
        tags=["demo"],
    )

    assert result.metric_type == MetricType.ROI
    assert result.value == Decimal("0.25")
    assert result.currency == "TWD"
    assert result.confidence.value == "HIGH"
    assert result.to_dict()["metric_type"] == "ROI"


def test_business_logic_result_rejects_invalid_metric_type() -> None:
    try:
        BusinessLogicResult(
            result_id="result-1",
            engine_name="demo",
            engine_version="0.1.0",
            metric_type="BAD",
        )
    except BusinessLogicError as exc:
        assert "Invalid metric_type" in str(exc)
    else:
        raise AssertionError("Invalid metric_type should be rejected.")


def test_business_logic_result_rejects_invalid_confidence() -> None:
    try:
        BusinessLogicResult(
            result_id="result-1",
            engine_name="demo",
            engine_version="0.1.0",
            metric_type="ROI",
            confidence="BAD",
        )
    except BusinessLogicError as exc:
        assert "Invalid confidence" in str(exc)
    else:
        raise AssertionError("Invalid confidence should be rejected.")


def test_signal_result_creation() -> None:
    signal = SignalResult(
        signal_id="signal-1",
        engine_name="demo-evaluator",
        engine_version="0.1.0",
        signal_type="CONCENTRATION_WARNING",
        severity="medium",
        message="Concentration is elevated.",
        payload={"asset_type": "ETF"},
        generated_at="2026-04-01T08:00:00+08:00",
        tags=["demo"],
    )

    assert signal.severity == SignalSeverity.MEDIUM
    assert signal.message == "Concentration is elevated."
    assert signal.to_dict()["severity"] == "MEDIUM"


def test_signal_result_rejects_invalid_severity() -> None:
    try:
        SignalResult(
            signal_id="signal-1",
            engine_name="demo",
            engine_version="0.1.0",
            signal_type="TEST",
            severity="BAD",
            message="Demo signal.",
        )
    except BusinessLogicError as exc:
        assert "Invalid severity" in str(exc)
    else:
        raise AssertionError("Invalid severity should be rejected.")


def test_signal_result_requires_signal_type() -> None:
    try:
        SignalResult(
            signal_id="signal-1",
            engine_name="demo",
            engine_version="0.1.0",
            signal_type="",
            severity="INFO",
            message="Demo signal.",
        )
    except BusinessLogicError as exc:
        assert "signal_type must be a non-empty string" in str(exc)
    else:
        raise AssertionError("Missing signal_type should be rejected.")


def test_base_calculator_contract() -> None:
    context = BusinessLogicContext(context_id="context-1")
    calculator = DemoCalculator()

    assert calculator.supports(context) is True
    result = calculator.calculate(context)

    assert result.engine_name == "demo-calculator"
    assert result.metric_type == MetricType.CASH_FLOW


def test_base_calculator_default_methods_raise() -> None:
    calculator = BaseCalculator("base", "0.1.0")
    context = BusinessLogicContext(context_id="context-1")

    try:
        calculator.supports(context)
    except BusinessLogicError as exc:
        assert "does not implement supports" in str(exc)
    else:
        raise AssertionError("BaseCalculator.supports should be overridden.")


def test_base_evaluator_contract() -> None:
    context = BusinessLogicContext(context_id="context-1")
    evaluator = DemoEvaluator()

    assert evaluator.supports(context) is True
    signal = evaluator.evaluate(context)

    assert signal.engine_name == "demo-evaluator"
    assert signal.severity == SignalSeverity.INFO


def test_base_evaluator_default_methods_raise() -> None:
    evaluator = BaseEvaluator("base", "0.1.0")
    context = BusinessLogicContext(context_id="context-1")

    try:
        evaluator.evaluate(context)
    except BusinessLogicError as exc:
        assert "does not implement evaluate" in str(exc)
    else:
        raise AssertionError("BaseEvaluator.evaluate should be overridden.")


def test_base_policy_validation() -> None:
    policy = BasePolicy(
        policy_name="demo-policy",
        policy_version="0.1.0",
        rules={"max_weight": "0.25"},
    )

    assert policy.policy_name == "demo-policy"
    assert policy.rules == {"max_weight": "0.25"}


def test_base_policy_rejects_invalid_rules() -> None:
    try:
        BasePolicy(
            policy_name="demo-policy",
            policy_version="0.1.0",
            rules=["bad"],
        )
    except BusinessLogicError as exc:
        assert "rules must be a dictionary" in str(exc)
    else:
        raise AssertionError("Invalid policy rules should be rejected.")


def test_business_logic_registry() -> None:
    registry = BusinessLogicRegistry()
    calculator = DemoCalculator()
    evaluator = DemoEvaluator()

    registry.register_calculator(calculator)
    registry.register_evaluator(evaluator)

    assert registry.get_calculator("demo-calculator") is calculator
    assert registry.get_evaluator("demo-evaluator") is evaluator
    assert registry.list_calculators() == (calculator,)
    assert registry.list_evaluators() == (evaluator,)


def test_business_logic_registry_rejects_duplicates() -> None:
    registry = BusinessLogicRegistry()
    registry.register_calculator(DemoCalculator())
    registry.register_evaluator(DemoEvaluator())

    try:
        registry.register_calculator(DemoCalculator())
    except BusinessLogicError as exc:
        assert "Duplicate calculator" in str(exc)
    else:
        raise AssertionError("Duplicate calculator should be rejected.")

    try:
        registry.register_evaluator(DemoEvaluator())
    except BusinessLogicError as exc:
        assert "Duplicate evaluator" in str(exc)
    else:
        raise AssertionError("Duplicate evaluator should be rejected.")


def test_business_logic_registry_unknown_entries() -> None:
    registry = BusinessLogicRegistry()

    try:
        registry.get_calculator("missing")
    except BusinessLogicError as exc:
        assert "Unknown calculator" in str(exc)
    else:
        raise AssertionError("Unknown calculator should be rejected.")

    try:
        registry.get_evaluator("missing")
    except BusinessLogicError as exc:
        assert "Unknown evaluator" in str(exc)
    else:
        raise AssertionError("Unknown evaluator should be rejected.")


class DemoCalculator(BaseCalculator):
    def __init__(self) -> None:
        super().__init__("demo-calculator", "0.1.0")

    def supports(self, context: BusinessLogicContext) -> bool:
        return bool(context.context_id)

    def calculate(
        self,
        context: BusinessLogicContext,
    ) -> BusinessLogicResult:
        return BusinessLogicResult(
            result_id=f"{context.context_id}-cash-flow",
            engine_name=self.engine_name,
            engine_version=self.engine_version,
            metric_type="CASH_FLOW",
            value="0",
            confidence="MEDIUM",
        )


class DemoEvaluator(BaseEvaluator):
    def __init__(self) -> None:
        super().__init__("demo-evaluator", "0.1.0")

    def supports(self, context: BusinessLogicContext) -> bool:
        return bool(context.context_id)

    def evaluate(self, context: BusinessLogicContext) -> SignalResult:
        return SignalResult(
            signal_id=f"{context.context_id}-signal",
            engine_name=self.engine_name,
            engine_version=self.engine_version,
            signal_type="DEMO_SIGNAL",
            severity="INFO",
            message="Demo signal.",
        )
