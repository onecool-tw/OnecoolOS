"""Business logic metric and signal result models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from onecool_os.business_logic.enums import ConfidenceLevel
from onecool_os.business_logic.enums import MetricType
from onecool_os.business_logic.enums import SignalSeverity
from onecool_os.business_logic.validation import optional_currency
from onecool_os.business_logic.validation import optional_text
from onecool_os.business_logic.validation import parse_enum
from onecool_os.business_logic.validation import parse_optional_datetime
from onecool_os.business_logic.validation import parse_optional_decimal
from onecool_os.business_logic.validation import parse_optional_dict
from onecool_os.business_logic.validation import parse_optional_enum
from onecool_os.business_logic.validation import parse_tags
from onecool_os.business_logic.validation import require_text


@dataclass(frozen=True)
class BusinessLogicResult:
    """Structured deterministic metric result."""

    result_id: str
    engine_name: str
    engine_version: str
    metric_type: MetricType | str
    value: Decimal | str | int | float | None = None
    currency: str | None = None
    payload: dict[str, Any] | None = None
    confidence: ConfidenceLevel | str | None = None
    generated_at: datetime | str | None = None
    note: str | None = None
    tags: list[str] | tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "result_id",
            require_text(self.result_id, "result_id"),
        )
        _normalize_engine_fields(self)
        object.__setattr__(
            self,
            "metric_type",
            parse_enum(MetricType, self.metric_type, "metric_type"),
        )
        object.__setattr__(
            self,
            "value",
            parse_optional_decimal(self.value, "value"),
        )
        object.__setattr__(self, "currency", optional_currency(self.currency))
        object.__setattr__(
            self,
            "payload",
            parse_optional_dict(self.payload, "payload"),
        )
        object.__setattr__(
            self,
            "confidence",
            parse_optional_enum(
                ConfidenceLevel,
                self.confidence,
                "confidence",
            ),
        )
        object.__setattr__(
            self,
            "generated_at",
            parse_optional_datetime(self.generated_at, "generated_at"),
        )
        object.__setattr__(self, "note", optional_text(self.note, "note"))
        object.__setattr__(self, "tags", parse_tags(self.tags))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe metric payload."""

        return {
            "result_id": self.result_id,
            "engine_name": self.engine_name,
            "engine_version": self.engine_version,
            "metric_type": self.metric_type.value,
            "value": _format_optional_decimal(self.value),
            "currency": self.currency,
            "payload": self.payload,
            "confidence": (
                self.confidence.value if self.confidence is not None else None
            ),
            "generated_at": _format_optional_datetime(self.generated_at),
            "note": self.note,
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class SignalResult:
    """Structured rule-based signal result."""

    signal_id: str
    engine_name: str
    engine_version: str
    signal_type: str
    severity: SignalSeverity | str
    message: str
    payload: dict[str, Any] | None = None
    generated_at: datetime | str | None = None
    note: str | None = None
    tags: list[str] | tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "signal_id",
            require_text(self.signal_id, "signal_id"),
        )
        _normalize_engine_fields(self)
        object.__setattr__(
            self,
            "signal_type",
            require_text(self.signal_type, "signal_type"),
        )
        object.__setattr__(
            self,
            "severity",
            parse_enum(SignalSeverity, self.severity, "severity"),
        )
        object.__setattr__(
            self,
            "message",
            require_text(self.message, "message"),
        )
        object.__setattr__(
            self,
            "payload",
            parse_optional_dict(self.payload, "payload"),
        )
        object.__setattr__(
            self,
            "generated_at",
            parse_optional_datetime(self.generated_at, "generated_at"),
        )
        object.__setattr__(self, "note", optional_text(self.note, "note"))
        object.__setattr__(self, "tags", parse_tags(self.tags))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe signal payload."""

        return {
            "signal_id": self.signal_id,
            "engine_name": self.engine_name,
            "engine_version": self.engine_version,
            "signal_type": self.signal_type,
            "severity": self.severity.value,
            "message": self.message,
            "payload": self.payload,
            "generated_at": _format_optional_datetime(self.generated_at),
            "note": self.note,
            "tags": list(self.tags),
        }


def _normalize_engine_fields(instance: Any) -> None:
    object.__setattr__(
        instance,
        "engine_name",
        require_text(instance.engine_name, "engine_name"),
    )
    object.__setattr__(
        instance,
        "engine_version",
        require_text(instance.engine_version, "engine_version"),
    )


def _format_optional_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}"


def _format_optional_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
