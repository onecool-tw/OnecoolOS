"""Models for Onecool Work Contract v1.0."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from onecool_os.work.enums import WorkErrorCategory
from onecool_os.work.enums import WorkPriority
from onecool_os.work.enums import WorkRequestType
from onecool_os.work.enums import WorkStatus
from onecool_os.work.validation import parse_datetime
from onecool_os.work.validation import parse_dict
from onecool_os.work.validation import parse_enum
from onecool_os.work.validation import parse_list
from onecool_os.work.validation import parse_optional_datetime
from onecool_os.work.validation import optional_text
from onecool_os.work.validation import require_text

WORK_CONTRACT_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class WorkContractErrorRecord:
    """One structured Work Contract error."""

    category: WorkErrorCategory | str
    message: str
    field: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "category",
            parse_enum(WorkErrorCategory, self.category, "category"),
        )
        object.__setattr__(self, "message", require_text(self.message, "message"))
        object.__setattr__(self, "field", optional_text(self.field, "field"))

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe data."""

        return {
            "category": self.category.value,
            "message": self.message,
            "field": self.field,
        }


@dataclass(frozen=True)
class WorkExecutionTime:
    """Optional execution timing details."""

    started_at: datetime | str | None = None
    duration_seconds: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "started_at",
            parse_optional_datetime(self.started_at, "started_at"),
        )
        if self.duration_seconds is not None and int(self.duration_seconds) < 0:
            raise ValueError("duration_seconds must be non-negative.")
        object.__setattr__(
            self,
            "duration_seconds",
            None if self.duration_seconds is None else int(self.duration_seconds),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe data."""

        return {
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "duration_seconds": self.duration_seconds,
        }


@dataclass(frozen=True)
class WorkRequest:
    """Provider-neutral Work request envelope."""

    schema_version: str
    request_id: str
    request_type: WorkRequestType | str
    reference_datetime: datetime | str
    priority: WorkPriority | str
    requested_action: str
    context: dict[str, Any]
    constraints: dict[str, Any]
    asset_id: str | None = None
    portfolio_id: str | None = None
    source_urls: tuple[str, ...] | list[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", require_text(self.schema_version, "schema_version"))
        object.__setattr__(self, "request_id", require_text(self.request_id, "request_id"))
        object.__setattr__(
            self,
            "request_type",
            parse_enum(WorkRequestType, self.request_type, "request_type"),
        )
        object.__setattr__(
            self,
            "reference_datetime",
            parse_datetime(self.reference_datetime, "reference_datetime"),
        )
        object.__setattr__(self, "priority", parse_enum(WorkPriority, self.priority, "priority"))
        object.__setattr__(self, "requested_action", require_text(self.requested_action, "requested_action"))
        object.__setattr__(self, "context", parse_dict(self.context, "context"))
        object.__setattr__(self, "constraints", parse_dict(self.constraints, "constraints"))
        object.__setattr__(self, "asset_id", optional_text(self.asset_id, "asset_id"))
        object.__setattr__(self, "portfolio_id", optional_text(self.portfolio_id, "portfolio_id"))
        object.__setattr__(
            self,
            "source_urls",
            tuple(require_text(item, "source_urls") for item in parse_list(self.source_urls, "source_urls")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe request data."""

        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "request_type": self.request_type.value,
            "asset_id": self.asset_id,
            "portfolio_id": self.portfolio_id,
            "reference_datetime": self.reference_datetime.isoformat(),
            "priority": self.priority.value,
            "requested_action": self.requested_action,
            "context": dict(self.context),
            "source_urls": list(self.source_urls),
            "constraints": dict(self.constraints),
        }


@dataclass(frozen=True)
class WorkResponse:
    """Provider-neutral Work response envelope."""

    schema_version: str
    request_id: str
    status: WorkStatus | str
    provider: str
    outputs: dict[str, Any]
    warnings: tuple[str, ...] | list[str]
    errors: tuple[WorkContractErrorRecord | dict[str, Any], ...] | list[WorkContractErrorRecord | dict[str, Any]]
    completed_at: datetime | str | None = None
    execution_time: WorkExecutionTime | dict[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", require_text(self.schema_version, "schema_version"))
        object.__setattr__(self, "request_id", require_text(self.request_id, "request_id"))
        object.__setattr__(self, "status", parse_enum(WorkStatus, self.status, "status"))
        object.__setattr__(self, "provider", require_text(self.provider, "provider"))
        object.__setattr__(
            self,
            "completed_at",
            parse_optional_datetime(self.completed_at, "completed_at"),
        )
        object.__setattr__(self, "outputs", parse_dict(self.outputs, "outputs"))
        object.__setattr__(
            self,
            "warnings",
            tuple(require_text(item, "warnings") for item in parse_list(self.warnings, "warnings")),
        )
        object.__setattr__(
            self,
            "errors",
            tuple(_error_record(item) for item in parse_list(self.errors, "errors")),
        )
        object.__setattr__(self, "execution_time", _execution_time(self.execution_time))

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe response data."""

        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "status": self.status.value,
            "provider": self.provider,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time": self.execution_time.to_dict() if self.execution_time else None,
            "outputs": dict(self.outputs),
            "warnings": list(self.warnings),
            "errors": [item.to_dict() for item in self.errors],
        }


def _error_record(item: WorkContractErrorRecord | dict[str, Any]) -> WorkContractErrorRecord:
    if isinstance(item, WorkContractErrorRecord):
        return item
    if isinstance(item, dict):
        return WorkContractErrorRecord(**item)
    raise TypeError("errors must contain dictionaries or WorkContractErrorRecord items.")


def _execution_time(value: WorkExecutionTime | dict[str, Any] | None) -> WorkExecutionTime | None:
    if value is None:
        return None
    if isinstance(value, WorkExecutionTime):
        return value
    if isinstance(value, dict):
        return WorkExecutionTime(**value)
    raise TypeError("execution_time must be a dictionary or WorkExecutionTime.")
