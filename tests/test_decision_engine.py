from onecool_os.decision import ConstraintType
from onecool_os.decision import DecisionAuditTrail
from onecool_os.decision import DecisionCandidate
from onecool_os.decision import DecisionConfidence
from onecool_os.decision import DecisionConstraint
from onecool_os.decision import DecisionContext
from onecool_os.decision import DecisionEngine
from onecool_os.decision import DecisionError
from onecool_os.decision import DecisionOption
from onecool_os.decision import DecisionReadiness
from onecool_os.decision import DecisionResult
from onecool_os.decision import DecisionScore
from onecool_os.decision import DecisionSeverity
from onecool_os.decision import DecisionType


def test_decision_context() -> None:
    context = DecisionContext(
        context_id="context-1",
        business_logic_results=[{"metric_type": "RISK"}],
        analytics_snapshot={"snapshot_id": "snapshot-1"},
        dashboard_summary={"dashboard_id": "dashboard-1"},
        scenario_set={"scenario_set_id": "scenario-set-1"},
        ofai_context={"context_id": "ofai-1"},
        metadata={"source": "test"},
    )

    assert context.context_id == "context-1"
    assert context.metadata == {"source": "test"}
    assert context.analytics_snapshot == {"snapshot_id": "snapshot-1"}


def test_decision_option() -> None:
    option = decision_option()

    assert option.option_id == "option-1"
    assert option.decision_type == DecisionType.REVIEW
    assert option.to_dict()["decision_type"] == "REVIEW"


def test_decision_candidate() -> None:
    candidate = DecisionCandidate(
        candidate_id="candidate-1",
        option=decision_option(),
        constraints=[decision_constraint()],
        score=decision_score(),
        readiness="ready",
        note="Ready",
        tags=["demo"],
    )

    assert candidate.readiness == DecisionReadiness.READY
    assert candidate.constraints[0].severity == DecisionSeverity.HIGH
    assert candidate.tags == ("demo",)


def test_decision_constraint() -> None:
    constraint = decision_constraint()

    assert constraint.constraint_type == ConstraintType.DATA_MISSING
    assert constraint.severity == DecisionSeverity.HIGH
    assert constraint.blocking is False


def test_decision_score() -> None:
    score = decision_score()

    assert score.score == 80
    assert score.confidence == DecisionConfidence.MEDIUM
    assert score.completeness == 1
    assert score.to_dict()["score"] == "80"


def test_decision_result() -> None:
    candidate = DecisionCandidate(
        candidate_id="candidate-1",
        option=decision_option(),
    )
    result = DecisionResult(
        result_id="result-1",
        context_id="context-1",
        candidates=[candidate],
        summary="One candidate.",
        warnings=["Review candidate."],
        generated_at="2026-01-01T00:00:00+08:00",
    )

    assert result.result_id == "result-1"
    assert result.candidates == (candidate,)
    assert result.to_dict()["generated_at"] == "2026-01-01T00:00:00+08:00"


def test_decision_audit_trail() -> None:
    audit = DecisionAuditTrail(
        audit_id="audit-1",
        context_id="context-1",
        rules_applied=["assign_readiness"],
        constraints_checked=["constraint-1"],
        candidates_generated=["candidate-1"],
        errors=[],
    )

    assert audit.audit_id == "audit-1"
    assert audit.rules_applied == ("assign_readiness",)
    assert audit.to_dict()["candidates_generated"] == ["candidate-1"]


def test_decision_enums() -> None:
    assert DecisionType.REBALANCE.value == "REBALANCE"
    assert DecisionReadiness.BLOCKED.value == "BLOCKED"
    assert DecisionConfidence.HIGH.value == "HIGH"
    assert DecisionSeverity.CRITICAL.value == "CRITICAL"
    assert ConstraintType.RISK_TOO_HIGH.value == "RISK_TOO_HIGH"


def test_decision_validation() -> None:
    try:
        DecisionContext(context_id="")
    except DecisionError as exc:
        assert "context_id must be a non-empty string" in str(exc)
    else:
        raise AssertionError("Missing context_id should fail.")

    try:
        DecisionOption(
            option_id="",
            title="Review",
            decision_type="REVIEW",
        )
    except DecisionError as exc:
        assert "option_id must be a non-empty string" in str(exc)
    else:
        raise AssertionError("Missing option_id should fail.")

    try:
        DecisionOption(
            option_id="option-1",
            title="",
            decision_type="REVIEW",
        )
    except DecisionError as exc:
        assert "title must be a non-empty string" in str(exc)
    else:
        raise AssertionError("Missing title should fail.")


def test_decision_invalid_enum_values() -> None:
    invalid_cases = (
        lambda: DecisionOption("option-1", "Option", "INVALID"),
        lambda: DecisionCandidate(
            "candidate-1",
            decision_option(),
            readiness="INVALID",
        ),
        lambda: DecisionConstraint(
            "constraint-1",
            "INVALID",
            "HIGH",
            "Message",
        ),
        lambda: DecisionConstraint(
            "constraint-1",
            "DATA_MISSING",
            "INVALID",
            "Message",
        ),
        lambda: DecisionScore("score-1", confidence="INVALID"),
    )
    for factory in invalid_cases:
        try:
            factory()
        except DecisionError:
            pass
        else:
            raise AssertionError("Invalid enum value should fail.")


