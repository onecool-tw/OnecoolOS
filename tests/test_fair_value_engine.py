from __future__ import annotations

from copy import deepcopy
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal

from onecool_os.fair_value import FairValueConfidence
from onecool_os.fair_value import FairValueFreshness
from onecool_os.fair_value import FairValueLiquidity
from onecool_os.fair_value import OnecoolFairValueEngine
from onecool_os.fair_value import select_verified_comparables
from onecool_os.runtime import RuntimeSession
from onecool_os.valuation.evidence import EbaySoldEvidence

REFERENCE = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)


def test_median_average_trimmed_mean_and_standard_deviation() -> None:
    evidence = tuple(
        _evidence(index=index, price=price, sold_date=REFERENCE.date() - timedelta(days=index))
        for index, price in enumerate(("10", "20", "30", "40", "50"), start=1)
    )

    snapshot = OnecoolFairValueEngine().build_from_evidence(
        evidence,
        asset_id="PSA-123",
        reference_datetime=REFERENCE,
    )

    assert snapshot.minimum == Decimal("10")
    assert snapshot.maximum == Decimal("50")
    assert snapshot.median == Decimal("30")
    assert snapshot.average == Decimal("30")
    assert snapshot.trimmed_mean == Decimal("30")
    assert snapshot.standard_deviation == Decimal("14.1421")
    assert snapshot.fair_value == Decimal("30")


def test_rejects_non_verified_and_identity_mismatched_evidence() -> None:
    evidence = (
        _evidence(index=1, price="100"),
        _evidence(index=2, price="100", status="NEEDS_REVIEW"),
        _evidence(index=3, price="100", mismatched_fields=["GRADE"]),
        _evidence(index=4, price="100", sold_date=None),
        _evidence(index=5, price="100", ebay_item_id=None),
    )

    snapshot = OnecoolFairValueEngine().build_from_evidence(
        evidence,
        asset_id="PSA-123",
        reference_datetime=REFERENCE,
    )

    assert snapshot.sample_count == 1
    assert snapshot.evidence_ids == ("ev-1",)


def test_duplicate_sold_items_are_deduplicated() -> None:
    evidence = (
        _evidence(index=1, price="100", item_id="same-item"),
        _evidence(index=2, price="200", item_id="same-item"),
    )

    snapshot = OnecoolFairValueEngine().build_from_evidence(
        evidence,
        asset_id="PSA-123",
        reference_datetime=REFERENCE,
    )

    assert snapshot.sample_count == 1
    assert snapshot.evidence_ids == ("ev-2",)


def test_latest_10_verified_comps_are_selected() -> None:
    evidence = tuple(
        _evidence(index=index, price=str(100 + index), sold_date=REFERENCE.date() - timedelta(days=index))
        for index in range(1, 13)
    )

    snapshot = OnecoolFairValueEngine().build_from_evidence(
        evidence,
        asset_id="PSA-123",
        reference_datetime=REFERENCE,
    )

    assert snapshot.sample_count == 10
    assert snapshot.latest_sold_date == date(2026, 7, 10)
    assert snapshot.oldest_included_date == date(2026, 7, 1)
    assert "ev-11" not in snapshot.evidence_ids
    assert "ev-12" not in snapshot.evidence_ids


def test_180_day_window_excludes_old_evidence() -> None:
    evidence = (
        _evidence(index=1, price="100", sold_date=REFERENCE.date() - timedelta(days=180)),
        _evidence(index=2, price="200", sold_date=REFERENCE.date() - timedelta(days=181)),
    )

    snapshot = OnecoolFairValueEngine().build_from_evidence(
        evidence,
        asset_id="PSA-123",
        reference_datetime=REFERENCE,
    )

    assert snapshot.sample_count == 1
    assert snapshot.evidence_ids == ("ev-1",)


def test_liquidity_levels() -> None:
    high = _snapshot_for_count(5, days_old=5)
    medium = _snapshot_for_count(3, days_old=60)
    low = _snapshot_for_count(1, days_old=120)
    none = OnecoolFairValueEngine().build_from_evidence(
        (),
        asset_id="PSA-123",
        reference_datetime=REFERENCE,
    )

    assert high.liquidity == FairValueLiquidity.HIGH
    assert medium.liquidity == FairValueLiquidity.MEDIUM
    assert low.liquidity == FairValueLiquidity.LOW
    assert none.liquidity == FairValueLiquidity.ILLIQUID


def test_freshness_levels() -> None:
    assert _snapshot_for_count(1, days_old=30).freshness == FairValueFreshness.CURRENT
    assert _snapshot_for_count(1, days_old=90).freshness == FairValueFreshness.AGING
    assert _snapshot_for_count(1, days_old=120).freshness == FairValueFreshness.STALE
    empty = OnecoolFairValueEngine().build_from_evidence(
        (),
        asset_id="PSA-123",
        reference_datetime=REFERENCE,
    )
    assert empty.freshness == FairValueFreshness.UNKNOWN


def test_confidence_rules() -> None:
    assert _snapshot_for_count(5).confidence == FairValueConfidence.HIGH
    assert _snapshot_for_count(4).confidence == FairValueConfidence.MEDIUM
    assert _snapshot_for_count(3).confidence == FairValueConfidence.MEDIUM
    assert _snapshot_for_count(2).confidence == FairValueConfidence.LOW
    assert _snapshot_for_count(1).confidence == FairValueConfidence.LOW
    assert _snapshot_for_count(0).confidence == FairValueConfidence.INSUFFICIENT_DATA


