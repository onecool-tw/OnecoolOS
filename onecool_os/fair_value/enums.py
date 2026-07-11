"""Enums for the Onecool Fair Value engine."""

from __future__ import annotations

from enum import Enum


class FairValueConfidence(str, Enum):
    """Confidence level for a fair value snapshot."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class FairValueLiquidity(str, Enum):
    """Observed comparable-sale liquidity."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    ILLIQUID = "ILLIQUID"


class FairValueFreshness(str, Enum):
    """Freshness of the latest included comparable."""

    CURRENT = "CURRENT"
    AGING = "AGING"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
