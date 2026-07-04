"""OFAI foundation enumerations."""

from __future__ import annotations

from enum import StrEnum


class PlanningMode(StrEnum):
    """Supported OFAI planning modes."""

    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    EVENT = "EVENT"


class ConfidenceLevel(StrEnum):
    """Supported OFAI plan confidence levels."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
