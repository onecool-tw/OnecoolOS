"""Analytics engine enumerations."""

from __future__ import annotations

from enum import StrEnum


class RiskLevel(StrEnum):
    """Supported analytics risk levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class MetricType(StrEnum):
    """Supported derived analytics metric families."""

    ROI = "ROI"
    IRR = "IRR"
    ALLOCATION = "ALLOCATION"
    PERFORMANCE = "PERFORMANCE"
    CASH_FLOW = "CASH_FLOW"
    RISK = "RISK"
    DRAWDOWN = "DRAWDOWN"
