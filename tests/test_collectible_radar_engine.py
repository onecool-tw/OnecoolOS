from copy import deepcopy
from datetime import datetime
from datetime import timezone

from onecool_os.business_logic.results import BusinessLogicResult
from onecool_os.radar import CollectibleRadarBuilder
from onecool_os.radar import RadarSnapshot
from onecool_os.radar import SignalSeverity
from onecool_os.radar import SignalType


REFERENCE = datetime(2026, 7, 5, tzinfo=timezone.utc)


def test_new_signal_detection() -> None:
    snapshot = CollectibleRadarBuilder().build(
        collectible_result("previous", market_quality="STRONG"),
        collectible_result("current", market_quality="PREMIUM"),
        reference_datetime=REFERENCE,
    )

    assert "Market Quality Improved" in _titles(snapshot.new_signals)


def test_resolved_signal_detection() -> None:
    snapshot = CollectibleRadarBuilder().build(
        collectible_result(
            "previous",
            valuation_quality="WEAK",
            warnings=("Low Confidence",),
        ),
        collectible_result("current", valuation_quality="STRONG"),
        reference_datetime=REFERENCE,
    )

    assert "Low Confidence Resolved" in _titles(snapshot.resolved_signals)


def test_changed_signal_detection() -> None:
    snapshot = CollectibleRadarBuilder().build(
        collectible_result("previous", source_quality="NORMAL"),
        collectible_result("current", source_quality="STRONG"),
        reference_datetime=REFERENCE,
    )

    assert "Source Agreement Improved" in _titles(snapshot.changed_signals)


def test_escalated_signal_detection() -> None:
    snapshot = CollectibleRadarBuilder().build(
        collectible_result("previous", liquidity_quality="STRONG"),
        collectible_result("current", liquidity_quality="WEAK"),
        reference_datetime=REFERENCE,
    )

    assert "Liquidity Deteriorated" in _titles(snapshot.escalated_signals)
    assert snapshot.escalated_signals[0].severity == SignalSeverity.HIGH


def test_trend_summary() -> None:
    snapshot = CollectibleRadarBuilder().build(
        collectible_result("previous", market_quality="STRONG"),
        collectible_result("current", market_quality="PREMIUM"),
        reference_datetime=REFERENCE,
    )

    assert "Market Quality Improved" in snapshot.change_summary


def test_no_mutation() -> None:
    previous = collectible_result(
        "previous",
        warnings=("Low Confidence",),
    )
    current = collectible_result("current")
    before = (deepcopy(previous.to_dict()), deepcopy(current.to_dict()))

    CollectibleRadarBuilder().build(
        previous,
        current,
        reference_datetime=REFERENCE,
    )

    assert (previous.to_dict(), current.to_dict()) == before


def test_deterministic_replay() -> None:
    previous = collectible_result("previous", market_quality="STRONG")
    current = collectible_result("current", market_quality="PREMIUM")
    builder = CollectibleRadarBuilder()

    first = builder.build(previous, current, reference_datetime=REFERENCE)
    second = builder.build(previous, current, reference_datetime=REFERENCE)

    assert first.to_dict() == second.to_dict()


def test_injected_reference_datetime() -> None:
    reference = datetime(2026, 8, 1, tzinfo=timezone.utc)

    snapshot = CollectibleRadarBuilder().build(
        collectible_result("previous"),
        collectible_result("current"),
        reference_datetime=reference,
    )

    assert snapshot.generated_at == reference
    assert snapshot.reference_datetime == reference


def test_current_and_previous_signals() -> None:
    snapshot = CollectibleRadarBuilder().build(
        collectible_result("previous", warnings=("Low Confidence",)),
        collectible_result("current", warnings=("Source Conflict",)),
        reference_datetime=REFERENCE,
    )

    assert snapshot.previous_signals[0].signal_type == (
        SignalType.LOW_CONFIDENCE
    )
    assert snapshot.current_signals[0].signal_type == SignalType.SOURCE_CONFLICT


def test_snapshot_model_output() -> None:
    snapshot = CollectibleRadarBuilder().build(
        collectible_result("previous"),
        collectible_result("current"),
        reference_datetime=REFERENCE,
    )

    assert isinstance(snapshot, RadarSnapshot)
    assert snapshot.asset_id == "CARD-001"
    assert snapshot.source_snapshot_ids == ("previous", "current")


def collectible_result(
    result_id: str,
    *,
    market_quality: str = "STRONG",
    valuation_quality: str = "STRONG",
    liquidity_quality: str = "STRONG",
    source_quality: str = "STRONG",
    review_status: str = "READY_FOR_REVIEW",
    warnings: tuple[str, ...] = (),
) -> BusinessLogicResult:
    return BusinessLogicResult(
        result_id=result_id,
        engine_name="collectible_intelligence",
        engine_version="v1",
        metric_type="EXPOSURE",
        payload={
            "market_quality": market_quality,
            "valuation_quality": valuation_quality,
            "liquidity_quality": liquidity_quality,
            "source_quality": source_quality,
            "review_status": review_status,
            "warnings": list(warnings),
            "market_intelligence": {
                "asset_id": "CARD-001",
                "confidence_score": 88,
                "confidence_level": "HIGH",
            },
        },
        tags=["collectible"],
    )


def _titles(signals) -> tuple[str, ...]:
    return tuple(signal.title for signal in signals)
