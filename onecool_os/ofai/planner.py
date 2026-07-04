"""OFAI deterministic planning orchestrator."""

from __future__ import annotations

from typing import Any

from onecool_os.ofai.context import OFAIContext
from onecool_os.ofai.enums import ConfidenceLevel
from onecool_os.ofai.enums import PlanningMode
from onecool_os.ofai.models import OFAIPlan
from onecool_os.ofai.validation import parse_enum


class OFAIPlanner:
    """Prepare structured plans from deterministic Onecool OS context."""

    def __init__(self, mode: PlanningMode | str = PlanningMode.DAILY) -> None:
        self.mode = parse_enum(PlanningMode, mode, "planning_mode")

    def plan(self, context: OFAIContext) -> OFAIPlan:
        """Aggregate deterministic inputs into an OFAI plan."""

        inputs = _input_summary(context)
        observations = _observations(context, inputs)
        next_steps = _next_steps(inputs)
        return OFAIPlan(
            plan_id=f"{context.context_id}-ofai-plan",
            title=f"OFAI {self.mode.value.title()} Plan",
            summary="Structured deterministic decision context prepared.",
            inputs=inputs,
            observations=observations,
            next_steps=next_steps,
            confidence=ConfidenceLevel.LOW,
        )


def _input_summary(context: OFAIContext) -> dict[str, Any]:
    return {
        "context_id": context.context_id,
        "planning_mode": context.metadata.get("planning_mode"),
        "business_logic_result_count": _count_items(
            context.business_logic_results
        ),
        "has_analytics_snapshot": context.analytics_snapshot is not None,
        "has_dashboard_view": context.dashboard_view is not None,
        "scenario_count": _scenario_count(context.scenario_set),
        "metadata": dict(context.metadata),
    }


def _observations(
    context: OFAIContext,
    inputs: dict[str, Any],
) -> list[str]:
    observations = []
    if inputs["business_logic_result_count"]:
        observations.append("Business Logic outputs are available.")
    if inputs["has_analytics_snapshot"]:
        observations.append("Analytics snapshot is available.")
    if inputs["has_dashboard_view"]:
        observations.append("Dashboard view is available.")
    if inputs["scenario_count"]:
        observations.append("Scenario objects are available.")
    if not observations:
        observations.append("No deterministic inputs are available yet.")
    if context.metadata:
        observations.append("Context metadata is available.")
    return observations


def _next_steps(inputs: dict[str, Any]) -> list[str]:
    steps = ["Review deterministic context before AI reasoning."]
    if not inputs["business_logic_result_count"]:
        steps.append("Run Business Logic pipeline.")
    if not inputs["has_analytics_snapshot"]:
        steps.append("Build Analytics snapshot.")
    if not inputs["scenario_count"]:
        steps.append("Build Scenario set.")
    return steps


def _count_items(value: Any) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, dict):
        if "engine_results" in value:
            return len(value.get("engine_results") or ())
        return len(value)
    if isinstance(value, (list, tuple)):
        return len(value)
    if hasattr(value, "engine_results"):
        return len(getattr(value, "engine_results") or ())
    return 1


def _scenario_count(value: Any) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, dict):
        return len(value.get("scenarios") or ())
    if hasattr(value, "scenarios"):
        return len(getattr(value, "scenarios") or ())
    return 1
