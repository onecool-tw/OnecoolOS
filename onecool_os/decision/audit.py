"""Decision Engine audit models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from onecool_os.decision.validation import parse_optional_datetime
from onecool_os.decision.validation import parse_text_list
from onecool_os.decision.validation import require_text


@dataclass(frozen=True)
class DecisionAuditTrail:
    """Immutable explanation of Decision Engine execution."""

    audit_id: str
    context_id: str
    rules_applied: list[str] | tuple[str, ...] | None = None
    constraints_checked: list[str] | tuple[str, ...] | None = None
    candidates_generated: list[str] | tuple[str, ...] | None = None
    errors: list[str] | tuple[str, ...] | None = None
    generated_at: datetime | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "audit_id",
            require_text(self.audit_id, "audit_id"),
        )
        object.__setattr__(
            self,
            "context_id",
            require_text(self.context_id, "context_id"),
        )
        object.__setattr__(
            self,
            "rules_applied",
            parse_text_list(self.rules_applied, "rules_applied"),
        )
        object.__setattr__(
            self,
            "constraints_checked",
            parse_text_list(
                self.constraints_checked,
                "constraints_checked",
            ),
        )
        object.__setattr__(
            self,
            "candidates_generated",
            parse_text_list(
                self.candidates_generated,
                "candidates_generated",
            ),
        )
        object.__setattr__(
            self,
            "errors",
            parse_text_list(self.errors, "errors"),
        )
        object.__setattr__(
            self,
            "generated_at",
            parse_optional_datetime(self.generated_at, "generated_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe audit payload."""

        generated_at = None
        if self.generated_at is not None:
            generated_at = self.generated_at.isoformat()
        return {
            "audit_id": self.audit_id,
            "context_id": self.context_id,
            "rules_applied": list(self.rules_applied),
            "constraints_checked": list(self.constraints_checked),
            "candidates_generated": list(self.candidates_generated),
            "errors": list(self.errors),
            "generated_at": generated_at,
        }
