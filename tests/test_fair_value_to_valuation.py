from __future__ import annotations

from copy import deepcopy
from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from onecool_os.fair_value import FairValueConfidence
from onecool_os.fair_value import FairValueFreshness
from onecool_os.fair_value import FairValueLiquidity
from onecool_os.fair_value import OnecoolFairValueSnapshot
from onecool_os.runtime import RuntimeSession
from onecool_os.valuation import FairValueValuationEngine
from onecool_os.valuation import RuntimeValuationStatus
from onecool_os.valuation import ValuationIntegrationError
from onecool_os.valuation import ValuationSource

REFERENCE = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)


def test_zero_fair_values_create_no_valuation_records() -> None:
    result = FairValueValuationEngine().build(())

    assert result.valuation_records == ()
    assert result.mappings == ()
    assert result.placeholders == ()


def test_insufficient_data_snapshot_creates_placeholder_only() -> None:
    result = FairValueValuationEngine().build((_snapshot(fair_value=None, confidence="INSUFFICIENT_DATA"),))

    assert result.valuation_records == ()
    assert len(result.placeholders) == 1
    assert result.placeholders[0].status == RuntimeValuationStatus.INSUFFICIENT_DATA


def test_one_fair_value_creates_one_valuation_record() -> None:
    result = FairValueValuationEngine().build((_snapshot(),))

    assert len(result.valuation_records) == 1
    record = result.valuation_records[0]
    assert record.valuation_id == "onecool-fair-value:PSA-123:20260711T090000+0000"
    assert record.asset_id == "PSA-123"
    assert record.source == ValuationSource.ONECOOL_FAIR_VALUE
    assert record.market_value == Decimal("250")
    assert record.currency == "USD"
    assert record.confidence.value == "HIGH"
    assert record.effective_date == date(2026, 7, 1)
    assert "onecool-fair-value" in record.tags


def test_multiple_fair_values_create_multiple_records() -> None:
    result = FairValueValuationEngine().build((
        _snapshot(asset_id="PSA-1", cert_number="1", fair_value="100"),
        _snapshot(asset_id="PSA-2", cert_number="2", fair_value="200"),
    ))

    assert [record.asset_id for record in result.valuation_records] == ["PSA-1", "PSA-2"]


def test_duplicate_source_is_rejected() -> None:
    with pytest.raises(ValuationIntegrationError, match="duplicate valuation source"):
        FairValueValuationEngine().build((
            _snapshot(asset_id="PSA-1"),
            _snapshot(asset_id="PSA-1", fair_value="300"),
        ))


def test_missing_market_value_is_rejected_for_trusted_snapshot() -> None:
    result = FairValueValuationEngine().build((_snapshot(fair_value=None, confidence="HIGH"),))

    assert result.valuation_records == ()
    assert result.placeholders[0].status == RuntimeValuationStatus.REJECTED
    assert "missing market value" in result.warnings[0]


def test_missing_asset_is_rejected() -> None:
    snapshot = SimpleNamespace(
        asset_id="",
        cert_number="123",
        fair_value=Decimal("250"),
        currency="USD",
        confidence=FairValueConfidence.HIGH,
        latest_sold_date=date(2026, 7, 1),
        eqs=Decimal("100"),
        sample_count=5,
        freshness=FairValueFreshness.CURRENT,
        liquidity=FairValueLiquidity.HIGH,
        warnings=(),
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )

    result = FairValueValuationEngine().build((snapshot,))

    assert result.valuation_records == ()
    assert result.placeholders[0].status == RuntimeValuationStatus.REJECTED
    assert "missing asset" in result.warnings[0]


def test_confidence_eqs_freshness_and_liquidity_propagate() -> None:
    mapping = FairValueValuationEngine().build((_snapshot(confidence="MEDIUM", eqs="77"),)).mappings[0]

    assert mapping.confidence == "MEDIUM"
    assert mapping.valuation_record.confidence.value == "MEDIUM"
    assert mapping.evidence_quality_score == Decimal("77")
    assert mapping.freshness_status == "CURRENT"
    assert mapping.liquidity == "HIGH"
    assert mapping.sample_count == 5


def test_invalid_confidence_is_rejected() -> None:
    snapshot = SimpleNamespace(
        asset_id="PSA-123",
        cert_number="123",
        fair_value=Decimal("250"),
        currency="USD",
        confidence="BROKEN",
        latest_sold_date=date(2026, 7, 1),
        eqs=Decimal("100"),
        sample_count=5,
        freshness=FairValueFreshness.CURRENT,
        liquidity=FairValueLiquidity.HIGH,
        warnings=(),
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )

    result = FairValueValuationEngine().build((snapshot,))

    assert result.valuation_records == ()
    assert result.placeholders[0].status == RuntimeValuationStatus.REJECTED
    assert "invalid confidence" in result.warnings[0]


def test_runtime_delegation_with_no_verified_evidence() -> None:
    runtime = RuntimeSession(
        imported_records=tuple(_asset(f"PSA-{index}", str(index)) for index in range(1, 51)),
        generated_at=REFERENCE,
    )

    assert runtime.build_valuation_records() == ()
    assert runtime.valuation_records() == ()
    assert runtime.valuation_record("PSA-1") is None
    result = FairValueValuationEngine().build_from_runtime_session(runtime)
    assert len(result.placeholders) == 50
    assert all(item.status == RuntimeValuationStatus.INSUFFICIENT_DATA for item in result.placeholders)


def test_no_mutation_and_deterministic_replay() -> None:
    snapshots = (_snapshot(),)
    before = deepcopy([snapshot.to_dict() for snapshot in snapshots])
    engine = FairValueValuationEngine()

    first = engine.build(snapshots)
    second = engine.build(snapshots)

    assert [snapshot.to_dict() for snapshot in snapshots] == before
    assert first.to_dict() == second.to_dict()


def _snapshot(
    *,
    asset_id: str = "PSA-123",
    cert_number: str = "123",
    fair_value: str | None = "250",
    confidence: str = "HIGH",
    eqs: str = "100",
) -> OnecoolFairValueSnapshot:
    return OnecoolFairValueSnapshot(
        asset_id=asset_id,
        cert_number=cert_number,
        fair_value=fair_value,
        currency="USD" if fair_value is not None else None,
        minimum=fair_value,
        maximum=fair_value,
        median=fair_value,
        average=fair_value,
        trimmed_mean=fair_value,
        standard_deviation="0",
        sample_count=5 if fair_value is not None else 0,
        latest_sold_date=date(2026, 7, 1) if fair_value is not None else None,
        oldest_included_date=date(2026, 7, 1) if fair_value is not None else None,
        liquidity="HIGH" if fair_value is not None else "ILLIQUID",
        freshness="CURRENT" if fair_value is not None else "UNKNOWN",
        confidence=confidence,
        eqs=eqs if fair_value is not None else "0",
        eqs_breakdown={
            "sample_size": "30",
            "identity_match": "25",
            "freshness": "20",
            "liquidity": "15",
            "evidence_completeness": "10",
        },
        warnings=() if fair_value is not None else ("No Verified Sold Comps",),
        evidence_ids=("ev-1",) if fair_value is not None else (),
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )


def _asset(asset_id: str, cert_number: str) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "cert_number": cert_number,
        "player": "Shohei Ohtani",
        "grade_company": "PSA",
        "grade": "10",
    }
