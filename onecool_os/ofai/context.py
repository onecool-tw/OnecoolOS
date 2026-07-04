"""OFAI read-only input context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from onecool_os.ofai.validation import parse_optional_dict
from onecool_os.ofai.validation import require_text


@dataclass(frozen=True)
class OFAIContext:
    """Read-only deterministic context for OFAI planning."""

    context_id: str
    business_logic_results: Any | None = None
    analytics_snapshot: Any | None = None
    dashboard_view: Any | None = None
    scenario_set: Any | None = None
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
