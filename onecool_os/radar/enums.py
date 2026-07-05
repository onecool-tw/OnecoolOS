"""Radar Engine enumerations."""

from __future__ import annotations

from enum import StrEnum


class SignalSeverity(StrEnum):
    """Radar signal severity."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SignalChange(StrEnum):
    """Radar change categories."""

    NEW = "NEW"
    CHANGED = "CHANGED"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class SignalType(StrEnum):
    """Radar signal types."""

    MARKET_QUALITY_CHANGED = "MARKET_QUALITY_CHANGED"
    LIQUIDITY_CHANGED = "LIQUIDITY_CHANGED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    STALE_DATA = "STALE_DATA"
    COVERAGE_CHANGED = "COVERAGE_CHANGED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
