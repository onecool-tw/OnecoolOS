"""Scenario Engine models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from onecool_os.scenario.enums import ScenarioSeverity
from onecool_os.scenario.enums import ScenarioType
from onecool_os.scenario.enums import TimeHorizon
from onecool_os.scenario.validation import ScenarioError
from onecool_os.scenario.validation import optional_text
from onecool_os.scenario.validation import parse_enum
from onecool_os.scenario.validation import parse_optional_datetime
from onecool_os.scenario.validation import parse_optional_dict
from onecool_os.scenario.validation import parse_optional_enum
from onecool_os.scenario.validation import parse_probability
from onecool_os.scenario.validation import parse_text_list
from onecool_os.scenario.validation import require_text


@dataclass(frozen=True)
class Scenario:
    """Structured deterministic scenario object."""

    scenario_id: str
    scenario_name: str
    scenario_type: ScenarioType | str
    description: str | None = None
    probability: Decimal | str | int | float | None = None
    severity: ScenarioSeverity | str | None = None
    time_horizon: TimeHorizon | str | None = None
    assumptions: dict[str, Any] | None = None
    triggers: list[str] | tuple[str, ...] | None = None
    impacts: dict[str, Any] | None = None
    actions: list[str] | tuple[str, ...] | None = None
    tags: list[str] | tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "scenario_id",
            require_text(self.scenario_id, "scenario_id"),
        )
        object.__setattr__(
            self,
            "scenario_name",
            require_text(self.scenario_name, "scenario_name"),
        )
        object.__setattr__(
            self,
            "scenario_type",
            parse_enum(ScenarioType, self.scenario_type, "scenario_type"),
        )
        object.__setattr__(
            self,
            "description",
            optional_text(self.description, "description"),
        )
        object.__setattr__(
            self,
            "probability",
            parse_probability(self.probability),
        )
        object.__setattr__(
            self,
            "severity",
            parse_optional_enum(
                ScenarioSeverity,
                self.severity,
                "severity",
            ),
        )
        object.__setattr__(
            self,
            "time_horizon",
            parse_optional_enum(
                TimeHorizon,
                self.time_horizon,
                "time_horizon",
            ),
        )
        object.__setattr__(
            self,
            "assumptions",
            parse_optional_dict(self.assumptions, "assumptions"),
        )
        object.__setattr__(
            self,
            "triggers",
            parse_text_list(self.triggers, "triggers"),
        )
        object.__setattr__(
            self,
            "impacts",
            parse_optional_dict(self.impacts, "impacts"),
        )
        object.__setattr__(
            self,
            "actions",
            parse_text_list(self.actions, "actions"),
        )
        object.__setattr__(self, "tags", parse_text_list(self.tags, "tags"))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe scenario payload."""

        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "scenario_type": self.scenario_type.value,
            "description": self.description,
            "probability": _format_optional_decimal(self.probability),
            "severity": self.severity.value if self.severity else None,
            "time_horizon": (
                self.time_horizon.value if self.time_horizon else None
            ),
            "assumptions": self.assumptions,
            "triggers": list(self.triggers),
            "impacts": self.impacts,
            "actions": list(self.actions),
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class ScenarioSet:
    """A deterministic set of related scenarios."""

    scenario_set_id: str
    scenario_set_name: str
    scenarios: list[Scenario] | tuple[Scenario, ...]
    base_case_id: str | None = None
    generated_at: datetime | str | None = None
    note: str | None = None
    tags: list[str] | tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "scenario_set_id",
            require_text(self.scenario_set_id, "scenario_set_id"),
        )
        object.__setattr__(
            self,
            "scenario_set_name",
            require_text(self.scenario_set_name, "scenario_set_name"),
        )
        object.__setattr__(
            self,
            "base_case_id",
            optional_text(self.base_case_id, "base_case_id"),
        )
        scenarios = tuple(self.scenarios or ())
        _validate_unique_scenarios(scenarios)
        object.__setattr__(self, "scenarios", scenarios)
        object.__setattr__(
            self,
            "generated_at",
            parse_optional_datetime(self.generated_at, "generated_at"),
        )
        object.__setattr__(self, "note", optional_text(self.note, "note"))
        object.__setattr__(self, "tags", parse_text_list(self.tags, "tags"))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe scenario set payload."""

        generated_at = None
        if self.generated_at is not None:
            generated_at = self.generated_at.isoformat()
        return {
            "scenario_set_id": self.scenario_set_id,
            "scenario_set_name": self.scenario_set_name,
            "base_case_id": self.base_case_id,
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "generated_at": generated_at,
            "note": self.note,
            "tags": list(self.tags),
        }


def _validate_unique_scenarios(scenarios: tuple[Scenario, ...]) -> None:
    seen: set[str] = set()
    for scenario in scenarios:
        if scenario.scenario_id in seen:
            raise ScenarioError(
                f"Duplicate scenario_id: {scenario.scenario_id}"
            )
        seen.add(scenario.scenario_id)


def _format_optional_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)
