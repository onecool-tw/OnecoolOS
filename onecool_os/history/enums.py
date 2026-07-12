"""Portfolio history enumerations."""

from __future__ import annotations

from enum import StrEnum


class HistorySnapshotType(StrEnum):
    """Supported portfolio history snapshot types."""

    PORTFOLIO_DAILY = "PORTFOLIO_DAILY"
    PORTFOLIO_MANUAL = "PORTFOLIO_MANUAL"
    RELEASE_BASELINE = "RELEASE_BASELINE"
    IMPORT_BASELINE = "IMPORT_BASELINE"


class HistoryRecordStatus(StrEnum):
    """Portfolio history snapshot completeness status."""

    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INVALID = "INVALID"


class HistoryWriteStatus(StrEnum):
    """Append-only history write outcome."""

    CREATED = "CREATED"
    DUPLICATE = "DUPLICATE"
    REPLACED = "REPLACED"
    REJECTED = "REJECTED"


class ChangeDirection(StrEnum):
    """Future trend direction marker."""

    UP = "UP"
    DOWN = "DOWN"
    UNCHANGED = "UNCHANGED"
    UNKNOWN = "UNKNOWN"
