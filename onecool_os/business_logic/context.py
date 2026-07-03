"""Read-only input context for business logic engines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from onecool_os.business_logic.validation import optional_currency
from onecool_os.business_logic.validation import optional_text
from onecool_os.business_logic.validation import parse_optional_dict
from onecool_os.business_logic.validation import require_text


@dataclass(frozen=True)
class BusinessLogicContext:
    """Read-only input bundle for deterministic business logic."""

    context_id: str
    portfolio_id: str | None = None
    base_currency: str | None = None
    ledger_data: Any | None = None
    valuation_data: Any | None = None
    portfolio_data: Any | None = None
    analytics_data: Any | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "context_id",
            require_text(self.context_id, "context_id"),
        )
        object.__setattr__(
            self,
            "portfolio_id",
            optional_text(self.portfolio_id, "portfolio_id"),
        )
        object.__setattr__(
            self,
            "base_currency",
            optional_currency(self.base_currency),
        )
        object.__setattr__(
            self,
            "metadata",
            parse_optional_dict(self.metadata, "metadata"),
        )
