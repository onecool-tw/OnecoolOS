from copy import deepcopy
from datetime import datetime
from datetime import timezone

from onecool_os.decision import DecisionQueue
from onecool_os.decision import DecisionQueueBuilder
from onecool_os.decision import DecisionQueuePriority
from onecool_os.report import CollectibleDailyRadarReport


REFERENCE = datetime(2026, 7, 5, tzinfo=timezone.utc)


def test_empty_queue() -> None:
    queue = DecisionQueueBuilder().build(report())

    assert isinstance(queue, DecisionQueue)
    assert queue.total_items == 0
    assert queue.critical == ()
    assert queue.high == ()
    assert queue.medium == ()
    assert queue.low == ()


def test_critical_queue() -> None:
    queue = DecisionQueueBuilder().build(
        report(warnings=("Source Conflict",))
    )

    assert queue.critical_count == 1
    assert queue.critical[0].priority == DecisionQueuePriority.CRITICAL
    assert queue.critical[0].title == "Source Conflict"


def test_high_queue() -> None:
    queue = DecisionQueueBuilder().build(
        report(warnings=("Low Confidence",))
    )

    assert queue.high_count == 1
    assert queue.high[0].priority == DecisionQueuePriority.HIGH


def test_medium_queue() -> None:
    queue = DecisionQueueBuilder().build(
        report(warnings=("Low Liquidity",))
    )

    assert queue.medium_count == 1
    assert queue.medium[0].priority == DecisionQueuePriority.MEDIUM


def test_low_queue() -> None:
    queue = DecisionQueueBuilder().build(
        report(new_signals=({"title": "Coverage Improvement"},))
    )

    assert queue.low_count == 1
    assert queue.low[0].priority == DecisionQueuePriority.LOW


def test_review_items() -> None:
    queue = DecisionQueueBuilder().build(
        report(needs_review=1, blocked=1)
    )

    assert queue.critical_count == 1
    assert queue.medium_count == 1
    assert queue.critical[0].title == "Blocked Review Items"
    assert queue.medium[0].title == "Needs Review"


def test_deterministic_output() -> None:
    source = report(
        warnings=("Source Conflict", "Low Confidence", "Low Liquidity"),
        new_signals=({"title": "Coverage Improvement"},),
    )
    builder = DecisionQueueBuilder()

    first = builder.build(source)
    second = builder.build(source)

    assert first.to_dict() == second.to_dict()


def test_replay_support() -> None:
    source = report(reference_datetime=datetime(2026, 8, 1, tzinfo=timezone.utc))

    queue = DecisionQueueBuilder().build(source)

    assert queue.reference_datetime == source.reference_datetime


def test_no_mutation() -> None:
    source = report(
        warnings=("Source Conflict",),
        new_signals=({"title": "Coverage Improvement"},),
    )
    before = deepcopy(source.to_dict())

    DecisionQueueBuilder().build(source)

    assert source.to_dict() == before


def report(
    *,
    warnings: tuple[str, ...] = (),
    new_signals: tuple[dict, ...] = (),
    needs_review: int = 0,
    blocked: int = 0,
    reference_datetime: datetime = REFERENCE,
) -> CollectibleDailyRadarReport:
    return CollectibleDailyRadarReport(
        report_id="daily-radar:dashboard:CARD-001",
        generated_at=REFERENCE,
        reference_datetime=reference_datetime,
        total_cards=1,
        total_market_value=100,
        total_cost_basis=80,
        unrealized_gain_loss=20,
        valuation_coverage=80,
        market_quality="STRONG",
        confidence_summary={"confidence_level": "HIGH"},
        agreement_summary={"agreement_level": "GOOD"},
        liquidity_summary={"liquidity_level": "HIGH"},
        new_signals=new_signals,
        resolved_signals=(),
        changed_signals=(),
        escalated_signals=(),
        trend_direction="STABLE",
        trend_strength="NONE",
        trend_summary=(),
        ready_for_review=1 if not needs_review and not blocked else 0,
        needs_review=needs_review,
        blocked=blocked,
        performance_summary={},
        top_movers={},
        warnings=warnings,
        dashboard_snapshot_id="collectible-dashboard:CARD-001",
    )
