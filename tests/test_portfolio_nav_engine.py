from __future__ import annotations

from copy import deepcopy
from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal

from onecool_os.portfolio import PortfolioNavEngine
from onecool_os.portfolio import PortfolioNavStatus
from onecool_os.portfolio import ValuationCoverageStatus
from onecool_os.runtime.session import RuntimeSession
from onecool_os.valuation.evidence import EbaySoldEvidence
from onecool_os.valuation.evidence import EbaySoldEvidenceBatch
from onecool_os.valuation.models import ValuationRecord

REFERENCE = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)


def test_one_verified_asset() -> None:
    snapshot = _single_snapshot(
        [_asset("PSA-1", cost="120.00")],
        [_valuation("v1", "PSA-1", "250.00", source="EBAY_SOLD")],
    )

    assert snapshot.status == PortfolioNavStatus.COMPLETE
    assert snapshot.total_cost_basis == Decimal("120.00")
    assert snapshot.total_market_value == Decimal("250.00")
    assert snapshot.unrealized_gain_loss == Decimal("130.00")
    assert snapshot.roi_percent == Decimal("108.3333")
    assert snapshot.valuation_coverage_percent == Decimal("100.0000")
    assert snapshot.verified_coverage_percent == Decimal("100.0000")
    assert snapshot.asset_lines[0].coverage_status == ValuationCoverageStatus.VERIFIED


def test_multiple_verified_assets() -> None:
    snapshot = _single_snapshot(
        [_asset("PSA-1", cost="120"), _asset("PSA-2", cost="80")],
        [
            _valuation("v1", "PSA-1", "250", source="EBAY_SOLD"),
            _valuation("v2", "PSA-2", "100", source="EBAY_SOLD"),
        ],
    )

    assert snapshot.total_assets == 2
    assert snapshot.total_cost_basis == Decimal("200.00")
    assert snapshot.total_market_value == Decimal("350.00")
    assert snapshot.unrealized_gain_loss == Decimal("150.00")


def test_missing_market_value() -> None:
    snapshot = _single_snapshot([_asset("PSA-1", cost="120")], [])

    assert snapshot.status == PortfolioNavStatus.INSUFFICIENT_DATA
    assert snapshot.assets_with_market_value == 0
    assert snapshot.missing_value_assets == 1
    assert "Missing Market Value" in snapshot.asset_lines[0].warnings


def test_missing_cost_basis() -> None:
    snapshot = _single_snapshot(
        [_asset("PSA-1", cost=None)],
        [_valuation("v1", "PSA-1", "250", source="EBAY_SOLD")],
    )

    assert snapshot.status == PortfolioNavStatus.INSUFFICIENT_DATA
    assert snapshot.assets_with_cost == 0
    assert snapshot.roi_percent is None
    assert "Missing Cost Basis" in snapshot.asset_lines[0].warnings


def test_supporting_estimate_classified_separately() -> None:
    snapshot = _single_snapshot(
        [_asset("PSA-1", cost="120")],
        [_valuation("v1", "PSA-1", "250", source="MANUAL")],
    )

    assert snapshot.status == PortfolioNavStatus.PARTIAL
    assert snapshot.estimated_assets == 1
    assert snapshot.verified_assets == 0
    assert snapshot.asset_lines[0].coverage_status == ValuationCoverageStatus.ESTIMATED
    assert "Supporting Estimate Only" in snapshot.asset_lines[0].warnings


def test_needs_review_evidence_excluded_from_trusted_nav() -> None:
    evidence = _evidence("ev-1", status="NEEDS_REVIEW")
    batch = _batch(evidence)
    snapshot = _single_snapshot(
        [_asset("PSA-1", cost="120")],
        [_valuation("ebay-sold:ev-1", "PSA-1", "250", source="EBAY_SOLD")],
        evidence_batches=[batch],
    )

    assert snapshot.assets_with_market_value == 0
    assert snapshot.review_required_assets == 1
    assert snapshot.asset_lines[0].coverage_status == ValuationCoverageStatus.REVIEW_REQUIRED
    assert "Evidence Needs Review" in snapshot.asset_lines[0].warnings


def test_rejected_evidence_excluded() -> None:
    evidence = _evidence("ev-1", status="REJECTED", mismatched_fields=("GRADE",))
    batch = _batch(evidence)
    snapshot = _single_snapshot(
        [_asset("PSA-1", cost="120")],
        [_valuation("ebay-sold:ev-1", "PSA-1", "250", source="EBAY_SOLD")],
        evidence_batches=[batch],
    )

    assert snapshot.assets_with_market_value == 0
    assert snapshot.missing_value_assets == 1
    assert "Evidence Needs Review" in snapshot.asset_lines[0].warnings


