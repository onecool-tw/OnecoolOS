"""Business Logic Pipeline Runner foundation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from onecool_os.business_logic.context import BusinessLogicContext
from onecool_os.business_logic.registry import BusinessLogicRegistry
from onecool_os.business_logic.results import BusinessLogicResult
from onecool_os.business_logic.results import SignalResult
from onecool_os.business_logic.validation import parse_optional_datetime
from onecool_os.business_logic.validation import parse_optional_dict
from onecool_os.business_logic.validation import require_text


@dataclass(frozen=True)
class BusinessLogicPipelineResult:
    """Structured report for a Business Logic pipeline execution."""

    pipeline_id: str
    context_id: str
    engine_results: list[BusinessLogicResult] | tuple[BusinessLogicResult, ...]
    signal_results: list[SignalResult] | tuple[SignalResult, ...]
    executed_engines: list[str] | tuple[str, ...]
    skipped_engines: list[str] | tuple[str, ...]
    errors: list[str] | tuple[str, ...]
    generated_at: datetime | str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "pipeline_id",
            require_text(self.pipeline_id, "pipeline_id"),
        )
        object.__setattr__(
            self,
            "context_id",
            require_text(self.context_id, "context_id"),
        )
        object.__setattr__(
            self,
            "engine_results",
            tuple(self.engine_results or ()),
        )
        object.__setattr__(
            self,
            "signal_results",
            tuple(self.signal_results or ()),
        )
        object.__setattr__(
            self,
            "executed_engines",
            tuple(str(engine) for engine in self.executed_engines or ()),
        )
        object.__setattr__(
            self,
            "skipped_engines",
            tuple(str(engine) for engine in self.skipped_engines or ()),
        )
        object.__setattr__(
            self,
            "errors",
            tuple(str(error) for error in self.errors or ()),
        )
        object.__setattr__(
            self,
            "generated_at",
            parse_optional_datetime(self.generated_at, "generated_at"),
        )
        object.__setattr__(
            self,
            "metadata",
            parse_optional_dict(self.metadata, "metadata"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe pipeline execution report."""

        generated_at = None
        if self.generated_at is not None:
            generated_at = self.generated_at.isoformat()
        return {
            "pipeline_id": self.pipeline_id,
            "context_id": self.context_id,
            "engine_results": [
                result.to_dict() for result in self.engine_results
            ],
            "signal_results": [
                result.to_dict() for result in self.signal_results
            ],
            "executed_engines": list(self.executed_engines),
            "skipped_engines": list(self.skipped_engines),
            "errors": list(self.errors),
            "generated_at": generated_at,
            "metadata": self.metadata,
        }


class BusinessLogicRunner:
    """Run registered Business Logic engines in deterministic order."""

    default_execution_order = (
        "cash_flow",
        "allocation",
        "performance",
        "risk",
    )

    def __init__(
        self,
        registry: BusinessLogicRegistry,
        execution_order: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        self.registry = registry
        self.execution_order = tuple(
            execution_order or self.default_execution_order
        )

    def run(
        self,
        context: BusinessLogicContext,
    ) -> BusinessLogicPipelineResult:
        """Execute registered calculators and evaluators."""

        calculators = {
            engine.engine_name: engine
            for engine in self.registry.list_calculators()
        }
        evaluators = {
            engine.engine_name: engine
            for engine in self.registry.list_evaluators()
        }
        engine_results: list[BusinessLogicResult] = []
        signal_results: list[SignalResult] = []
        executed_engines: list[str] = []
        skipped_engines: list[str] = []
        errors: list[str] = []

        for engine_name in self.execution_order:
            _run_calculator(
                engine_name,
                calculators,
                context,
                engine_results,
                executed_engines,
                skipped_engines,
                errors,
            )
            _run_evaluator(
                engine_name,
                evaluators,
                context,
                signal_results,
                executed_engines,
                skipped_engines,
                errors,
            )

        return BusinessLogicPipelineResult(
            pipeline_id=f"{context.context_id}-business-logic-pipeline",
            context_id=context.context_id,
            engine_results=engine_results,
            signal_results=signal_results,
            executed_engines=executed_engines,
            skipped_engines=skipped_engines,
            errors=errors,
            metadata={"execution_order": list(self.execution_order)},
        )


def _run_calculator(
    engine_name: str,
    calculators: dict[str, Any],
    context: BusinessLogicContext,
    engine_results: list[BusinessLogicResult],
    executed_engines: list[str],
    skipped_engines: list[str],
    errors: list[str],
) -> None:
    calculator = calculators.get(engine_name)
    if calculator is None:
        skipped_engines.append(f"{engine_name}:calculator:missing")
        return
    label = f"{engine_name}:calculator"
    try:
        if not calculator.supports(context):
            skipped_engines.append(f"{label}:unsupported")
            return
        engine_results.append(calculator.calculate(context))
        executed_engines.append(label)
    except Exception as exc:  # noqa: BLE001 - pipeline records engine errors.
        errors.append(f"{label}:{exc}")


def _run_evaluator(
    engine_name: str,
    evaluators: dict[str, Any],
    context: BusinessLogicContext,
    signal_results: list[SignalResult],
    executed_engines: list[str],
    skipped_engines: list[str],
    errors: list[str],
) -> None:
    evaluator = evaluators.get(engine_name)
    if evaluator is None:
        skipped_engines.append(f"{engine_name}:evaluator:missing")
        return
    label = f"{engine_name}:evaluator"
    try:
        if not evaluator.supports(context):
            skipped_engines.append(f"{label}:unsupported")
            return
        signal_results.extend(_normalize_signals(evaluator.evaluate(context)))
        executed_engines.append(label)
    except Exception as exc:  # noqa: BLE001 - pipeline records engine errors.
        errors.append(f"{label}:{exc}")


def _normalize_signals(value: Any) -> tuple[SignalResult, ...]:
    if value is None:
        return ()
    if isinstance(value, SignalResult):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(
            signal for signal in value
            if isinstance(signal, SignalResult)
        )
    return ()
