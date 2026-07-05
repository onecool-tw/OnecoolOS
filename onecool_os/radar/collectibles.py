"""Collectible Radar builder."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from onecool_os.business_logic.results import BusinessLogicResult
from onecool_os.radar.builder import BaseRadarBuilder
from onecool_os.radar.enums import SignalSeverity
from onecool_os.radar.enums import SignalType
from onecool_os.radar.models import RadarSignal
from onecool_os.radar.models import RadarSnapshot
from onecool_os.radar.validation import RadarError


QUALITY_ORDER = {
    "UNKNOWN": 0,
    "WEAK": 1,
    "NORMAL": 2,
    "STRONG": 3,
    "PREMIUM": 4,
}
REVIEW_ORDER = {
    "READY_FOR_REVIEW": 0,
    "NEEDS_REVIEW": 1,
    "BLOCKED": 2,
}


class CollectibleRadarBuilder(BaseRadarBuilder):
    """Detect deterministic changes in collectible intelligence output."""

    builder_name = "collectible_radar"

    def build(
        self,
        previous_intelligence: BusinessLogicResult | dict[str, Any] | None,
        current_intelligence: BusinessLogicResult | dict[str, Any],
        *,
        reference_datetime: datetime,
    ) -> RadarSnapshot:
        """Build a Collectible Radar snapshot without mutating inputs."""

        if not isinstance(reference_datetime, datetime):
            raise RadarError("reference_datetime must be a datetime.")
        previous_payload = _payload(previous_intelligence)
        current_payload = _payload(current_intelligence)
        asset_id = _asset_id(current_payload, previous_payload)
        previous_signals = _state_signals(
            previous_payload,
            reference_datetime,
            prefix="previous",
        )
        current_signals = _state_signals(
            current_payload,
            reference_datetime,
            prefix="current",
        )
        changed_signals = _changed_signals(
            previous_payload,
            current_payload,
            reference_datetime,
        )
        escalated_signals = tuple(
            signal
            for signal in changed_signals
            if signal.payload.get("direction") == "deteriorated"
        )
        new_signals = _new_signals(
            previous_signals,
            current_signals,
            changed_signals,
        )
        resolved_signals = _resolved_signals(
            previous_signals,
            current_signals,
            changed_signals,
        )
        change_summary = tuple(
            signal.title
            for signal in (
                new_signals
                + resolved_signals
                + changed_signals
                + escalated_signals
            )
        )
        warning_summary = tuple(
            dict.fromkeys(current_payload.get("warnings") or ())
        )
        return RadarSnapshot(
            snapshot_id=f"radar:{asset_id}:{reference_datetime.isoformat()}",
            asset_id=asset_id,
            generated_at=reference_datetime,
            reference_datetime=reference_datetime,
            current_signals=current_signals,
            previous_signals=previous_signals,
            new_signals=new_signals,
            resolved_signals=resolved_signals,
            changed_signals=changed_signals,
            escalated_signals=escalated_signals,
            change_summary=change_summary,
            warning_summary=warning_summary,
            source_snapshot_ids=_source_ids(
                previous_intelligence,
                current_intelligence,
            ),
        )


def _payload(
    intelligence: BusinessLogicResult | dict[str, Any] | None,
) -> dict[str, Any]:
    if intelligence is None:
        return {}
    if isinstance(intelligence, BusinessLogicResult):
        return dict(intelligence.payload or {})
    if isinstance(intelligence, dict):
        if isinstance(intelligence.get("payload"), dict):
            return dict(intelligence["payload"])
        return dict(intelligence)
    raise RadarError("Collectible intelligence must be a result or dict.")


def _asset_id(current: dict[str, Any], previous: dict[str, Any]) -> str:
    for payload in (current, previous):
        market_intelligence = payload.get("market_intelligence")
        if isinstance(market_intelligence, dict):
            asset_id = market_intelligence.get("asset_id")
            if asset_id:
                return str(asset_id)
    return "unknown"


def _state_signals(
    payload: dict[str, Any],
    created_at: datetime,
    *,
    prefix: str,
) -> tuple[RadarSignal, ...]:
    signals: list[RadarSignal] = []
    for warning in payload.get("warnings") or ():
        signals.append(
            RadarSignal(
                signal_id=f"{prefix}:warning:{_slug(warning)}",
                signal_type=_signal_type_for_warning(str(warning)),
                severity=_severity_for_warning(str(warning)),
                title=str(warning),
                description=f"Collectible intelligence warning: {warning}",
                created_at=created_at,
                payload={"warning": warning},
            )
        )
    review_status = payload.get("review_status")
    if review_status and review_status != "READY_FOR_REVIEW":
        signals.append(
            RadarSignal(
                signal_id=f"{prefix}:review:{review_status}",
                signal_type=SignalType.REVIEW_REQUIRED,
                severity=(
                    SignalSeverity.HIGH
                    if review_status == "BLOCKED"
                    else SignalSeverity.MEDIUM
                ),
                title="Review Required",
                description=f"Review status is {review_status}.",
                created_at=created_at,
                payload={"review_status": review_status},
            )
        )
    return tuple(signals)


def _changed_signals(
    previous: dict[str, Any],
    current: dict[str, Any],
    created_at: datetime,
) -> tuple[RadarSignal, ...]:
    changes: list[RadarSignal] = []
    quality_fields = (
        ("market_quality", "Market Quality", SignalType.MARKET_QUALITY_CHANGED),
        ("source_quality", "Source Agreement", SignalType.MARKET_QUALITY_CHANGED),
        ("liquidity_quality", "Liquidity", SignalType.LIQUIDITY_CHANGED),
        ("valuation_quality", "Confidence", SignalType.LOW_CONFIDENCE),
    )
    for field_name, label, signal_type in quality_fields:
        previous_value = previous.get(field_name)
        current_value = current.get(field_name)
        if not previous_value or not current_value or previous_value == current_value:
            continue
        previous_score = QUALITY_ORDER.get(str(previous_value), 0)
        current_score = QUALITY_ORDER.get(str(current_value), 0)
        direction = (
            "improved" if current_score > previous_score else "deteriorated"
        )
        title = _trend_title(label, direction)
        changes.append(
            RadarSignal(
                signal_id=f"changed:{field_name}:{previous_value}:{current_value}",
                signal_type=signal_type,
                severity=(
                    SignalSeverity.INFO
                    if direction == "improved"
                    else SignalSeverity.HIGH
                ),
                title=title,
                description=(
                    f"{label} changed from {previous_value} to "
                    f"{current_value}."
                ),
                created_at=created_at,
                payload={
                    "field": field_name,
                    "previous": previous_value,
                    "current": current_value,
                    "direction": direction,
                },
            )
        )
    changes.extend(_review_status_changes(previous, current, created_at))
    return tuple(changes)


def _review_status_changes(
    previous: dict[str, Any],
    current: dict[str, Any],
    created_at: datetime,
) -> tuple[RadarSignal, ...]:
    previous_status = previous.get("review_status")
    current_status = current.get("review_status")
    if (
        not previous_status
        or not current_status
        or previous_status == current_status
    ):
        return ()
    previous_score = REVIEW_ORDER.get(str(previous_status), 0)
    current_score = REVIEW_ORDER.get(str(current_status), 0)
    direction = "improved" if current_score < previous_score else "deteriorated"
    return (
        RadarSignal(
            signal_id=f"changed:review_status:{previous_status}:{current_status}",
            signal_type=SignalType.REVIEW_REQUIRED,
            severity=(
                SignalSeverity.INFO
                if direction == "improved"
                else SignalSeverity.HIGH
            ),
            title=_trend_title("Review Status", direction),
            description=(
                f"Review status changed from {previous_status} to "
                f"{current_status}."
            ),
            created_at=created_at,
            payload={
                "field": "review_status",
                "previous": previous_status,
                "current": current_status,
                "direction": direction,
            },
        ),
    )


def _new_signals(
    previous_signals: tuple[RadarSignal, ...],
    current_signals: tuple[RadarSignal, ...],
    changed_signals: tuple[RadarSignal, ...],
) -> tuple[RadarSignal, ...]:
    previous_titles = {signal.title for signal in previous_signals}
    new_state_signals = tuple(
        signal for signal in current_signals
        if signal.title not in previous_titles
    )
    improvements = tuple(
        signal for signal in changed_signals
        if signal.payload.get("direction") == "improved"
    )
    return new_state_signals + improvements


def _resolved_signals(
    previous_signals: tuple[RadarSignal, ...],
    current_signals: tuple[RadarSignal, ...],
    changed_signals: tuple[RadarSignal, ...],
) -> tuple[RadarSignal, ...]:
    current_titles = {signal.title for signal in current_signals}
    resolved = [
        RadarSignal(
            signal_id=f"resolved:{signal.signal_id}",
            signal_type=signal.signal_type,
            severity=SignalSeverity.INFO,
            title=f"{signal.title} Resolved",
            description=f"Previous signal resolved: {signal.title}.",
            created_at=signal.created_at,
            payload={"resolved_signal_id": signal.signal_id},
        )
        for signal in previous_signals
        if signal.title not in current_titles
    ]
    for signal in changed_signals:
        if (
            signal.payload.get("field") == "valuation_quality"
            and signal.payload.get("direction") == "improved"
        ):
            resolved.append(
                RadarSignal(
                    signal_id=f"resolved:{signal.signal_id}",
                    signal_type=SignalType.LOW_CONFIDENCE,
                    severity=SignalSeverity.INFO,
                    title="Low Confidence Resolved",
                    description="Confidence improved from a weaker state.",
                    created_at=signal.created_at,
                    payload=signal.payload,
                )
            )
    return tuple(resolved)


def _source_ids(
    previous: BusinessLogicResult | dict[str, Any] | None,
    current: BusinessLogicResult | dict[str, Any],
) -> tuple[str, ...]:
    ids: list[str] = []
    for source in (previous, current):
        if isinstance(source, BusinessLogicResult):
            ids.append(source.result_id)
        elif isinstance(source, dict):
            source_id = source.get("result_id") or source.get("snapshot_id")
            if source_id:
                ids.append(str(source_id))
    return tuple(ids)


def _signal_type_for_warning(warning: str) -> SignalType:
    normalized = warning.lower()
    if "conflict" in normalized:
        return SignalType.SOURCE_CONFLICT
    if "confidence" in normalized:
        return SignalType.LOW_CONFIDENCE
    if "stale" in normalized:
        return SignalType.STALE_DATA
    if "liquidity" in normalized:
        return SignalType.LIQUIDITY_CHANGED
    if "coverage" in normalized or "source" in normalized:
        return SignalType.COVERAGE_CHANGED
    return SignalType.REVIEW_REQUIRED


def _severity_for_warning(warning: str) -> SignalSeverity:
    normalized = warning.lower()
    if "conflict" in normalized or "blocked" in normalized:
        return SignalSeverity.HIGH
    if "low" in normalized or "stale" in normalized:
        return SignalSeverity.MEDIUM
    return SignalSeverity.LOW


def _trend_title(label: str, direction: str) -> str:
    if label == "Liquidity" and direction == "deteriorated":
        return "Liquidity Deteriorated"
    if label == "Confidence" and direction == "deteriorated":
        return "Confidence Declined"
    if label == "Confidence" and direction == "improved":
        return "Confidence Improved"
    if label == "Source Agreement" and direction == "improved":
        return "Source Agreement Improved"
    if label == "Source Agreement" and direction == "deteriorated":
        return "Source Agreement Deteriorated"
    if direction == "improved":
        return f"{label} Improved"
    return f"{label} Deteriorated"


def _slug(value: str) -> str:
    return value.strip().lower().replace(" ", "-").replace("_", "-")
