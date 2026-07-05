from copy import deepcopy
from datetime import datetime
from datetime import timezone

from onecool_os.decision import DecisionQueueBuilder
from onecool_os.ofai import CollectibleOFAIContext
from onecool_os.ofai import CollectibleOFAIContextBuilder
from onecool_os.report import CollectibleDailyRadarReport


REFERENCE = datetime(2026, 7, 5, tzinfo=timezone.utc)


def test_empty_context() -> None:
    source = report()
    queue = DecisionQueueBuilder().build(source)

    context = CollectibleOFAIContextBuilder().build(source, queue)

    assert isinstance(context, CollectibleOFAIContext)
    assert context.review_targets == ()
    assert context.warnings == ()
    assert context.decision_queue_summary["total_items"] == 0


def test_populated_context() -> None:
    source = report(
        warnings=("Source Conflict", "Low Confidence"),
        needs_review=1,
        new_signals=({"title": "Low Liquidity"},),
    )
    queue = DecisionQueueBuilder().build(source)

    context = CollectibleOFAIContextBuilder().build(source, queue)

    assert context.collection_summary["total_cards"] == 2
    assert context.market_summary["market_quality"] == "STRONG"
    assert context.radar_summary["new_signals"][0]["title"] == "Low Liquidity"
    assert context.timeline_summary["trend_direction"] == "STABLE"
    assert context.decision_queue_summary["total_items"] == 4


def test_review_targets() -> None:
    source = report(
        warnings=(
            "Missing Primary Market",
            "Low Confidence",
            "Low Liquidity",
            "Coverage Improvement",
        ),
    )
    queue = DecisionQueueBuilder().build(source)

    context = CollectibleOFAIContextBuilder().build(source, queue)

    assert [target["priority"] for target in context.review_targets] == [
        "CRITICAL",
        "HIGH",
        "MEDIUM",
        "LOW",
    ]
    assert context.review_targets[0]["title"] == "Missing Primary Market"


def test_warnings() -> None:
    source = report(warnings=("Stale Valuation",))
    queue = DecisionQueueBuilder().build(source)

    context = CollectibleOFAIContextBuilder().build(source, queue)

    assert context.warnings == ("Stale Valuation",)
    assert context.to_dict()["warnings"] == ["Stale Valuation"]


def test_metadata() -> None:
    source = report(warnings=("Source Conflict",))
    queue = DecisionQueueBuilder().build(source)

    context = CollectibleOFAIContextBuilder().build(source, queue)

    assert context.report_id == source.report_id
    assert context.decision_queue_id == queue.queue_id
    assert context.to_dict()["metadata"] == {
        "report_id": source.report_id,
        "decision_queue_id": queue.queue_id,
    }


def test_deterministic_output() -> None:
    source = report(warnings=("Source Conflict", "Low Confidence"))
    queue = DecisionQueueBuilder().build(source)
    builder = CollectibleOFAIContextBuilder()

    first = builder.build(source, queue)
    second = builder.build(source, queue)

    assert first.to_dict() == second.to_dict()


def test_replay_support() -> None:
    reference = datetime(2026, 8, 1, tzinfo=timezone.utc)
    source = report(reference_datetime=reference)
    queue = DecisionQueueBuilder().build(source)

    context = CollectibleOFAIContextBuilder().build(source, queue)

    assert context.reference_datetime == reference


def test_injected_reference_datetime() -> None:
    reference = datetime(2026, 8, 2, tzinfo=timezone.utc)
    source = report(reference_datetime=reference)
    queue = DecisionQueueBuilder().build(source)

    context = CollectibleOFAIContextBuilder().build(source, queue)

    assert context.reference_datetime == reference
    assert context.generated_at == REFERENCE


def test_no_mutation() -> None:
    source = report(
        warnings=("Source Conflict",),
        new_signals=({"title": "Low Liquidity"},),
    )
    queue = DecisionQueueBuilder().build(source)
    before_report = deepcopy(source.to_dict())
    before_queue = deepcopy(queue.to_dict())

    CollectibleOFAIContextBuilder().build(source, queue)

    assert source.to_dict() == before_report
    assert queue.to_dict() == before_queue


def report(
    *,
    warnings: tuple[str, ...] = (),
    new_signals: tuple[dict, ...] = (),
    needs_review: int = 0,
    reference_datetime: datetime = REFERENCE,
) -> CollectibleDailyRadarReport:
    return CollectibleDailyRadarReport(
        report_id="daily-radar:dashboard:CARD-001",
        generated_at=REFERENCE,
        reference_datetime=reference_datetime,
        total_cards=2,
        total_market_value=1000,
        total_cost_basis=700,
        unrealized_gain_loss=300,
        valuation_coverage=75,
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
        trend_summary=("Confidence Stable",),
        ready_for_review=0 if needs_review else 1,
        needs_review=needs_review,
        blocked=0,
        warnings=warnings,
        dashboard_snapshot_id="collectible-dashboard:CARD-001",
    )
