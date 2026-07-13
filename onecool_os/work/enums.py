"""Enums for Onecool Work Contract bridge."""

from __future__ import annotations

from enum import StrEnum


class WorkStatus(StrEnum):
    """Execution status values from Onecool Work Contract v1.0."""

    CREATED = "CREATED"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_INPUT = "WAITING_INPUT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkErrorCategory(StrEnum):
    """Standard Work Contract error categories."""

    INVALID_REQUEST = "INVALID_REQUEST"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    NO_MATCH = "NO_MATCH"
    RATE_LIMIT = "RATE_LIMIT"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    UNSUPPORTED_PROVIDER = "UNSUPPORTED_PROVIDER"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class WorkPriority(StrEnum):
    """Execution priority labels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class WorkRequestType(StrEnum):
    """Supported Work request types for the MVP bridge."""

    COLLECTION_RESEARCH = "COLLECTION_RESEARCH"
    EVIDENCE_RESEARCH = "EVIDENCE_RESEARCH"
    BATCH_RESEARCH = "BATCH_RESEARCH"
    MORNING_BRIEF = "MORNING_BRIEF"
    HISTORY_SNAPSHOT_REVIEW = "HISTORY_SNAPSHOT_REVIEW"
    REPORT_GENERATION = "REPORT_GENERATION"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    NOTIFICATION = "NOTIFICATION"
