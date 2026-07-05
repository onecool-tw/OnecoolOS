"""Radar Engine models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from onecool_os.radar.enums import SignalSeverity
from onecool_os.radar.enums import SignalType
from onecool_os.radar.validation import parse_datetime
from onecool_os.radar.validation import parse_enum
from onecool_os.radar.validation import parse_optional_dict
from onecool_os.radar.validation import parse_signal_tuple
from onecool_os.radar.validation import require_text


@dataclass(frozen=True)
class RadarSignal:
    """A deterministic radar signal."""

    signal_id: str
    signal_type: SignalType | str
    severity: SignalSeverity | str
    title: str
    description: str
    created_at: datetime | str
    payload: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "signal_id",
            require_text(self.signal_id, "signal_id"),
        )
        object.__setattr__(
            self,
            "signal_type",
            parse_enum(SignalType, self.signal_type, "signal_type"),
        )
        object.__setattr__(
            self,
            "severity",
            parse_enum(SignalSeverity, self.severity, "severity"),
        )
        object.__setattr__(self, "title", require_text(self.title, "title"))
        object.__setattr__(
            self,
            "description",
            require_text(self.description, "description"),
        )
        object.__setattr__(
            self,
            "created_at",
            parse_datetime(self.created_at, "created_at"),
        )
        object.__setattr__(
            self,
            "payload",
            parse_optional_dict(self.payload, "payload"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "payload": self.payload,
        }


@dataclass(frozen=True)
class RadarSnapshot:
    """A deterministic comparison between previous and current signals."""

    snapshot_id: str
    asset_id: str
    generated_at: datetime | str
    reference_datetime: datetime | str
    current_signals: tuple[RadarSignal, ...] | list[RadarSignal] | None = None
    previous_signals: tuple[RadarSignal, ...] | list[RadarSignal] | None = None
    new_signals: tuple[RadarSignal, ...] | list[RadarSignal] | None = None
    resolved_signals: (
        tuple[RadarSignal, ...] | list[RadarSignal] | None
    ) = None
    changed_signals: tuple[RadarSignal, ...] | list[RadarSignal] | None = None
    escalated_signals: (
        tuple[RadarSignal, ...] | list[RadarSignal] | None
    ) = None
    change_summary: tuple[str, ...] | list[str] | None = None
    warning_summary: tuple[str, ...] | list[str] | None = None
    source_snapshot_ids: tuple[str, ...] | list[str] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            require_text(self.snapshot_id, "snapshot_id"),
        )
        object.__setattr__(
            self,
            "asset_id",
            require_text(self.asset_id, "asset_id"),
        )
        object.__setattr__(
            self,
            "generated_at",
            parse_datetime(self.generated_at, "generated_at"),
        )
        object.__setattr__(
            self,
            "reference_datetime",
            parse_datetime(self.reference_datetime, "reference_datetime"),
        )
        for field_name in (
            "current_signals",
            "previous_signals",
            "new_signals",
            "resolved_signals",
            "changed_signals",
            "escalated_signals",
        ):
            object.__setattr__(
                self,
                field_name,
                parse_signal_tuple(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "change_summary",
            tuple(self.change_summary or ()),
        )
        object.__setattr__(
            self,
            "warning_summary",
            tuple(self.warning_summary or ()),
        )
        object.__setattr__(
            self,
            "source_snapshot_ids",
            tuple(self.source_snapshot_ids or ()),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "snapshot_id": self.snapshot_id,
            "asset_id": self.asset_id,
            "generated_at": self.generated_at.isoformat(),
            "reference_datetime": self.reference_datetime.isoformat(),
            "current_signals": _signals_to_dict(self.current_signals),
            "previous_signals": _signals_to_dict(self.previous_signals),
            "new_signals": _signals_to_dict(self.new_signals),
            "resolved_signals": _signals_to_dict(self.resolved_signals),
            "changed_signals": _signals_to_dict(self.changed_signals),
            "escalated_signals": _signals_to_dict(self.escalated_signals),
            "change_summary": list(self.change_summary),
            "warning_summary": list(self.warning_summary),
            "source_snapshot_ids": list(self.source_snapshot_ids),
        }


def _signals_to_dict(signals: tuple[RadarSignal, ...]) -> list[dict[str, Any]]:
    return [signal.to_dict() for signal in signals]
