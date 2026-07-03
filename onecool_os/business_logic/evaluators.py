"""Base evaluator contract for business logic engines."""

from __future__ import annotations

from dataclasses import dataclass

from onecool_os.business_logic.context import BusinessLogicContext
from onecool_os.business_logic.results import SignalResult
from onecool_os.business_logic.validation import BusinessLogicError
from onecool_os.business_logic.validation import require_text


@dataclass(frozen=True)
class BaseEvaluator:
    """Base class for deterministic rule evaluators."""

    engine_name: str
    engine_version: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "engine_name",
            require_text(self.engine_name, "engine_name"),
        )
        object.__setattr__(
            self,
            "engine_version",
            require_text(self.engine_version, "engine_version"),
        )

    def supports(self, context: BusinessLogicContext) -> bool:
        """Return whether this evaluator supports the input context."""

        raise BusinessLogicError(
            f"{self.engine_name} does not implement supports()."
        )

    def evaluate(self, context: BusinessLogicContext) -> SignalResult:
        """Evaluate the context and return a rule-based signal."""

        raise BusinessLogicError(
            f"{self.engine_name} does not implement evaluate()."
        )
