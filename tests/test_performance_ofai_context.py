from copy import deepcopy
from datetime import datetime
from datetime import timezone

from onecool_os.decision import DecisionQueueBuilder
from onecool_os.ofai import CollectibleOFAIContextBuilder
from onecool_os.report import CollectibleDailyRadarReport


REFERENCE = datetime(2026, 7, 9, tzinfo=timezone.utc)


def test_performance_summary_included() -> None:
    source = report()
    queue = DecisionQueueBuilder().build(source)

    context = CollectibleOFAIContextBuilder().build(source, queue)

    assert context.performance_overview == {
        "total_cost_basis": "80.00",
        "total_market_value": "100.00",
        "unrealized_gain_loss": "20.00",
        "unrealized_percent": "0.25",
        "performing_assets": 1,
    }


def test_performance_review_priorities_included() -> None:
    source = report(
        warnings=(
            "Missing Cost Basis",
            "Insufficient Data",
            "Missing Holding Date",
        )
    )
    queue = DecisionQueueBuilder().build(source)

    context = CollectibleOFAIContextBuilder().build(source, queue)

    assert context.performance_review_priorities["critical"][0]["title"] == (
        "Missing Cost Basis"
    )
    assert context.performance_review_priorities["high"][0]["title"] == (
        "Insufficient Data"
    )
    assert context.performance_review_priorities["medium"][0]["title"] == (
        "Missing Holding Date"
    )


def test_performance_warnings_included() -> None:
    source = report(
        warnings=(
            "Missing Market Value",
            "Currency Mismatch",
            "Insufficient Data",
        )
    )
    queue = DecisionQueueBuilder().build(source)

    context = CollectibleOFAIContextBuilder().build(source, queue)

    assert context.warnings == (
        "Missing Market Value",
        "Currency Mismatch",
        "Insufficient Data",
    )


def test_performance_top_movers_included() -> None:
    source = report()
    queue = DecisionQueueBuilder().build(source)

    context = CollectibleOFAIContextBuilder().build(source, queue)

    assert context.top_movers["top_gainers"][0]["asset_id"] == "CARD-001"
    assert context.top_movers["top_losers"][0]["asset_id"] == "CARD-002"


def test_performance_deterministic_replay() -> None:
    source = report(warnings=("Missing Cost Basis", "Insufficient Data"))
    queue = DecisionQueueBuilder().build(source)
    builder = CollectibleOFAIContextBuilder()

    first = builder.build(source, queue).to_dict()
    second = builder.build(source, queue).to_dict()

    assert first == second


def test_performance_no_mutation() -> None:
    source = report(warnings=("Missing Cost Basis",))
    queue = DecisionQueueBuilder().build(source)
    before_report = deepcopy(source.to_dict())
    before_queue = deepcopy(queue.to_dict())

    CollectibleOFAIContextBuilder().build(source, queue)

    assert source.to_dict() == before_report
    assert queue.to_dict() == before_queue


def report(
    *,
    warnings: tuple[str, ...] = (),
) -> CollectibleDailyRadarReport:
    return CollectibleDailyRadarReport(
        report_id="daily-radar:dashboard:CARD-001",
        generated_at=REFERENCE,
        reference_datetime=REFERENCE,
        total_cards=1,
        total_market_value=100,
        total_cost_basis=80,
        unrealized_gain_loss=20,
        valuation_coverage=80,
        market_quality="STRONG",
        confidence_summary={"confidence_level": "HIGH"},
        agreement_summary={"agreement_level": "GOOD"},
        liquidity_summary={"liquidity_level": "HIGH"},
        new_signals=(),
        resolved_signals=(),
        changed_signals=(),
        escalated_signals=(),
        trend_direction="STABLE",
        trend_strength="NONE",
        trend_summary=(),
        ready_for_review=1,
        needs_review=0,
        blocked=0,
        performance_summary={
            "total_cost_basis": "80.00",
            "total_market_value": "100.00",
            "total_unrealized_gain_loss": "20.00",
            "total_unrealized_percent": "0.25",
            "performing_assets": 1,
            "missing_valuations": 0,
            "missing_cost_basis": 0,
        },
        top_movers={
            "top_gainers": [{"asset_id": "CARD-001"}],
            "top_losers": [{"asset_id": "CARD-002"}],
        },
        warnings=warnings,
        dashboard_snapshot_id="collectible-dashboard:CARD-001",
    )
