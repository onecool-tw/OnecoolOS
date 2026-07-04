"""OFAI foundation models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from onecool_os.ofai.enums import ConfidenceLevel
from onecool_os.ofai.validation import optional_text
from onecool_os.ofai.validation import parse_optional_datetime
from onecool_os.ofai.validation import parse_optional_dict
from onecool_os.ofai.validation import parse_optional_enum
from onecool_os.ofai.validation import parse_text_list
from onecool_os.ofai.validation import require_text


@dataclass(frozen=True)
class OFAIPlan:
    """Structured OFAI planning output."""

    plan_id: str
    title: str
    summary: str
    inputs: dict[str, Any] | None = None
    observations: list[str] | tuple[str, ...] | None = None
    next_steps: list[str] | tuple[str, ...] | None = None
    confidence: ConfidenceLevel | str | None = None
    generated_at: datetime | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "plan_id",
            require_text(self.plan_id, "plan_id"),
        )
        object.__setattr__(self, "title", require_text(self.title, "title"))
        object.__setattr__(
            self,
            "summary",
            require_text(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "inputs",
            parse_optional_dict(self.inputs, "inputs"),
        )
        object.__setattr__(
            self,
            "observations",
            parse_text_list(self.observations, "observations"),
        )
        object.__setattr__(
            self,
            "next_steps",
            parse_text_list(self.next_steps, "next_steps"),
        )
        object.__setattr__(
            self,
            "confidence",
            parse_optional_enum(
                ConfidenceLevel,
                self.confidence,
                "confidence",
            ),
        )
        object.__setattr__(
            self,
            "generated_at",
            parse_optional_datetime(self.generated_at, "generated_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe OFAI plan."""

        generated_at = None
        if self.generated_at is not None:
            generated_at = self.generated_at.isoformat()
        return {
            "plan_id": self.plan_id,
            "title": self.title,
            "summary": self.summary,
            "inputs": self.inputs,
            "observations": list(self.observations),
            "next_steps": list(self.next_steps),
            "confidence": (
                self.confidence.value if self.confidence is not None else None
            ),
            "generated_at": generated_at,
        }