def test_evidence_quality_score_and_breakdown() -> None:
    snapshot = _snapshot_for_count(5)

    assert snapshot.eqs == Decimal("100")
    assert snapshot.eqs_breakdown["sample_size"] == Decimal("30")
    assert snapshot.eqs_breakdown["identity_match"] == Decimal("25")
    assert snapshot.eqs_breakdown["sold_count_180_days"] == 5
    assert snapshot.warnings == ()


def test_insufficient_data_snapshot_reports_honestly() -> None:
    snapshot = OnecoolFairValueEngine().build_from_evidence(
        (),
        asset_id="PSA-123",
        reference_datetime=REFERENCE,
    )

    assert snapshot.fair_value is None
    assert snapshot.sample_count == 0
    assert snapshot.confidence == FairValueConfidence.INSUFFICIENT_DATA
    assert "No Verified Sold Comps" in snapshot.warnings
    assert "Insufficient Verified Evidence" in snapshot.warnings


def test_no_mutation_and_deterministic_replay() -> None:
    evidence = tuple(_evidence(index=index, price=str(100 + index)) for index in range(1, 6))
    before = tuple(item.to_dict() for item in evidence)
    engine = OnecoolFairValueEngine()

    first = engine.build_from_evidence(evidence, asset_id="PSA-123", reference_datetime=REFERENCE)
    second = engine.build_from_evidence(evidence, asset_id="PSA-123", reference_datetime=REFERENCE)

    assert tuple(item.to_dict() for item in evidence) == before
    assert first.to_dict() == second.to_dict()


def test_runtime_session_builds_fair_value_without_calculating_inside_runtime() -> None:
    runtime = RuntimeSession(
        imported_records=(
            _asset("PSA-1", "1"),
            _asset("PSA-2", "2"),
        ),
        generated_at=REFERENCE,
    )

    snapshots = runtime.build_fair_value()

    assert len(snapshots) == 2
    assert all(item.confidence == FairValueConfidence.INSUFFICIENT_DATA for item in snapshots)
    assert runtime.fair_value("PSA-1").asset_id == "PSA-1"
    assert runtime.fair_value("missing") is None


def test_real_trial_shape_with_50_assets_and_no_verified_evidence() -> None:
    runtime = RuntimeSession(
        imported_records=tuple(_asset(f"PSA-{index}", str(index)) for index in range(1, 51)),
        generated_at=REFERENCE,
    )

    snapshots = runtime.build_fair_value()

    assert len(snapshots) == 50
    assert sum(1 for item in snapshots if item.fair_value is not None) == 0
    assert all(item.confidence == FairValueConfidence.INSUFFICIENT_DATA for item in snapshots)


def test_select_verified_comparables_does_not_mutate_input() -> None:
    evidence = [_evidence(index=1, price="100")]
    before = deepcopy([item.to_dict() for item in evidence])

    selected = select_verified_comparables(
        evidence,
        asset_id="PSA-123",
        reference_datetime=REFERENCE,
    )

    assert len(selected) == 1
    assert [item.to_dict() for item in evidence] == before


def _snapshot_for_count(count: int, *, days_old: int = 5):
    evidence = tuple(
        _evidence(
            index=index,
            price=str(100 + index),
            sold_date=REFERENCE.date() - timedelta(days=days_old),
        )
        for index in range(1, count + 1)
    )
    return OnecoolFairValueEngine().build_from_evidence(
        evidence,
        asset_id="PSA-123",
        reference_datetime=REFERENCE,
    )


def _evidence(
    *,
    index: int,
    price: str,
    sold_date: date | None = date(2026, 7, 1),
    status: str = "VERIFIED",
    mismatched_fields: list[str] | None = None,
    item_id: str | None = None,
    ebay_item_id: str | None = "AUTO",
) -> EbaySoldEvidence:
    actual_item_id = item_id if item_id is not None else ebay_item_id
    if actual_item_id == "AUTO":
        actual_item_id = f"item-{index}"
    return EbaySoldEvidence(
        evidence_id=f"ev-{index}",
        asset_id="PSA-123",
        cert_number="123",
        provider_name="fixture",
        search_url="https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1",
        sold_item_url=f"https://www.ebay.com/itm/{actual_item_id}" if actual_item_id else None,
        ebay_item_id=actual_item_id,
        title="2018 Topps Update US1 Shohei Ohtani PSA 10",
        sold_price=price,
        currency="USD",
        shipping_amount="5.00",
        sold_date=sold_date,
        listing_type="AUCTION",
        best_offer_used=False,
        exact_match=True,
        matched_fields=[
            "YEAR",
            "SET",
            "CARD_NUMBER",
            "SUBJECT",
            "GRADE_ISSUER",
            "GRADE",
        ],
        mismatched_fields=mismatched_fields or [],
        confidence="HIGH",
        status=status,
        collected_at=REFERENCE.isoformat(),
        reference_datetime=REFERENCE.isoformat(),
        raw_metadata={},
        warnings=[],
    )


def _asset(asset_id: str, cert_number: str) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "cert_number": cert_number,
        "player": "Shohei Ohtani",
        "grade_company": "PSA",
        "grade": "10",
    }
