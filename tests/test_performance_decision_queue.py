from copy import deepcopy
from datetime import datetime
from datetime import timezone

from onecool_os.decision import DecisionQueueBuilder
from onecool_os.decision import DecisionQueuePriority
from onecool_os.report import CollectibleDailyRadarReport


REFERENCE = datetime(2026, 7, 9, tzinfo=timezone.utc)


def test_performance_critical_queue() -> None:
    queue = DecisionQueueBuilder().build(
        report(warnings=("Missing Cost Basis", "Missing Market Value"))
    )

    assert queue.critical_count == 2
    assert tuple(item.title for item in queue.critical) == (
        "Missing Cost Basis",
        "Missing Market Value",
    )
    assert all(
        item.priority == DecisionQueuePriority.CRITICAL
        for item in queue.critical
    )


def test_performance_high_queue() -> None:
    queue = DecisionQueueBuilder().build(
        report(warnings=("Insufficient Data", "Currency Mismatch"))
    )

    assert queue.high_count == 2
    assert tuple(item.title for item in queue.high) == (
        "Currency Mismatch",
        "Insufficient Data",
    )


def test_performance_medium_queue() -> None:
    queue = DecisionQueueBuilder().build(
        report(warnings=("Missing Holding Date",))
    )

    assert queue.medium_count == 1
    assert queue.medium[0].priority == DecisionQueuePriority.MEDIUM
    assert queue.medium[0].title == "Missing Holding Date"


def test_performance_low_queue() -> None:
    queue = DecisionQueueBuilder().build(report())

    assert queue.low_count == 1
    assert queue.low[0].title == "Performance Review Only"
    assert queue.low[0].source == "daily_radar_report.performance"


def test_performance_deterministic_replay() -> None:
    source = report(warnings=("Missing Cost Basis", "Insufficient Data"))
    builder = DecisionQueueBuilder()

    first = builder.build(source).to_dict()
    second = builder.build(source).to_dict()

    assert first == second


def test_performance_no_mutation() -> None:
    source = report(warnings=("Missing Cost Basis",))
    before = deepcopy(source.to_dict())

    DecisionQueueBuilder().build(source)

    assert source.to_dict() == before


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
            "top_losers": [],
        },
        warnings=warnings,
        dashboard_snapshot_id="collectible-dashboard:CARD-001",
    )
