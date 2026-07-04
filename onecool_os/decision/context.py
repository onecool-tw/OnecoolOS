"""Decision Engine read-only context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from onecool_os.decision.validation import parse_optional_dict
from onecool_os.decision.validation import require_text


@dataclass(frozen=True)
class DecisionContext:
    """Read-only deterministic input context for decision evaluation."""

    context_id: str
    business_logic_results: Any | None = None
    analytics_snapshot: Any | None = None
    dashboard_summary: Any | None = None
    scenario_set: Any | None = None
    ofai_context: Any | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "context_id",
            require_text(self.context_id, "context_id"),
        )
        object.__setattr__(
            self,
            "metadata",
            parse_optional_dict(self.metadata, "metadata"),
        )
