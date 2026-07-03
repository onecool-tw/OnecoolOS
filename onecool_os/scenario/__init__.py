"""Scenario Engine foundation."""

from onecool_os.scenario.builder import ScenarioBuilder
from onecool_os.scenario.enums import ScenarioSeverity
from onecool_os.scenario.enums import ScenarioType
from onecool_os.scenario.enums import TimeHorizon
from onecool_os.scenario.models import Scenario
from onecool_os.scenario.models import ScenarioSet
from onecool_os.scenario.validation import ScenarioError

__all__ = [
    "Scenario",
    "ScenarioBuilder",
    "ScenarioError",
    "ScenarioSet",
    "ScenarioSeverity",
    "ScenarioType",
    "TimeHorizon",
]