def test_decision_score_bounds() -> None:
    for value in ("-1", "101"):
        try:
            DecisionScore("score-1", score=value)
        except DecisionError as exc:
            assert "score must be between 0 and 100" in str(exc)
        else:
            raise AssertionError("Invalid score should fail.")

    for value in ("-0.1", "1.1"):
        try:
            DecisionScore("score-1", completeness=value)
        except DecisionError as exc:
            assert "completeness must be between 0 and 1" in str(exc)
        else:
            raise AssertionError("Invalid completeness should fail.")


def test_decision_duplicate_option_ids() -> None:
    option = decision_option()

    try:
        DecisionEngine().evaluate(
            complete_context(),
            options=[option, option],
        )
    except DecisionError as exc:
        assert "Duplicate option_id" in str(exc)
    else:
        raise AssertionError("Duplicate option_id should fail.")


def test_decision_duplicate_candidate_ids() -> None:
    candidate = DecisionCandidate(
        candidate_id="candidate-1",
        option=decision_option(),
    )

    try:
        DecisionResult(
            result_id="result-1",
            context_id="context-1",
            candidates=[candidate, candidate],
        )
    except DecisionError as exc:
        assert "Duplicate candidate_id" in str(exc)
    else:
        raise AssertionError("Duplicate candidate_id should fail.")


def test_decision_engine_with_no_options() -> None:
    result, audit = DecisionEngine().evaluate(complete_context())

    assert result.candidates == ()
    assert result.summary == "No decision options were evaluated."
    assert audit.candidates_generated == ()
    assert audit.errors == ()


def test_decision_engine_ready() -> None:
    result, audit = DecisionEngine().evaluate(
        complete_context(),
        options=[decision_option()],
    )

    candidate = result.candidates[0]
    assert candidate.readiness == DecisionReadiness.READY
    assert candidate.constraints == ()
    assert candidate.score.score == 100
    assert audit.candidates_generated == ("candidate-option-1",)


def test_decision_engine_needs_review() -> None:
    result, _audit = DecisionEngine().evaluate(
        DecisionContext(
            context_id="context-review",
            scenario_set={"scenario_set_id": "scenario-set-1"},
        ),
        options=[decision_option()],
    )

    candidate = result.candidates[0]
    assert candidate.readiness == DecisionReadiness.NEEDS_REVIEW
    assert candidate.constraints[0].severity == DecisionSeverity.HIGH
    assert result.warnings == ("candidate-option-1 needs review.",)


def test_decision_engine_blocked() -> None:
    context = complete_context(metadata={
        "constraints": [
            {
                "constraint_id": "policy-block",
                "constraint_type": "POLICY_VIOLATION",
                "severity": "CRITICAL",
                "message": "Policy blocks option.",
                "blocking": True,
            }
        ]
    })

    result, _audit = DecisionEngine().evaluate(
        context,
        options=[decision_option()],
    )

    candidate = result.candidates[0]
    assert candidate.readiness == DecisionReadiness.BLOCKED
    assert candidate.constraints[0].blocking is True
    assert result.warnings == ("candidate-option-1 is blocked.",)


def test_decision_engine_audit_trail() -> None:
    result, audit = DecisionEngine().evaluate(
        DecisionContext(context_id="context-audit"),
        options=[decision_option()],
    )

    assert result.context_id == "context-audit"
    assert audit.audit_id == "context-audit-decision-audit"
    assert "assign_readiness" in audit.rules_applied
    assert audit.constraints_checked == (
        "option-1-analytics-missing",
        "option-1-scenario-missing",
    )


def test_decision_engine_no_mutation_behavior() -> None:
    metadata = {"constraints": []}
    context = complete_context(metadata=metadata)
    option = decision_option()
    before_metadata = dict(context.metadata)
    before_option = option.to_dict()

    DecisionEngine().evaluate(context, options=[option])

    assert context.metadata == before_metadata
    assert option.to_dict() == before_option


def decision_option() -> DecisionOption:
    return DecisionOption(
        option_id="option-1",
        title="Review Portfolio",
        decision_type="REVIEW",
        description="Review deterministic context.",
        estimated_impact={"risk": "neutral"},
        assumptions={"source": "deterministic"},
        tags=["demo"],
    )


def decision_constraint() -> DecisionConstraint:
    return DecisionConstraint(
        constraint_id="constraint-1",
        constraint_type="DATA_MISSING",
        severity="HIGH",
        message="Data is missing.",
        payload={"source": "analytics"},
    )


def decision_score() -> DecisionScore:
    return DecisionScore(
        score_id="score-1",
        score="80",
        confidence="MEDIUM",
        completeness="1",
        evidence={"source": "test"},
        reasoning=["Evidence is complete."],
    )


def complete_context(metadata: dict | None = None) -> DecisionContext:
    return DecisionContext(
        context_id="context-1",
        analytics_snapshot={"snapshot_id": "snapshot-1"},
        scenario_set={"scenario_set_id": "scenario-set-1"},
        metadata=metadata,
    )
