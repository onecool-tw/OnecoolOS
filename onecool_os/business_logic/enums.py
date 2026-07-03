"""Business Logic Engine enumerations."""

from __future__ import annotations

from enum import StrEnum


class MetricType(StrEnum):
    """Supported deterministic metric categories."""

    ROI = "ROI"
    IRR = "IRR"
    ALLOCATION = "ALLOCATION"
    PERFORMANCE = "PERFORMANCE"
    CASH_FLOW = "CASH_FLOW"
    RISK = "RISK"
    EXPOSURE = "EXPOSURE"
    CONCENTRATION = "CONCENTRATION"
    LIQUIDITY = "LIQUIDITY"
    REBALANCING = "REBALANCING"
    TAX = "TAX"


class SignalSeverity(StrEnum):
    """Supported rule-based signal severity levels."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConfidenceLevel(StrEnum):
    """Supported result confidence levels."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
