from onecool_os.business_logic import BusinessLogicResult
from onecool_os.ofai import ConfidenceLevel
from onecool_os.ofai import OFAIContext
from onecool_os.ofai import OFAIError
from onecool_os.ofai import OFAIPlan
from onecool_os.ofai import OFAIPlanner
from onecool_os.ofai import PlanningMode
from onecool_os.scenario import ScenarioBuilder


def test_ofai_context_model() -> None:
    context = OFAIContext(
        context_id="context-1",
        business_logic_results=[business_logic_result()],
        analytics_snapshot={"snapshot_id": "snapshot-1"},
        dashboard_view={"dashboard_id": "dashboard-1"},
        scenario_set={"scenarios": [{"scenario_id": "scenario-1"}]},
        metadata={"planning_mode": "DAILY"},
    )

    assert context.context_id == "context-1"
    assert context.metadata == {"planning_mode": "DAILY"}
    assert len(context.business_logic_results) == 1


def test_ofai_plan_model() -> None:
    plan = OFAIPlan(
        plan_id="plan-1",
        title="Daily Plan",
        summary="Summary",
        inputs={"context_id": "context-1"},
        observations=["Business Logic outputs are available."],
        next_steps=["Review deterministic context before AI reasoning."],
        confidence="medium",
        generated_at="2026-01-01T00:00:00+08:00",
    )

    assert plan.plan_id == "plan-1"
    assert plan.confidence == ConfidenceLevel.MEDIUM
    assert plan.to_dict()["confidence"] == "MEDIUM"
    assert plan.to_dict()["generated_at"] == "2026-01-01T00:00:00+08:00"


def test_ofai_planner() -> None:
    context = OFAIContext(
        context_id="context-plan",
        business_logic_results=[business_logic_result()],
        analytics_snapshot={"snapshot_id": "snapshot-1"},
        dashboard_view={"dashboard_id": "dashboard-1"},
        scenario_set=ScenarioBuilder().build(),
        metadata={"planning_mode": "DAILY"},
    )

    plan = OFAIPlanner(mode=PlanningMode.DAILY).plan(context)

    assert plan.plan_id == "context-plan-ofai-plan"
    assert plan.title == "OFAI Daily Plan"
    assert plan.confidence == ConfidenceLevel.LOW
    assert plan.inputs["business_logic_result_count"] == 1
    assert plan.inputs["has_analytics_snapshot"] is True
    assert plan.inputs["has_dashboard_view"] is True
    assert plan.inputs["scenario_count"] == 4
    assert "Scenario objects are available." in plan.observations


def test_ofai_validation() -> None:
    try:
        OFAIContext(context_id="")
    except OFAIError as exc:
        assert "context_id must be a non-empty string" in str(exc)
    else:
        raise AssertionError("Missing context_id should fail.")

    try:
        OFAIPlan(plan_id="", title="Title", summary="Summary")
    except OFAIError as exc:
        assert "plan_id must be a non-empty string" in str(exc)
    else:
        raise AssertionError("Missing plan_id should fail.")

    try:
        OFAIPlan(plan_id="plan-1", title="", summary="Summary")
    except OFAIError as exc:
        assert "title must be a non-empty string" in str(exc)
    else:
        raise AssertionError("Missing title should fail.")

    try:
        OFAIPlanner(mode="INVALID")
    except OFAIError as exc:
        assert "Invalid planning_mode" in str(exc)
    else:
        raise AssertionError("Invalid planning mode should fail.")

    try:
        OFAIPlan(
            plan_id="plan-1",
            title="Title",
            summary="Summary",
            confidence="INVALID",
        )
    except OFAIError as exc:
        assert "Invalid confidence" in str(exc)
    else:
        raise AssertionError("Invalid confidence should fail.")


def test_ofai_empty_context() -> None:
    plan = OFAIPlanner().plan(OFAIContext(context_id="context-empty"))

    assert plan.inputs["business_logic_result_count"] == 0
    assert plan.inputs["has_analytics_snapshot"] is False
    assert plan.inputs["has_dashboard_view"] is False
    assert plan.inputs["scenario_count"] == 0
    assert "No deterministic inputs are available yet." in plan.observations
    assert "Run Business Logic pipeline." in plan.next_steps
    assert "Build Analytics snapshot." in plan.next_steps
    assert "Build Scenario set." in plan.next_steps


def test_ofai_aggregation_behavior() -> None:
    context = OFAIContext(
        context_id="context-aggregation",
        business_logic_results={"engine_results": [business_logic_result()]},
        analytics_snapshot={"snapshot_id": "snapshot-1"},
        scenario_set={"scenarios": [{"scenario_id": "scenario-1"}]},
    )

    plan = OFAIPlanner(mode="weekly").plan(context)

    assert plan.title == "OFAI Weekly Plan"
    assert plan.inputs["business_logic_result_count"] == 1
    assert plan.inputs["scenario_count"] == 1
    assert "Dashboard view is available." not in plan.observations


def test_ofai_no_mutation() -> None:
    metadata = {"planning_mode": "EVENT"}
    business_logic_results = [business_logic_result()]
    context = OFAIContext(
        context_id="context-read-only",
        business_logic_results=business_logic_results,
        metadata=metadata,
    )
    before_metadata = dict(context.metadata)
    before_results = tuple(context.business_logic_results)

    OFAIPlanner(mode="EVENT").plan(context)

    assert context.metadata == before_metadata
    assert tuple(context.business_logic_results) == before_results


def test_ofai_enums() -> None:
    assert PlanningMode.MONTHLY.value == "MONTHLY"
    assert ConfidenceLevel.HIGH.value == "HIGH"


def business_logic_result() -> BusinessLogicResult:
    return BusinessLogicResult(
        result_id="cash-flow-result",
        engine_name="cash_flow",
        engine_version="v1",
        metric_type="CASH_FLOW",
        payload={"net_cash_flow": "100"},
    )
