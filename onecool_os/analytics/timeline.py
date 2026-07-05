"""Reusable Timeline Analytics foundation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from onecool_os.analytics.validation import AnalyticsError
from onecool_os.analytics.validation import require_text
from onecool_os.radar.models import RadarSnapshot


class TrendDirection(StrEnum):
    """Supported timeline trend directions."""

    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DETERIORATING = "DETERIORATING"
    UNKNOWN = "UNKNOWN"


class TrendStrength(StrEnum):
    """Supported timeline trend strength levels."""

    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    NONE = "NONE"


@dataclass(frozen=True)
class TimelineSnapshot:
    """Reusable summary of Radar snapshots across time."""

    snapshot_id: str
    asset_id: str
    generated_at: datetime
    reference_datetime: datetime
    previous_snapshots: tuple[RadarSnapshot, ...]
    current_snapshot: RadarSnapshot | None
    trend_direction: TrendDirection | str
    trend_strength: TrendStrength | str
    trend_summary: tuple[str, ...]
    signal_count: int
    new_signal_count: int
    resolved_signal_count: int
    escalated_signal_count: int
    changed_signal_count: int
    confidence_trend: TrendDirection | str
    liquidity_trend: TrendDirection | str
    agreement_trend: TrendDirection | str
    warnings: tuple[str, ...]
    radar_snapshot_ids: tuple[str, ...]

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
        if not isinstance(self.generated_at, datetime):
            raise AnalyticsError("generated_at must be a datetime.")
        if not isinstance(self.reference_datetime, datetime):
            raise AnalyticsError("reference_datetime must be a datetime.")
        if self.current_snapshot is not None and not isinstance(
            self.current_snapshot,
            RadarSnapshot,
        ):
            raise AnalyticsError("current_snapshot must be a RadarSnapshot.")
        object.__setattr__(
            self,
            "previous_snapshots",
            _snapshot_tuple(self.previous_snapshots, "previous_snapshots"),
        )
        object.__setattr__(
            self,
            "trend_direction",
            TrendDirection(str(self.trend_direction).upper()),
        )
        object.__setattr__(
            self,
            "trend_strength",
            TrendStrength(str(self.trend_strength).upper()),
        )
        object.__setattr__(
            self,
            "confidence_trend",
            TrendDirection(str(self.confidence_trend).upper()),
        )
        object.__setattr__(
            self,
            "liquidity_trend",
            TrendDirection(str(self.liquidity_trend).upper()),
        )
        object.__setattr__(
            self,
            "agreement_trend",
            TrendDirection(str(self.agreement_trend).upper()),
        )
        for field_name in (
            "signal_count",
            "new_signal_count",
            "resolved_signal_count",
            "escalated_signal_count",
            "changed_signal_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or value < 0:
                raise AnalyticsError(f"{field_name} must be a positive int.")
        object.__setattr__(
            self,
            "trend_summary",
            tuple(self.trend_summary or ()),
        )
        object.__setattr__(self, "warnings", tuple(self.warnings or ()))
        object.__setattr__(
            self,
            "radar_snapshot_ids",
            tuple(self.radar_snapshot_ids or ()),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe timeline payload."""

        return {
            "snapshot_id": self.snapshot_id,
            "asset_id": self.asset_id,
            "generated_at": self.generated_at.isoformat(),
            "reference_datetime": self.reference_datetime.isoformat(),
            "previous_snapshots": [
                snapshot.to_dict() for snapshot in self.previous_snapshots
            ],
            "current_snapshot": (
                self.current_snapshot.to_dict()
                if self.current_snapshot is not None
                else None
            ),
            "trend_direction": self.trend_direction.value,
            "trend_strength": self.trend_strength.value,
            "trend_summary": list(self.trend_summary),
            "signal_count": self.signal_count,
            "new_signal_count": self.new_signal_count,
            "resolved_signal_count": self.resolved_signal_count,
            "escalated_signal_count": self.escalated_signal_count,
            "changed_signal_count": self.changed_signal_count,
            "confidence_trend": self.confidence_trend.value,
            "liquidity_trend": self.liquidity_trend.value,
            "agreement_trend": self.agreement_trend.value,
            "warnings": list(self.warnings),
            "radar_snapshot_ids": list(self.radar_snapshot_ids),
        }


