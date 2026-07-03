"""Scenario Engine enumerations."""

from __future__ import annotations

from enum import StrEnum


class ScenarioType(StrEnum):
    """Supported scenario categories."""

    BASE = "BASE"
    UPSIDE = "UPSIDE"
    DOWNSIDE = "DOWNSIDE"
    STRESS = "STRESS"
    BLACK_SWAN = "BLACK_SWAN"


class ScenarioSeverity(StrEnum):
    """Supported scenario severity levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class TimeHorizon(StrEnum):
    """Supported scenario time horizons."""

    SHORT_TERM = "SHORT_TERM"
    MEDIUM_TERM = "MEDIUM_TERM"
    LONG_TERM = "LONG_TERM"
