"""Decision Engine foundation."""

from __future__ import annotations

from typing import Any

from onecool_os.decision.audit import DecisionAuditTrail
from onecool_os.decision.context import DecisionContext
from onecool_os.decision.enums import ConstraintType
from onecool_os.decision.enums import DecisionReadiness
from onecool_os.decision.enums import DecisionSeverity
from onecool_os.decision.models import DecisionCandidate
from onecool_os.decision.models import DecisionConstraint
from onecool_os.decision.models import DecisionOption
from onecool_os.decision.models import DecisionResult
from onecool_os.decision.models import DecisionScore
from onecool_os.decision.validation import DecisionError


class DecisionEngine:
    """Evaluate deterministic decision options."""

    def evaluate(
        self,
        context: DecisionContext,
        options: (
            list[DecisionOption] | tuple[DecisionOption, ...] | None
        ) = None,
    ) -> tuple[DecisionResult, DecisionAuditTrail]:
        """Evaluate options and return result plus audit trail."""

        options_tuple = tuple(options or ())
        _validate_unique_options(options_tuple)
        constraints_checked: list[str] = []
        candidates = []
        errors: list[str] = []
        for option in options_tuple:
            try:
                constraints = _constraints_for_option(context, option)
                constraints_checked.extend(
                    constraint.constraint_id for constraint in constraints
                )
                readiness = _readiness_from_constraints(constraints)
                candidates.append(
                    DecisionCandidate(
                        candidate_id=f"candidate-{option.option_id}",
                        option=option,
                        constraints=constraints,
                        score=_score_for_option(option, constraints),
                        readiness=readiness,
                        note="Deterministic candidate evaluation.",
                        tags=["decision", "deterministic"],
                    )
                )
            except DecisionError as exc:
                errors.append(str(exc))
        result = DecisionResult(
            result_id=f"{context.context_id}-decision-result",
            context_id=context.context_id,
            candidates=candidates,
            summary=_summary(candidates),
            warnings=_warnings(candidates),
        )
        audit = DecisionAuditTrail(
            audit_id=f"{context.context_id}-decision-audit",
            context_id=context.context_id,
            rules_applied=[
                "validate_unique_options",
                "evaluate_constraints",
                "assign_readiness",
            ],
            constraints_checked=constraints_checked,
            candidates_generated=[
                candidate.candidate_id for candidate in candidates
            ],
            errors=errors,
        )
        return result, audit


def _validate_unique_options(options: tuple[DecisionOption, ...]) -> None:
    seen: set[str] = set()
    for option in options:
        if option.option_id in seen:
            raise DecisionError(f"Duplicate option_id: {option.option_id}")
        seen.add(option.option_id)


def _constraints_for_option(
    context: DecisionContext,
    option: DecisionOption,
) -> tuple[DecisionConstraint, ...]:
    constraints = []
    if context.analytics_snapshot is None:
        constraints.append(
            DecisionConstraint(
                constraint_id=f"{option.option_id}-analytics-missing",
                constraint_type=ConstraintType.DATA_MISSING,
                severity=DecisionSeverity.HIGH,
                message="Analytics snapshot is missing.",
                blocking=False,
                payload={"source": "analytics_snapshot"},
            )
        )
    if context.scenario_set is None:
        constraints.append(
            DecisionConstraint(
                constraint_id=f"{option.option_id}-scenario-missing",
                constraint_type=ConstraintType.MANUAL_REVIEW_REQUIRED,
                severity=DecisionSeverity.MEDIUM,
                message="Scenario set is missing.",
                blocking=False,
                payload={"source": "scenario_set"},
            )
        )
    for raw_constraint in _metadata_constraints(context.metadata):
        constraints.append(raw_constraint)
    return tuple(constraints)


def _metadata_constraints(
    metadata: dict[str, Any],
) -> tuple[DecisionConstraint, ...]:
    constraints = []
    for index, payload in enumerate(metadata.get("constraints", ())):
        if not isinstance(payload, dict):
            continue
        constraints.append(
            DecisionConstraint(
                constraint_id=str(
                    payload.get("constraint_id")
                    or f"metadata-constraint-{index}"
                ),
                constraint_type=payload.get(
                    "constraint_type",
                    ConstraintType.MANUAL_REVIEW_REQUIRED,
                ),
                severity=payload.get("severity", DecisionSeverity.MEDIUM),
                message=str(payload.get("message") or "Metadata constraint."),
                blocking=bool(payload.get("blocking", False)),
                payload=dict(payload.get("payload") or {}),
            )
        )
    return tuple(constraints)


def _readiness_from_constraints(
    constraints: tuple[DecisionConstraint, ...],
) -> DecisionReadiness:
    if any(constraint.blocking for constraint in constraints):
        return DecisionReadiness.BLOCKED
    if any(
        constraint.severity in (
            DecisionSeverity.HIGH,
            DecisionSeverity.CRITICAL,
        )
        for constraint in constraints
    ):
        return DecisionReadiness.NEEDS_REVIEW
    return DecisionReadiness.READY


def _score_for_option(
    option: DecisionOption,
    constraints: tuple[DecisionConstraint, ...],
) -> DecisionScore:
    score = 100
    for constraint in constraints:
        if constraint.blocking:
            score -= 60
        elif constraint.severity == DecisionSeverity.CRITICAL:
            score -= 40
        elif constraint.severity == DecisionSeverity.HIGH:
            score -= 25
        elif constraint.severity == DecisionSeverity.MEDIUM:
            score -= 10
        elif constraint.severity == DecisionSeverity.LOW:
            score -= 5
    score = max(score, 0)
    return DecisionScore(
        score_id=f"{option.option_id}-score",
        score=score,
        confidence="LOW",
        completeness="0.5",
        evidence={"constraint_count": len(constraints)},
        reasoning=["Deterministic foundation score from constraints."],
    )


def _summary(candidates: list[DecisionCandidate]) -> str:
    if not candidates:
        return "No decision options were evaluated."
    return f"{len(candidates)} decision option(s) evaluated."


def _warnings(candidates: list[DecisionCandidate]) -> list[str]:
    warnings = []
    for candidate in candidates:
        if candidate.readiness == DecisionReadiness.BLOCKED:
            warnings.append(f"{candidate.candidate_id} is blocked.")
        elif candidate.readiness == DecisionReadiness.NEEDS_REVIEW:
            warnings.append(f"{candidate.candidate_id} needs review.")
    return warnings