def test_latest_eligible_valuation_selected() -> None:
    snapshot = _single_snapshot(
        [_asset("PSA-1", cost="120")],
        [
            _valuation("v1", "PSA-1", "200", source="EBAY_SOLD", valuation_date=date(2026, 7, 1)),
            _valuation("v2", "PSA-1", "250", source="EBAY_SOLD", valuation_date=date(2026, 7, 2)),
        ],
    )

    assert snapshot.asset_lines[0].valuation_record_id == "v2"
    assert snapshot.asset_lines[0].market_value == Decimal("250.00")


def test_deterministic_valuation_tie_break() -> None:
    snapshot = _single_snapshot(
        [_asset("PSA-1", cost="120")],
        [
            _valuation("v1", "PSA-1", "200", source="EBAY_SOLD"),
            _valuation("v9", "PSA-1", "250", source="EBAY_SOLD"),
        ],
    )

    assert snapshot.asset_lines[0].valuation_record_id == "v9"
    assert "Multiple Eligible Valuation Records" in snapshot.asset_lines[0].warnings


def test_multiple_currencies_produce_separate_snapshots() -> None:
    snapshots = PortfolioNavEngine().build_snapshots(
        [_asset("PSA-1", cost="120", currency="USD"), _asset("PSA-2", cost="3000", currency="TWD")],
        [
            _valuation("v1", "PSA-1", "250", currency="USD", source="EBAY_SOLD"),
            _valuation("v2", "PSA-2", "5000", currency="TWD", source="EBAY_SOLD"),
        ],
        reference_datetime=REFERENCE,
    )

    assert [snapshot.currency for snapshot in snapshots] == ["TWD", "USD"]
    assert [snapshot.total_assets for snapshot in snapshots] == [1, 1]


def test_currency_mismatch() -> None:
    snapshot = _single_snapshot(
        [_asset("PSA-1", cost="120", currency="USD")],
        [_valuation("v1", "PSA-1", "250", currency="TWD", source="EBAY_SOLD")],
    )

    assert snapshot.status == PortfolioNavStatus.CURRENCY_MISMATCH
    assert snapshot.unrealized_gain_loss is None
    assert "Currency Mismatch" in snapshot.asset_lines[0].warnings


def test_zero_cost_basis() -> None:
    snapshot = _single_snapshot(
        [_asset("PSA-1", cost="0")],
        [_valuation("v1", "PSA-1", "250", source="EBAY_SOLD")],
    )

    assert snapshot.status == PortfolioNavStatus.INSUFFICIENT_DATA
    assert snapshot.roi_percent is None
    assert "Zero or Negative Cost Basis" in snapshot.asset_lines[0].warnings


def test_negative_cost_basis() -> None:
    snapshot = _single_snapshot(
        [_asset("PSA-1", cost="-10")],
        [_valuation("v1", "PSA-1", "250", source="EBAY_SOLD")],
    )

    assert snapshot.status == PortfolioNavStatus.INSUFFICIENT_DATA
    assert snapshot.total_cost_basis == Decimal("0.00")
    assert "Zero or Negative Cost Basis" in snapshot.asset_lines[0].warnings


def test_decimal_precision_and_rounding_policy() -> None:
    snapshot = _single_snapshot(
        [_asset("PSA-1", cost="120.005")],
        [_valuation("v1", "PSA-1", "250.006", source="EBAY_SOLD")],
    )

    assert snapshot.total_cost_basis == Decimal("120.00")
    assert snapshot.total_market_value == Decimal("250.01")
    assert snapshot.to_dict()["roi_percent"] == "108.3417"


def test_portfolio_totals_and_coverage() -> None:
    snapshot = _single_snapshot(
        [_asset("PSA-1", cost="100"), _asset("PSA-2", cost="100")],
        [_valuation("v1", "PSA-1", "150", source="EBAY_SOLD")],
    )

    assert snapshot.total_cost_basis == Decimal("200.00")
    assert snapshot.total_market_value == Decimal("150.00")
    assert snapshot.valuation_coverage_percent == Decimal("50.0000")
    assert snapshot.verified_coverage_percent == Decimal("50.0000")
    assert snapshot.status == PortfolioNavStatus.PARTIAL


def test_complete_status() -> None:
    snapshot = _single_snapshot(
        [_asset("PSA-1", cost="100")],
        [_valuation("v1", "PSA-1", "150", source="EBAY_SOLD")],
    )

    assert snapshot.status == PortfolioNavStatus.COMPLETE


def test_partial_status() -> None:
    snapshot = _single_snapshot(
        [_asset("PSA-1", cost="100"), _asset("PSA-2", cost="100")],
        [_valuation("v1", "PSA-1", "150", source="EBAY_SOLD")],
    )

    assert snapshot.status == PortfolioNavStatus.PARTIAL


