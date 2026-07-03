"""Registry for business logic calculators and evaluators."""

from __future__ import annotations

from onecool_os.business_logic.calculators import BaseCalculator
from onecool_os.business_logic.evaluators import BaseEvaluator
from onecool_os.business_logic.validation import BusinessLogicError


class BusinessLogicRegistry:
    """Register and retrieve business logic engines."""

    def __init__(self) -> None:
        self._calculators: dict[str, BaseCalculator] = {}
        self._evaluators: dict[str, BaseEvaluator] = {}

    def register_calculator(self, calculator: BaseCalculator) -> None:
        """Register a calculator by engine name."""

        if calculator.engine_name in self._calculators:
            raise BusinessLogicError(
                f"Duplicate calculator: {calculator.engine_name}"
            )
        self._calculators[calculator.engine_name] = calculator

    def register_evaluator(self, evaluator: BaseEvaluator) -> None:
        """Register an evaluator by engine name."""

        if evaluator.engine_name in self._evaluators:
            raise BusinessLogicError(
                f"Duplicate evaluator: {evaluator.engine_name}"
            )
        self._evaluators[evaluator.engine_name] = evaluator

    def list_calculators(self) -> tuple[BaseCalculator, ...]:
        """Return calculators in stable engine name order."""

        return tuple(
            self._calculators[name]
            for name in sorted(self._calculators)
        )

    def list_evaluators(self) -> tuple[BaseEvaluator, ...]:
        """Return evaluators in stable engine name order."""

        return tuple(
            self._evaluators[name]
            for name in sorted(self._evaluators)
        )

    def get_calculator(self, name: str) -> BaseCalculator:
        """Return a calculator by name."""

        try:
            return self._calculators[name]
        except KeyError as exc:
            raise BusinessLogicError(f"Unknown calculator: {name}") from exc

    def get_evaluator(self, name: str) -> BaseEvaluator:
        """Return an evaluator by name."""

        try:
            return self._evaluators[name]
        except KeyError as exc:
            raise BusinessLogicError(f"Unknown evaluator: {name}") from exc
