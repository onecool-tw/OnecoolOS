"""Decision Engine enumerations."""

from __future__ import annotations

from enum import StrEnum


class DecisionType(StrEnum):
    """Supported decision option types."""

    REVIEW = "REVIEW"
    HOLD = "HOLD"
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    REBALANCE = "REBALANCE"
    INVESTIGATE = "INVESTIGATE"


class DecisionReadiness(StrEnum):
    """Supported decision readiness states."""

    READY = "READY"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    BLOCKED = "BLOCKED"


class DecisionConfidence(StrEnum):
    """Supported decision confidence levels."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DecisionSeverity(StrEnum):
    """Supported decision constraint severities."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConstraintType(StrEnum):
    """Supported decision constraint types."""

    DATA_MISSING = "DATA_MISSING"
    CASH_INSUFFICIENT = "CASH_INSUFFICIENT"
    RISK_TOO_HIGH = "RISK_TOO_HIGH"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