def test_insufficient_data_status() -> None:
    snapshot = _single_snapshot([_asset("PSA-1", cost="100")], [])

    assert snapshot.status == PortfolioNavStatus.INSUFFICIENT_DATA


def test_runtime_session_helper_delegates_to_nav_engine() -> None:
    session = RuntimeSession(imported_records=(_asset("PSA-1", cost="100"),), generated_at=REFERENCE)

    snapshots = session.build_portfolio_nav((_valuation("v1", "PSA-1", "150", source="EBAY_SOLD"),))

    assert len(snapshots) == 1
    assert snapshots[0].total_market_value == Decimal("150.00")


def test_no_mutation() -> None:
    assets = [_asset("PSA-1", cost="100")]
    valuations = [_valuation("v1", "PSA-1", "150", source="EBAY_SOLD")]
    before_assets = deepcopy(assets)
    before_valuations = tuple(valuation.to_dict() for valuation in valuations)

    PortfolioNavEngine().build_snapshots(assets, valuations, reference_datetime=REFERENCE)

    assert assets == before_assets
    assert tuple(valuation.to_dict() for valuation in valuations) == before_valuations


def test_deterministic_replay() -> None:
    assets = [_asset("PSA-1", cost="100")]
    valuations = [_valuation("v1", "PSA-1", "150", source="EBAY_SOLD")]

    first = PortfolioNavEngine().build_snapshots(assets, valuations, reference_datetime=REFERENCE)
    second = PortfolioNavEngine().build_snapshots(assets, valuations, reference_datetime=REFERENCE)

    assert [snapshot.to_dict() for snapshot in first] == [snapshot.to_dict() for snapshot in second]


def _single_snapshot(
    assets: list[dict[str, str | None]],
    valuations: list[ValuationRecord],
    *,
    evidence_batches: list[EbaySoldEvidenceBatch] | None = None,
):
    snapshots = PortfolioNavEngine().build_snapshots(
        assets,
        valuations,
        evidence_batches=evidence_batches or [],
        reference_datetime=REFERENCE,
    )
    assert len(snapshots) == 1
    return snapshots[0]


def _asset(asset_id: str, *, cost: str | None, currency: str = "USD") -> dict[str, str | None]:
    return {
        "asset_id": asset_id,
        "cert_number": asset_id.replace("PSA-", ""),
        "player": "Shohei Ohtani",
        "year": "2018",
        "brand": "Topps Update",
        "card_number": "US1",
        "grade_company": "PSA",
        "grade": "10",
        "cost": cost,
        "currency": currency,
    }


def _valuation(
    valuation_id: str,
    asset_id: str,
    value: str,
    *,
    source: str,
    currency: str = "USD",
    valuation_date: date = date(2026, 7, 10),
) -> ValuationRecord:
    return ValuationRecord(
        valuation_id=valuation_id,
        asset_id=asset_id,
        asset_type="SPORTS_CARD",
        source=source,
        currency=currency,
        valuation_date=valuation_date,
        confidence="HIGH" if source == "EBAY_SOLD" else "LOW",
        market_value=value,
    )


def _evidence(
    evidence_id: str,
    *,
    status: str,
    mismatched_fields: tuple[str, ...] = (),
) -> EbaySoldEvidence:
    return EbaySoldEvidence(
        evidence_id=evidence_id,
        asset_id="PSA-1",
        cert_number="1",
        provider_name="Fixture",
        search_url="https://www.ebay.com/sch/i.html?_nkw=ohtani",
        sold_item_url="https://www.ebay.com/itm/1",
        ebay_item_id="1",
        title="2018 Topps Update Shohei Ohtani US1 PSA 10",
        sold_price="250",
        currency="USD",
        shipping_amount="5",
        sold_date="2026-07-10",
        listing_type="AUCTION",
        best_offer_used=False,
        exact_match=True,
        matched_fields=("YEAR", "SET", "CARD_NUMBER", "SUBJECT", "GRADE_ISSUER", "GRADE"),
        mismatched_fields=mismatched_fields,
        confidence="HIGH",
        status=status,
        reference_datetime=REFERENCE,
        raw_metadata={},
        warnings=(),
    )


def _batch(evidence: EbaySoldEvidence) -> EbaySoldEvidenceBatch:
    return EbaySoldEvidenceBatch(
        asset_id="PSA-1",
        cert_number="1",
        provider_name="Fixture",
        search_url="https://www.ebay.com/sch/i.html?_nkw=ohtani",
        search_queries=("ohtani",),
        evidence=(evidence,),
        generated_at=REFERENCE,
    )
