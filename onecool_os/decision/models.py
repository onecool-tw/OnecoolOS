"""Decision Engine models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from onecool_os.decision.enums import ConstraintType
from onecool_os.decision.enums import DecisionConfidence
from onecool_os.decision.enums import DecisionReadiness
from onecool_os.decision.enums import DecisionSeverity
from onecool_os.decision.enums import DecisionType
from onecool_os.decision.validation import DecisionError
from onecool_os.decision.validation import optional_text
from onecool_os.decision.validation import parse_decimal_between
from onecool_os.decision.validation import parse_enum
from onecool_os.decision.validation import parse_optional_datetime
from onecool_os.decision.validation import parse_optional_dict
from onecool_os.decision.validation import parse_optional_enum
from onecool_os.decision.validation import parse_text_list
from onecool_os.decision.validation import require_text


@dataclass(frozen=True)
class DecisionOption:
    """A possible deterministic decision path."""

    option_id: str
    title: str
    decision_type: DecisionType | str
    description: str | None = None
    estimated_impact: dict[str, Any] | None = None
    assumptions: dict[str, Any] | None = None
    tags: list[str] | tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "option_id",
            require_text(self.option_id, "option_id"),
        )
        object.__setattr__(self, "title", require_text(self.title, "title"))
        object.__setattr__(
            self,
            "decision_type",
            parse_enum(DecisionType, self.decision_type, "decision_type"),
        )
        object.__setattr__(
            self,
            "description",
            optional_text(self.description, "description"),
        )
        object.__setattr__(
            self,
            "estimated_impact",
            parse_optional_dict(self.estimated_impact, "estimated_impact"),
        )
        object.__setattr__(
            self,
            "assumptions",
            parse_optional_dict(self.assumptions, "assumptions"),
        )
        object.__setattr__(self, "tags", parse_text_list(self.tags, "tags"))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe option payload."""

        return {
            "option_id": self.option_id,
            "title": self.title,
            "description": self.description,
            "decision_type": self.decision_type.value,
            "estimated_impact": self.estimated_impact,
            "assumptions": self.assumptions,
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class DecisionConstraint:
    """A deterministic constraint for a decision candidate."""

    constraint_id: str
    constraint_type: ConstraintType | str
    severity: DecisionSeverity | str
    message: str
    blocking: bool = False
    payload: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "constraint_id",
            require_text(self.constraint_id, "constraint_id"),
        )
        object.__setattr__(
            self,
            "constraint_type",
            parse_enum(
                ConstraintType,
                self.constraint_type,
                "constraint_type",
            ),
        )
        object.__setattr__(
            self,
            "severity",
            parse_enum(DecisionSeverity, self.severity, "severity"),
        )
        object.__setattr__(
            self,
            "message",
            require_text(self.message, "message"),
        )
        object.__setattr__(self, "blocking", bool(self.blocking))
        object.__setattr__(
            self,
            "payload",
            parse_optional_dict(self.payload, "payload"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe constraint payload."""

        return {
            "constraint_id": self.constraint_id,
            "constraint_type": self.constraint_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "blocking": self.blocking,
            "payload": self.payload,
        }


@dataclass(frozen=True)
class DecisionScore:
    """A deterministic option score."""

    score_id: str
    score: Decimal | str | int | float | None = None
    confidence: DecisionConfidence | str | None = None
    completeness: Decimal | str | int | float | None = None
    evidence: dict[str, Any] | None = None
    reasoning: list[str] | tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "score_id",
            require_text(self.score_id, "score_id"),
        )
        object.__setattr__(
            self,
            "score",
            parse_decimal_between(
                self.score,
                "score",
                Decimal("0"),
                Decimal("100"),
            ),
        )
        object.__setattr__(
            self,
            "confidence",
            parse_optional_enum(
                DecisionConfidence,
                self.confidence,
                "confidence",
            ),
        )
        object.__setattr__(
            self,
            "completeness",
            parse_decimal_between(
                self.completeness,
                "completeness",
                Decimal("0"),
                Decimal("1"),
            ),
        )
        object.__setattr__(
            self,
            "evidence",
            parse_optional_dict(self.evidence, "evidence"),
        )
        object.__setattr__(
            self,
            "reasoning",
            parse_text_list(self.reasoning, "reasoning"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe score payload."""

        return {
            "score_id": self.score_id,
            "score": _format_optional_decimal(self.score),
            "confidence": (
                self.confidence.value if self.confidence is not None else None
            ),
            "completeness": _format_optional_decimal(self.completeness),
            "evidence": self.evidence,
            "reasoning": list(self.reasoning),
        }


@dataclass(frozen=True)
class DecisionCandidate:
    """A decision option with constraints, score, and readiness."""

    candidate_id: str
    option: DecisionOption
    constraints: (
        list[DecisionConstraint] | tuple[DecisionConstraint, ...] | None
    ) = None
    score: DecisionScore | None = None
    readiness: DecisionReadiness | str | None = None
    note: str | None = None
    tags: list[str] | tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "candidate_id",
            require_text(self.candidate_id, "candidate_id"),
        )
        if not isinstance(self.option, DecisionOption):
            raise DecisionError("option must be a DecisionOption.")
        constraints = tuple(self.constraints or ())
        object.__setattr__(self, "constraints", constraints)
        if (
            self.score is not None
            and not isinstance(self.score, DecisionScore)
        ):
            raise DecisionError("score must be a DecisionScore.")
        object.__setattr__(
            self,
            "readiness",
            parse_optional_enum(
                DecisionReadiness,
                self.readiness,
                "readiness",
            ),
        )
        object.__setattr__(self, "note", optional_text(self.note, "note"))
        object.__setattr__(self, "tags", parse_text_list(self.tags, "tags"))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe candidate payload."""

        return {
            "candidate_id": self.candidate_id,
            "option": self.option.to_dict(),
            "constraints": [
                constraint.to_dict() for constraint in self.constraints
            ],
            "score": self.score.to_dict() if self.score else None,
            "readiness": (
                self.readiness.value if self.readiness is not None else None
            ),
            "note": self.note,
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class DecisionResult:
    """Decision Engine output."""

    result_id: str
    context_id: str
    candidates: list[DecisionCandidate] | tuple[DecisionCandidate, ...]
    summary: str | None = None
    warnings: list[str] | tuple[str, ...] | None = None
    generated_at: datetime | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "result_id",
            require_text(self.result_id, "result_id"),
        )
        object.__setattr__(
            self,
            "context_id",
            require_text(self.context_id, "context_id"),
        )
        candidates = tuple(self.candidates or ())
        _validate_unique_candidates(candidates)
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(
            self,
            "summary",
            optional_text(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "warnings",
            parse_text_list(self.warnings, "warnings"),
        )
        object.__setattr__(
            self,
            "generated_at",
            parse_optional_datetime(self.generated_at, "generated_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe decision result payload."""

        generated_at = None
        if self.generated_at is not None:
            generated_at = self.generated_at.isoformat()
        return {
            "result_id": self.result_id,
            "context_id": self.context_id,
            "candidates": [
                candidate.to_dict() for candidate in self.candidates
            ],
            "summary": self.summary,
            "warnings": list(self.warnings),
            "generated_at": generated_at,
        }


def _validate_unique_candidates(
    candidates: tuple[DecisionCandidate, ...],
) -> None:
    seen: set[str] = set()
    for candidate in candidates:
        if candidate.candidate_id in seen:
            raise DecisionError(
                f"Duplicate candidate_id: {candidate.candidate_id}"
            )
        seen.add(candidate.candidate_id)


def _format_optional_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)
