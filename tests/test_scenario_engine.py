from onecool_os.scenario import Scenario
from onecool_os.scenario import ScenarioBuilder
from onecool_os.scenario import ScenarioError
from onecool_os.scenario import ScenarioSet
from onecool_os.scenario import ScenarioSeverity
from onecool_os.scenario import ScenarioType
from onecool_os.scenario import TimeHorizon


def test_scenario_model() -> None:
    scenario = Scenario(
        scenario_id="scenario-1",
        scenario_name="Base",
        scenario_type="base",
        description="Base case.",
        probability="0.5",
        severity="medium",
        time_horizon="short_term",
        assumptions={"growth": "stable"},
        triggers=["monthly review"],
        impacts={"cash": "neutral"},
        actions=["observe"],
        tags=["demo"],
    )

    assert scenario.scenario_id == "scenario-1"
    assert scenario.scenario_type == ScenarioType.BASE
    assert scenario.severity == ScenarioSeverity.MEDIUM
    assert scenario.time_horizon == TimeHorizon.SHORT_TERM
    assert scenario.to_dict()["probability"] == "0.5"
    assert scenario.tags == ("demo",)


def test_scenario_set_model() -> None:
    scenario = Scenario(
        scenario_id="scenario-1",
        scenario_name="Base",
        scenario_type=ScenarioType.BASE,
    )
    scenario_set = ScenarioSet(
        scenario_set_id="set-1",
        scenario_set_name="Set",
        base_case_id="scenario-1",
        scenarios=[scenario],
        generated_at="2026-01-01T00:00:00+08:00",
        note="Demo",
        tags=["scenario"],
    )

    assert scenario_set.scenario_set_id == "set-1"
    assert scenario_set.scenarios == (scenario,)
    assert scenario_set.to_dict()["generated_at"] == (
        "2026-01-01T00:00:00+08:00"
    )


def test_scenario_enums() -> None:
    assert ScenarioType.BLACK_SWAN.value == "BLACK_SWAN"
    assert ScenarioSeverity.EXTREME.value == "EXTREME"
    assert TimeHorizon.LONG_TERM.value == "LONG_TERM"


def test_scenario_validation() -> None:
    try:
        Scenario(
            scenario_id="",
            scenario_name="Base",
            scenario_type="BASE",
        )
    except ScenarioError as exc:
        assert "scenario_id must be a non-empty string" in str(exc)
    else:
        raise AssertionError("Missing scenario_id should fail.")

    try:
        Scenario(
            scenario_id="scenario-1",
            scenario_name="Base",
            scenario_type="INVALID",
        )
    except ScenarioError as exc:
        assert "Invalid scenario_type" in str(exc)
    else:
        raise AssertionError("Invalid scenario_type should fail.")

    try:
        Scenario(
            scenario_id="scenario-1",
            scenario_name="Base",
            scenario_type="BASE",
            severity="INVALID",
        )
    except ScenarioError as exc:
        assert "Invalid severity" in str(exc)
    else:
        raise AssertionError("Invalid severity should fail.")


def test_scenario_set_duplicate_scenarios() -> None:
    scenario = Scenario(
        scenario_id="scenario-1",
        scenario_name="Base",
        scenario_type="BASE",
    )

    try:
        ScenarioSet(
            scenario_set_id="set-1",
            scenario_set_name="Set",
            scenarios=[scenario, scenario],
        )
    except ScenarioError as exc:
        assert "Duplicate scenario_id" in str(exc)
    else:
        raise AssertionError("Duplicate scenario_id should fail.")


def test_scenario_probability_bounds() -> None:
    for probability in ("-0.1", "1.1"):
        try:
            Scenario(
                scenario_id=f"scenario-{probability}",
                scenario_name="Base",
                scenario_type="BASE",
                probability=probability,
            )
        except ScenarioError as exc:
            assert "probability must be between 0 and 1" in str(exc)
        else:
            raise AssertionError("Invalid probability should fail.")


def test_scenario_builder_default_abcd() -> None:
    scenario_set = ScenarioBuilder().build({
        "scenario_set_id": "set-custom",
        "scenario_set_name": "Custom Set",
    })
    scenarios = scenario_set.scenarios

    assert scenario_set.scenario_set_id == "set-custom"
    assert scenario_set.scenario_set_name == "Custom Set"
    assert scenario_set.base_case_id == "scenario-a-base"
    assert [scenario.scenario_name for scenario in scenarios] == [
        "A: Base Case",
        "B: Upside Case",
        "C: Downside Case",
        "D: Stress Case",
    ]
    assert [scenario.scenario_type for scenario in scenarios] == [
        ScenarioType.BASE,
        ScenarioType.UPSIDE,
        ScenarioType.DOWNSIDE,
        ScenarioType.STRESS,
    ]


def test_scenario_builder_empty_context() -> None:
    scenario_set = ScenarioBuilder().build()

    assert scenario_set.scenario_set_id == "scenario-set-abcd"
    assert len(scenario_set.scenarios) == 4
    assert scenario_set.generated_at is None


def test_scenario_builder_no_mutation_behavior() -> None:
    context = {
        "assumptions": {"cash_flow": "stable"},
        "triggers": ["review"],
        "impacts": {"risk": "medium"},
        "actions": ["monitor"],
        "tags": ["input"],
    }
    before = {
        "assumptions": dict(context["assumptions"]),
        "triggers": list(context["triggers"]),
        "impacts": dict(context["impacts"]),
        "actions": list(context["actions"]),
        "tags": list(context["tags"]),
    }

    scenario_set = ScenarioBuilder().build(context)
    scenario_set.scenarios[0].assumptions["cash_flow"] = "changed"

    assert context == before
