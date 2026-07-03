from decimal import Decimal

from onecool_os.business_logic import AllocationEngine
from onecool_os.business_logic import BaseCalculator
from onecool_os.business_logic import BaseEvaluator
from onecool_os.business_logic import BusinessLogicContext
from onecool_os.business_logic import BusinessLogicPipelineResult
from onecool_os.business_logic import BusinessLogicRegistry
from onecool_os.business_logic import BusinessLogicResult
from onecool_os.business_logic import BusinessLogicRunner
from onecool_os.business_logic import CashFlowEngine
from onecool_os.business_logic import PerformanceEngine
from onecool_os.business_logic import RiskEngine
from onecool_os.business_logic import SignalResult


def test_pipeline_empty_registry() -> None:
    result = BusinessLogicRunner(BusinessLogicRegistry()).run(
        BusinessLogicContext(context_id="pipeline-empty")
    )

    assert result.context_id == "pipeline-empty"
    assert result.engine_results == ()
    assert result.signal_results == ()
    assert result.executed_engines == ()
    assert len(result.skipped_engines) == 8
    assert result.errors == ()


def test_pipeline_deterministic_execution_order() -> None:
    registry = BusinessLogicRegistry()
    registry.register_calculator(FakeCalculator("beta"))
    registry.register_calculator(FakeCalculator("alpha"))
    runner = BusinessLogicRunner(
        registry,
        execution_order=("alpha", "beta"),
    )

    result = runner.run(BusinessLogicContext(context_id="pipeline-order"))

    assert result.executed_engines == (
        "alpha:calculator",
        "beta:calculator",
    )
    assert [item.engine_name for item in result.engine_results] == [
        "alpha",
        "beta",
    ]


def test_pipeline_calculator_execution() -> None:
    registry = BusinessLogicRegistry()
    registry.register_calculator(FakeCalculator("cash_flow"))

    result = BusinessLogicRunner(registry).run(
        BusinessLogicContext(context_id="pipeline-calculator")
    )

    assert result.engine_results[0].engine_name == "cash_flow"
    assert "cash_flow:calculator" in result.executed_engines


def test_pipeline_evaluator_execution() -> None:
    registry = BusinessLogicRegistry()
    registry.register_evaluator(FakeEvaluator("risk"))

    result = BusinessLogicRunner(registry).run(
        BusinessLogicContext(context_id="pipeline-evaluator")
    )

    assert result.signal_results[0].signal_type == "risk_signal"
    assert "risk:evaluator" in result.executed_engines


def test_pipeline_unsupported_engine_skipped() -> None:
    registry = BusinessLogicRegistry()
    registry.register_calculator(UnsupportedCalculator("cash_flow"))

    result = BusinessLogicRunner(registry).run(
        BusinessLogicContext(context_id="pipeline-unsupported")
    )

    assert "cash_flow:calculator:unsupported" in result.skipped_engines
    assert result.engine_results == ()


def test_pipeline_engine_error_recorded() -> None:
    registry = BusinessLogicRegistry()
    registry.register_calculator(ErrorCalculator("cash_flow"))

    result = BusinessLogicRunner(registry).run(
        BusinessLogicContext(context_id="pipeline-error")
    )

    assert result.engine_results == ()
    assert len(result.errors) == 1
    assert result.errors[0].startswith("cash_flow:calculator:")


def test_pipeline_context_not_mutated() -> None:
    ledger_data = {"holdings": [holding("cash", "CASH", "1", "100")]}
    context = BusinessLogicContext(
        context_id="pipeline-read-only",
        ledger_data=ledger_data,
    )
    registry = BusinessLogicRegistry()
    registry.register_calculator(FakeCalculator("cash_flow"))

    BusinessLogicRunner(registry).run(context)

    assert context.ledger_data == ledger_data
    assert context.ledger_data is ledger_data


def test_pipeline_result_structure() -> None:
    result = BusinessLogicPipelineResult(
        pipeline_id="pipeline-1",
        context_id="context-1",
        engine_results=[],
        signal_results=[],
        executed_engines=["cash_flow:calculator"],
        skipped_engines=["risk:evaluator:missing"],
        errors=[],
        metadata={"source": "test"},
    )

    payload = result.to_dict()

    assert payload["pipeline_id"] == "pipeline-1"
    assert payload["context_id"] == "context-1"
    assert payload["engine_results"] == []
    assert payload["signal_results"] == []
    assert payload["executed_engines"] == ["cash_flow:calculator"]
    assert payload["skipped_engines"] == ["risk:evaluator:missing"]
    assert payload["errors"] == []
    assert payload["metadata"] == {"source": "test"}


def test_pipeline_integration_with_existing_engines() -> None:
    registry = BusinessLogicRegistry()
    registry.register_calculator(CashFlowEngine())
    registry.register_calculator(AllocationEngine())
    registry.register_calculator(PerformanceEngine())
    risk_engine = RiskEngine()
    registry.register_calculator(risk_engine)
    registry.register_evaluator(risk_engine)
    context = BusinessLogicContext(
        context_id="pipeline-integration",
        base_currency="TWD",
        ledger_data={
            "holdings": [
                holding("cash", "CASH", "1", "100"),
                holding("spy", "ETF", "2", "50"),
            ],
            "transactions": [
                {
                    "transaction_type": "DEPOSIT",
                    "price": "100",
                }
            ],
        },
        portfolio_data={
            "holdings": [
                holding("cash", "CASH", "1", "100"),
                holding("spy", "ETF", "2", "50"),
            ]
        },
        valuation_data={"valuations": [{"asset_id": "cash", "value": "100"}]},
    )

    result = BusinessLogicRunner(registry).run(context)

    assert [item.engine_name for item in result.engine_results] == [
        "cash_flow",
        "allocation",
        "performance",
        "risk",
    ]
    assert result.executed_engines == (
        "cash_flow:calculator",
        "allocation:calculator",
        "performance:calculator",
        "risk:calculator",
        "risk:evaluator",
    )
    assert result.errors == ()


class FakeCalculator(BaseCalculator):
    def __init__(self, engine_name: str) -> None:
        super().__init__(engine_name=engine_name, engine_version="v1")

    def supports(self, context: BusinessLogicContext) -> bool:
        return True

    def calculate(
        self,
        context: BusinessLogicContext,
    ) -> BusinessLogicResult:
        return BusinessLogicResult(
            result_id=f"{context.context_id}-{self.engine_name}",
            engine_name=self.engine_name,
            engine_version=self.engine_version,
            metric_type="CASH_FLOW",
            value=Decimal("1"),
        )


class UnsupportedCalculator(FakeCalculator):
    def supports(self, context: BusinessLogicContext) -> bool:
        return False


class ErrorCalculator(FakeCalculator):
    def calculate(
        self,
        context: BusinessLogicContext,
    ) -> BusinessLogicResult:
        raise RuntimeError("calculation failed")


class FakeEvaluator(BaseEvaluator):
    def __init__(self, engine_name: str) -> None:
        super().__init__(engine_name=engine_name, engine_version="v1")

    def supports(self, context: BusinessLogicContext) -> bool:
        return True

    def evaluate(self, context: BusinessLogicContext) -> SignalResult:
        return SignalResult(
            signal_id=f"{context.context_id}-{self.engine_name}",
            engine_name=self.engine_name,
            engine_version=self.engine_version,
            signal_type=f"{self.engine_name}_signal",
            severity="INFO",
            message="Signal generated.",
        )


def holding(
    asset_id: str,
    asset_type: str,
    quantity: str,
    market_value: str,
) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "quantity": quantity,
        "average_cost": market_value,
        "market_value": market_value,
    }