class TimelineAnalyticsBuilder:
    """Summarize historical Radar snapshots without mutation."""

    def build(
        self,
        radar_snapshots: tuple[RadarSnapshot, ...] | list[RadarSnapshot],
        *,
        reference_datetime: datetime,
        asset_id: str | None = None,
    ) -> TimelineSnapshot:
        """Build a deterministic timeline snapshot."""

        if not isinstance(reference_datetime, datetime):
            raise AnalyticsError("reference_datetime must be a datetime.")
        snapshots = _snapshot_tuple(radar_snapshots, "radar_snapshots")
        if not snapshots:
            resolved_asset_id = require_text(asset_id or "unknown", "asset_id")
            return _empty_timeline(resolved_asset_id, reference_datetime)

        current_snapshot = snapshots[-1]
        previous_snapshots = snapshots[:-1]
        resolved_asset_id = asset_id or current_snapshot.asset_id
        has_history = len(snapshots) >= 2
        signal_count = len(current_snapshot.current_signals)
        new_count = len(current_snapshot.new_signals)
        resolved_count = len(current_snapshot.resolved_signals)
        escalated_count = len(current_snapshot.escalated_signals)
        changed_count = len(current_snapshot.changed_signals)
        trend_direction = _trend_direction(
            has_history,
            resolved_count,
            escalated_count,
            new_count,
            changed_count,
        )
        trend_strength = _trend_strength(
            trend_direction,
            resolved_count,
            escalated_count,
            new_count,
            changed_count,
        )
        summaries = _trend_summary(current_snapshot, trend_direction)
        return TimelineSnapshot(
            snapshot_id=(
                f"timeline:{resolved_asset_id}:"
                f"{reference_datetime.isoformat()}"
            ),
            asset_id=resolved_asset_id,
            generated_at=reference_datetime,
            reference_datetime=reference_datetime,
            previous_snapshots=previous_snapshots,
            current_snapshot=current_snapshot,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            trend_summary=summaries,
            signal_count=signal_count,
            new_signal_count=new_count,
            resolved_signal_count=resolved_count,
            escalated_signal_count=escalated_count,
            changed_signal_count=changed_count,
            confidence_trend=_topic_trend(
                current_snapshot.change_summary,
                "Confidence",
            ),
            liquidity_trend=_topic_trend(
                current_snapshot.change_summary,
                "Liquidity",
            ),
            agreement_trend=_topic_trend(
                current_snapshot.change_summary,
                "Source Agreement",
            ),
            warnings=tuple(current_snapshot.warning_summary),
            radar_snapshot_ids=tuple(
                snapshot.snapshot_id for snapshot in snapshots
            ),
        )


def _empty_timeline(
    asset_id: str,
    reference_datetime: datetime,
) -> TimelineSnapshot:
    return TimelineSnapshot(
        snapshot_id=f"timeline:{asset_id}:{reference_datetime.isoformat()}",
        asset_id=asset_id,
        generated_at=reference_datetime,
        reference_datetime=reference_datetime,
        previous_snapshots=(),
        current_snapshot=None,
        trend_direction=TrendDirection.UNKNOWN,
        trend_strength=TrendStrength.NONE,
        trend_summary=("Insufficient Radar history",),
        signal_count=0,
        new_signal_count=0,
        resolved_signal_count=0,
        escalated_signal_count=0,
        changed_signal_count=0,
        confidence_trend=TrendDirection.UNKNOWN,
        liquidity_trend=TrendDirection.UNKNOWN,
        agreement_trend=TrendDirection.UNKNOWN,
        warnings=(),
        radar_snapshot_ids=(),
    )


def _snapshot_tuple(value: Any, field_name: str) -> tuple[RadarSnapshot, ...]:
    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise AnalyticsError(f"{field_name} must be a list or tuple.")
    snapshots = tuple(value)
    for snapshot in snapshots:
        if not isinstance(snapshot, RadarSnapshot):
            raise AnalyticsError(f"{field_name} must contain RadarSnapshot.")
    return snapshots


def _trend_direction(
    has_history: bool,
    resolved_count: int,
    escalated_count: int,
    new_count: int,
    changed_count: int,
) -> TrendDirection:
    if not has_history:
        return TrendDirection.UNKNOWN
    if resolved_count > escalated_count:
        return TrendDirection.IMPROVING
    if escalated_count > resolved_count:
        return TrendDirection.DETERIORATING
    if new_count == 0 and changed_count == 0 and resolved_count == 0:
        return TrendDirection.STABLE
    return TrendDirection.STABLE


def _trend_strength(
    direction: TrendDirection,
    resolved_count: int,
    escalated_count: int,
    new_count: int,
    changed_count: int,
) -> TrendStrength:
    if direction in (TrendDirection.UNKNOWN, TrendDirection.STABLE):
        if new_count == changed_count == resolved_count == escalated_count == 0:
            return TrendStrength.NONE
        return TrendStrength.WEAK
    magnitude = abs(resolved_count - escalated_count) + changed_count
    if magnitude >= 3:
        return TrendStrength.STRONG
    if magnitude == 2:
        return TrendStrength.MODERATE
    return TrendStrength.WEAK


def _trend_summary(
    current_snapshot: RadarSnapshot,
    direction: TrendDirection,
) -> tuple[str, ...]:
    summaries = list(current_snapshot.change_summary)
    if not summaries:
        if direction == TrendDirection.UNKNOWN:
            summaries.append("Insufficient Radar history")
        elif direction == TrendDirection.STABLE:
            summaries.append("Confidence Stable")
    if (
        len(current_snapshot.new_signals) + len(current_snapshot.escalated_signals)
        > len(current_snapshot.resolved_signals)
    ):
        summaries.append("Review Queue Growing")
    return tuple(dict.fromkeys(summaries))


def _topic_trend(
    summaries: tuple[str, ...],
    topic: str,
) -> TrendDirection:
    matching = tuple(
        summary for summary in summaries
        if summary.startswith(topic)
    )
    if not matching:
        return TrendDirection.STABLE
    latest = matching[-1].lower()
    if "improved" in latest or "improving" in latest:
        return TrendDirection.IMPROVING
    if (
        "deteriorated" in latest
        or "deteriorating" in latest
        or "declined" in latest
    ):
        return TrendDirection.DETERIORATING
    return TrendDirection.STABLE
