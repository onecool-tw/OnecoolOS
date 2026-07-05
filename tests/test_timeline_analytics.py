from copy import deepcopy
from datetime import datetime
from datetime import timezone

from onecool_os.analytics import TimelineAnalyticsBuilder
from onecool_os.analytics import TimelineSnapshot
from onecool_os.analytics import TrendDirection
from onecool_os.analytics import TrendStrength
from onecool_os.radar import RadarSnapshot
from onecool_os.radar import RadarSignal


REFERENCE = datetime(2026, 7, 5, tzinfo=timezone.utc)


def test_improving_trend() -> None:
    timeline = TimelineAnalyticsBuilder().build(
        (
            radar_snapshot("previous"),
            radar_snapshot("current", resolved=2, escalated=0),
        ),
        reference_datetime=REFERENCE,
    )

    assert timeline.trend_direction == TrendDirection.IMPROVING
    assert timeline.trend_strength == TrendStrength.MODERATE


def test_stable_trend() -> None:
    timeline = TimelineAnalyticsBuilder().build(
        (
            radar_snapshot("previous"),
            radar_snapshot("current"),
        ),
        reference_datetime=REFERENCE,
    )

    assert timeline.trend_direction == TrendDirection.STABLE
    assert timeline.trend_strength == TrendStrength.NONE
    assert timeline.trend_summary == ("Confidence Stable",)


def test_deteriorating_trend() -> None:
    timeline = TimelineAnalyticsBuilder().build(
        (
            radar_snapshot("previous"),
            radar_snapshot("current", escalated=2, resolved=0),
        ),
        reference_datetime=REFERENCE,
    )

    assert timeline.trend_direction == TrendDirection.DETERIORATING
    assert timeline.trend_strength == TrendStrength.MODERATE


def test_unknown_trend() -> None:
    timeline = TimelineAnalyticsBuilder().build(
        (radar_snapshot("current"),),
        reference_datetime=REFERENCE,
    )

    assert timeline.trend_direction == TrendDirection.UNKNOWN
    assert timeline.trend_strength == TrendStrength.NONE


def test_statistics() -> None:
    timeline = TimelineAnalyticsBuilder().build(
        (
            radar_snapshot("previous"),
            radar_snapshot(
                "current",
                current=3,
                new=2,
                resolved=1,
                escalated=1,
                changed=2,
            ),
        ),
        reference_datetime=REFERENCE,
    )

    assert timeline.signal_count == 3
    assert timeline.new_signal_count == 2
    assert timeline.resolved_signal_count == 1
    assert timeline.escalated_signal_count == 1
    assert timeline.changed_signal_count == 2


def test_trend_summary() -> None:
    timeline = TimelineAnalyticsBuilder().build(
        (
            radar_snapshot("previous"),
            radar_snapshot(
                "current",
                new=2,
                escalated=1,
                summaries=("Market Quality Improving",),
            ),
        ),
        reference_datetime=REFERENCE,
    )

    assert "Market Quality Improving" in timeline.trend_summary
    assert "Review Queue Growing" in timeline.trend_summary


def test_replay_support() -> None:
    snapshots = (
        radar_snapshot("previous"),
        radar_snapshot("current", resolved=1),
    )
    builder = TimelineAnalyticsBuilder()

    first = builder.build(snapshots, reference_datetime=REFERENCE)
    second = builder.build(snapshots, reference_datetime=REFERENCE)

    assert first.to_dict() == second.to_dict()


def test_injected_reference_datetime() -> None:
    reference = datetime(2026, 8, 1, tzinfo=timezone.utc)

    timeline = TimelineAnalyticsBuilder().build(
        (
            radar_snapshot("previous"),
            radar_snapshot("current"),
        ),
        reference_datetime=reference,
    )

    assert timeline.generated_at == reference
    assert timeline.reference_datetime == reference


def test_deterministic_output() -> None:
    snapshots = (
        radar_snapshot("previous"),
        radar_snapshot("current", escalated=1),
    )

    first = TimelineAnalyticsBuilder().build(
        snapshots,
        reference_datetime=REFERENCE,
    )
    second = TimelineAnalyticsBuilder().build(
        snapshots,
        reference_datetime=REFERENCE,
    )

    assert first.snapshot_id == second.snapshot_id
    assert first.to_dict() == second.to_dict()


def test_no_mutation() -> None:
    snapshots = (
        radar_snapshot("previous"),
        radar_snapshot("current", warnings=("Low Confidence",)),
    )
    before = deepcopy([snapshot.to_dict() for snapshot in snapshots])

    TimelineAnalyticsBuilder().build(snapshots, reference_datetime=REFERENCE)

    assert [snapshot.to_dict() for snapshot in snapshots] == before


def test_topic_trends_and_warnings() -> None:
    timeline = TimelineAnalyticsBuilder().build(
        (
            radar_snapshot("previous"),
            radar_snapshot(
                "current",
                summaries=(
                    "Confidence Declined",
                    "Liquidity Deteriorating",
                    "Source Agreement Improved",
                ),
                warnings=("Source Conflict",),
            ),
        ),
        reference_datetime=REFERENCE,
    )

    assert timeline.confidence_trend == TrendDirection.DETERIORATING
    assert timeline.liquidity_trend == TrendDirection.DETERIORATING
    assert timeline.agreement_trend == TrendDirection.IMPROVING
    assert timeline.warnings == ("Source Conflict",)


def test_empty_timeline() -> None:
    timeline = TimelineAnalyticsBuilder().build(
        (),
        reference_datetime=REFERENCE,
        asset_id="CARD-EMPTY",
    )

    assert isinstance(timeline, TimelineSnapshot)
    assert timeline.asset_id == "CARD-EMPTY"
    assert timeline.trend_direction == TrendDirection.UNKNOWN
    assert timeline.radar_snapshot_ids == ()


def radar_snapshot(
    snapshot_id: str,
    *,
    current: int = 0,
    new: int = 0,
    resolved: int = 0,
    escalated: int = 0,
    changed: int = 0,
    summaries: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> RadarSnapshot:
    return RadarSnapshot(
        snapshot_id=snapshot_id,
        asset_id="CARD-001",
        generated_at=REFERENCE,
        reference_datetime=REFERENCE,
        current_signals=signals("current", current),
        previous_signals=signals("previous", 1),
        new_signals=signals("new", new),
        resolved_signals=signals("resolved", resolved),
        changed_signals=signals("changed", changed),
        escalated_signals=signals("escalated", escalated),
        change_summary=summaries,
        warning_summary=warnings,
        source_snapshot_ids=(f"source-{snapshot_id}",),
    )


def signals(prefix: str, count: int) -> tuple[RadarSignal, ...]:
    return tuple(
        RadarSignal(
            signal_id=f"{prefix}-{index}",
            signal_type="REVIEW_REQUIRED",
            severity="MEDIUM",
            title=f"{prefix.title()} Signal {index}",
            description=f"{prefix} signal {index}",
            created_at=REFERENCE,
            payload={"index": index},
        )
        for index in range(count)
    )
