"""Investment performance enumerations."""

from __future__ import annotations

from enum import StrEnum


class PerformanceStatus(StrEnum):
    """Supported investment performance states."""

    UNKNOWN = "UNKNOWN"
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    BREAKEVEN = "BREAKEVEN"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

