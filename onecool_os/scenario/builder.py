"""Scenario Engine builder."""

from __future__ import annotations

from typing import Any

from onecool_os.scenario.models import Scenario
from onecool_os.scenario.models import ScenarioSet


class ScenarioBuilder:
    """Build deterministic A/B/C/D scenario sets from structured context."""

    def build(self, context: dict[str, Any] | None = None) -> ScenarioSet:
        """Build a default A/B/C/D scenario set."""

        payload = dict(context or {})
        assumptions = _copy_dict(payload.get("assumptions"))
        impacts = _copy_dict(payload.get("impacts"))
        triggers = _copy_list(payload.get("triggers"))
        actions = _copy_list(payload.get("actions"))
        tags = _copy_list(payload.get("tags")) or ["scenario", "abcd"]
        scenario_set_id = str(
            payload.get("scenario_set_id") or "scenario-set-abcd"
        )
        scenario_set_name = str(
            payload.get("scenario_set_name") or "A/B/C/D Scenario Set"
        )
        scenarios = (
            Scenario(
                scenario_id="scenario-a-base",
                scenario_name="A: Base Case",
                scenario_type="BASE",
                description="Current structured context continues.",
                severity="LOW",
                time_horizon="MEDIUM_TERM",
                assumptions=assumptions,
                triggers=triggers,
                impacts=impacts,
                actions=actions,
                tags=["A", "base"],
            ),
            Scenario(
                scenario_id="scenario-b-upside",
                scenario_name="B: Upside Case",
                scenario_type="UPSIDE",
                description="Favorable structured context improves outcomes.",
                severity="LOW",
                time_horizon="MEDIUM_TERM",
                assumptions=assumptions,
                triggers=triggers,
                impacts=impacts,
                actions=actions,
                tags=["B", "upside"],
            ),
            Scenario(
                scenario_id="scenario-c-downside",
                scenario_name="C: Downside Case",
                scenario_type="DOWNSIDE",
                description=(
                    "Unfavorable structured context pressures outcomes."
                ),
                severity="MEDIUM",
                time_horizon="MEDIUM_TERM",
                assumptions=assumptions,
                triggers=triggers,
                impacts=impacts,
                actions=actions,
                tags=["C", "downside"],
            ),
            Scenario(
                scenario_id="scenario-d-stress",
                scenario_name="D: Stress Case",
                scenario_type="STRESS",
                description="Severe structured context tests resilience.",
                severity="HIGH",
                time_horizon="SHORT_TERM",
                assumptions=assumptions,
                triggers=triggers,
                impacts=impacts,
                actions=actions,
                tags=["D", "stress"],
            ),
        )
        return ScenarioSet(
            scenario_set_id=scenario_set_id,
            scenario_set_name=scenario_set_name,
            base_case_id="scenario-a-base",
            scenarios=scenarios,
            note="Deterministic A/B/C/D scenario set.",
            tags=tags,
        )


def _copy_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _copy_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return list(value)
    return []
