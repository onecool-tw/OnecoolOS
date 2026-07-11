from __future__ import annotations

from copy import deepcopy
from datetime import date
from datetime import datetime
from datetime import timezone

from onecool_os.assets.master import AssetMasterRecord
from onecool_os.portfolio import PortfolioNavEngine
from onecool_os.research import ResearchQueueEngine
from onecool_os.research import ResearchQueuePriority
from onecool_os.research import ResearchQueueReason
from onecool_os.research import ResearchQueueStatus
from onecool_os.research import validate_research_queue_snapshot
from onecool_os.runtime import RuntimeSession
from onecool_os.valuation.evidence import EbaySoldEvidence
from onecool_os.valuation.evidence import EbaySoldEvidenceBatch
from onecool_os.valuation.models import ValuationRecord

REFERENCE = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)


def test_empty_runtime_queue() -> None:
    snapshot = ResearchQueueEngine().build(RuntimeSession(generated_at=REFERENCE))

    assert snapshot.total_assets == 0
    assert snapshot.total_queue_items == 0
    assert snapshot.items == ()
    assert validate_research_queue_snapshot(snapshot).valid


def test_missing_verified_valuation_is_low_for_non_core_asset() -> None:
    snapshot = _snapshot_without_sync([_asset_with_source_url("A-1", "1001")])
    item = snapshot.items[0]

    assert item.priority == ResearchQueuePriority.LOW
    assert item.status == ResearchQueueStatus.READY
    assert ResearchQueueReason.MISSING_VERIFIED_VALUATION in item.reasons
    assert ResearchQueueReason.MISSING_ANY_VALUATION in item.reasons


def test_missing_verified_valuation_is_high_for_core_asset() -> None:
    snapshot = _snapshot(
        [_asset("A-1", "1001", collection_type="Core")],
        [_master("1001")],
    )

    assert snapshot.items[0].priority == ResearchQueuePriority.HIGH
    assert ResearchQueueReason.CORE_HOLDING_RESEARCH in snapshot.items[0].reasons


def test_verified_ebay_valuation_completes_queue_item() -> None:
    snapshot = _snapshot_without_sync(
        [_asset_with_source_url("A-1", "1001")],
        valuations=[_valuation("v1", "A-1", source="EBAY_SOLD")],
    )
    item = snapshot.items[0]

    assert item.priority == ResearchQueuePriority.INFORMATIONAL
    assert item.status == ResearchQueueStatus.COMPLETED
    assert item.valuation_coverage_status == "VERIFIED"


def test_supporting_estimate_only_is_high_priority() -> None:
    assets = [_asset("A-1", "1001", cost="100")]
    valuations = [_valuation("v1", "A-1", source="MANUAL")]
    session = _session(assets, [_master("1001")])
    nav_snapshots = session.build_portfolio_nav(valuations)
    snapshot = ResearchQueueEngine().build(
        session,
        valuation_records=valuations,
        nav_snapshots=nav_snapshots,
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )

    assert snapshot.items[0].priority == ResearchQueuePriority.HIGH
    assert ResearchQueueReason.SUPPORTING_ESTIMATE_ONLY in snapshot.items[0].reasons


def test_multiple_eligible_valuations_are_high_priority() -> None:
    snapshot = _snapshot(
        [_asset("A-1", "1001")],
        [_master("1001")],
        valuations=[
            _valuation("v1", "A-1", value="100", source="EBAY_SOLD"),
            _valuation("v2", "A-1", value="105", source="CARD_LADDER"),
        ],
    )

    assert snapshot.items[0].priority == ResearchQueuePriority.HIGH
    assert ResearchQueueReason.MULTIPLE_ELIGIBLE_VALUATIONS in snapshot.items[0].reasons


def test_evidence_needs_review_is_high_priority() -> None:
    snapshot = _snapshot(
        [_asset("A-1", "1001")],
        [_master("1001")],
        evidence_batches=[_batch("A-1", "1001", _evidence("ev-1", "A-1", "1001", raw_metadata={"title_ambiguous": True}))],
    )

    assert snapshot.items[0].priority == ResearchQueuePriority.HIGH
    assert ResearchQueueReason.EVIDENCE_NEEDS_REVIEW in snapshot.items[0].reasons


def test_rejected_evidence_is_high_priority() -> None:
    snapshot = _snapshot(
        [_asset("A-1", "1001")],
        [_master("1001")],
        evidence_batches=[_batch("A-1", "1001", _evidence("ev-1", "A-1", "1001", mismatched_fields=("GRADE",)))],
    )

    assert snapshot.items[0].priority == ResearchQueuePriority.HIGH
    assert ResearchQueueReason.EVIDENCE_REJECTED in snapshot.items[0].reasons


def test_no_match_evidence_is_high_priority() -> None:
    snapshot = _snapshot(
        [_asset("A-1", "1001")],
        [_master("1001")],
        evidence_batches=[_batch("A-1", "1001", _evidence("ev-1", "A-1", "1001", status="NO_MATCH"))],
    )

    assert snapshot.items[0].priority == ResearchQueuePriority.HIGH
    assert ResearchQueueReason.NO_MATCH in snapshot.items[0].reasons


def test_missing_ebay_url_is_medium_priority() -> None:
    snapshot = _snapshot([_asset("A-1", "1001")], [_master("1001", ebay_url=None)])

    assert snapshot.items[0].priority == ResearchQueuePriority.MEDIUM
    assert snapshot.items[0].status == ResearchQueueStatus.READY
    assert ResearchQueueReason.MISSING_EBAY_SEARCH_URL in snapshot.items[0].reasons


def test_invalid_source_url_blocks_item() -> None:
    snapshot = _snapshot(
        [_asset("A-1", "1001")],
        [_master("1001", ebay_url="not-a-url")],
    )
    item = snapshot.items[0]

    assert item.priority == ResearchQueuePriority.CRITICAL
    assert item.status == ResearchQueueStatus.BLOCKED
    assert "Invalid source URL." in item.blocking_reasons


def test_missing_identity_blocks_item() -> None:
    snapshot = _snapshot([_asset("", "")], [])

    assert snapshot.items[0].priority == ResearchQueuePriority.CRITICAL
    assert snapshot.items[0].status == ResearchQueueStatus.BLOCKED
    assert ResearchQueueReason.AMBIGUOUS_IDENTITY in snapshot.items[0].reasons


def test_duplicate_cert_sync_issue_blocks_item() -> None:
    snapshot = _snapshot(
        [_asset("A-1", "1001"), _asset("A-2", "1001")],
        [_master("1001")],
    )

    assert snapshot.critical_items == 2
    assert all(item.status == ResearchQueueStatus.BLOCKED for item in snapshot.items)


def test_grade_change_sync_issue_blocks_item() -> None:
    snapshot = _snapshot(
        [_asset("A-1", "1001", grade="10")],
        [_master("1001", grade="9")],
    )

    assert snapshot.items[0].priority == ResearchQueuePriority.CRITICAL
    assert ResearchQueueReason.COLLECTION_SYNC_ISSUE in snapshot.items[0].reasons


def test_variety_change_sync_issue_does_not_block_research() -> None:
    snapshot = _snapshot(
        [_asset("A-1", "1001")],
        [_master("1001", metadata={"variety": "Gold"}),],
    )

    assert snapshot.items[0].status == ResearchQueueStatus.READY
    assert snapshot.items[0].priority == ResearchQueuePriority.MEDIUM
    assert ResearchQueueReason.COLLECTION_SYNC_ISSUE in snapshot.items[0].reasons


def test_watchlist_and_target_price_review_are_medium_priority() -> None:
    snapshot = _snapshot(
        [_asset("A-1", "1001")],
        [_master("1001", watch_status="Watch", target_price="250")],
    )

    assert snapshot.items[0].priority == ResearchQueuePriority.MEDIUM
    assert ResearchQueueReason.WATCHLIST_RESEARCH in snapshot.items[0].reasons
    assert ResearchQueueReason.TARGET_PRICE_REVIEW in snapshot.items[0].reasons


def test_manual_research_request_from_metadata() -> None:
    snapshot = _snapshot(
        [_asset("A-1", "1001")],
        [_master("1001", metadata={"manual_research_request": True})],
    )

    assert snapshot.items[0].priority == ResearchQueuePriority.MEDIUM
    assert ResearchQueueReason.MANUAL_RESEARCH_REQUEST in snapshot.items[0].reasons


def test_deduplicates_reasons_and_open_items() -> None:
    snapshot = _snapshot(
        [_asset("A-1", "1001")],
        [_master("1001", ebay_url=None)],
    )
    item = snapshot.items[0]

    assert len(item.reasons) == len(set(item.reasons))
    assert validate_research_queue_snapshot(snapshot).valid


def test_deterministic_priority_ordering() -> None:
    snapshot = _snapshot_without_sync(
        [
            _asset_with_source_url("A-3", "1003"),
            _asset_with_source_url("A-1", "1001", ebay_url="not-a-url"),
            _asset_with_source_url("A-2", "1002", collection_type="Core"),
        ],
    )

    assert [item.asset_id for item in snapshot.items] == ["A-1", "A-2", "A-3"]
    assert [item.priority for item in snapshot.items] == [
        ResearchQueuePriority.CRITICAL,
        ResearchQueuePriority.HIGH,
        ResearchQueuePriority.LOW,
    ]


def test_runtime_session_delegation_helpers() -> None:
    session = _session(
        [_asset("A-1", "1001"), _asset("A-2", "1002")],
        [_master("1001", ebay_url="not-a-url"), _master("1002")],
    )

    assert len(session.open_research_items()) == 2
    assert len(session.blocked_research_items()) == 1
    assert len(session.ready_research_items()) == 1
    assert len(session.critical_research_items()) == 1


def test_no_mutation_of_runtime_or_inputs() -> None:
    imported = [_asset("A-1", "1001")]
    masters = [_master("1001")]
    valuations = [_valuation("v1", "A-1", source="MANUAL")]
    session = _session(imported, masters)
    before_imported = deepcopy(imported)
    before_masters = tuple(record.to_metadata() for record in masters)
    before_session = tuple(dict(record) for record in session.enriched_runtime_assets)
    before_valuations = tuple(valuation.to_dict() for valuation in valuations)

    ResearchQueueEngine().build(session, valuation_records=valuations, reference_datetime=REFERENCE, generated_at=REFERENCE)

    assert imported == before_imported
    assert tuple(record.to_metadata() for record in masters) == before_masters
    assert tuple(dict(record) for record in session.enriched_runtime_assets) == before_session
    assert tuple(valuation.to_dict() for valuation in valuations) == before_valuations


def test_deterministic_replay() -> None:
    session = _session([_asset("A-1", "1001")], [_master("1001")])

    first = ResearchQueueEngine().build(session, reference_datetime=REFERENCE, generated_at=REFERENCE)
    second = ResearchQueueEngine().build(session, reference_datetime=REFERENCE, generated_at=REFERENCE)

    assert first.to_dict() == second.to_dict()


def test_fifty_assets_without_verified_market_values_are_not_all_critical() -> None:
    assets = [_asset_with_source_url(f"A-{index:02d}", f"{1000 + index}") for index in range(50)]

    snapshot = _snapshot_without_sync(assets)

    assert snapshot.total_assets == 50
    assert snapshot.critical_items == 0
    assert snapshot.low_items == 50
    assert snapshot.ready_items == 50


def test_queue_snapshot_validation_detects_duplicate_open_items() -> None:
    session = _session([_asset("A-1", "1001")], [_master("1001")])
    snapshot = ResearchQueueEngine().build(session, reference_datetime=REFERENCE, generated_at=REFERENCE)
    duplicate_snapshot = type(snapshot)(
        **{
            **snapshot.to_dict(),
            "reference_datetime": snapshot.reference_datetime,
            "items": (snapshot.items[0], snapshot.items[0]),
            "generated_at": snapshot.generated_at,
        }
    )

    result = validate_research_queue_snapshot(duplicate_snapshot)

    assert not result.valid
    assert any("Duplicate open research item" in issue.message for issue in result.issues)


def _snapshot(
    assets: list[dict[str, str | None]],
    masters: list[AssetMasterRecord],
    *,
    valuations: list[ValuationRecord] | None = None,
    evidence_batches: list[EbaySoldEvidenceBatch] | None = None,
):
    session = _session(assets, masters, evidence_batches=evidence_batches)
    return ResearchQueueEngine().build(
        session,
        valuation_records=valuations or [],
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )


def _snapshot_without_sync(
    assets: list[dict[str, str | None]],
    *,
    valuations: list[ValuationRecord] | None = None,
):
    runtime = _RuntimeWithoutSync(assets)
    return ResearchQueueEngine().build(
        runtime,
        valuation_records=valuations or [],
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )


def _session(
    assets: list[dict[str, str | None]],
    masters: list[AssetMasterRecord],
    *,
    evidence_batches: list[EbaySoldEvidenceBatch] | None = None,
) -> RuntimeSession:
    return RuntimeSession(
        imported_records=tuple(assets),
        asset_master_records=tuple(masters),
        ebay_sold_evidence_batches=tuple(evidence_batches or ()),
        generated_at=REFERENCE,
    )


def _asset(
    asset_id: str,
    cert_number: str,
    *,
    player: str = "Shohei Ohtani",
    grade: str = "10",
    collection_type: str = "Investment",
    cost: str | None = "100",
) -> dict[str, str | None]:
    return {
        "asset_id": asset_id,
        "cert_number": cert_number,
        "year": "2018",
        "set": "Topps Update",
        "card_number": "US1",
        "player": player,
        "subject": player,
        "grade_company": "PSA",
        "grade_issuer": "PSA",
        "grade": grade,
        "collection_type": collection_type,
        "cost": cost,
        "currency": "USD",
    }


def _asset_with_source_url(
    asset_id: str,
    cert_number: str,
    *,
    ebay_url: str = "https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1",
    collection_type: str = "Investment",
) -> dict[str, str | None]:
    asset = _asset(asset_id, cert_number, collection_type=collection_type)
    asset["ebay_sold_search_url"] = ebay_url
    return asset


def _master(
    cert_number: str,
    *,
    ebay_url: str | None = "https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1",
    grade: str = "10",
    watch_status: str | None = None,
    target_price: str | None = "200",
    metadata: dict | None = None,
) -> AssetMasterRecord:
    return AssetMasterRecord(
        cert_number=cert_number,
        grade_issuer="PSA",
        grade=grade,
        ebay_sold_search_url=ebay_url,
        psa_url=f"https://www.psacard.com/cert/{cert_number}",
        watch_status=watch_status,
        target_price=target_price,
        metadata=metadata or {},
        imported_at=REFERENCE,
    )


def _valuation(
    valuation_id: str,
    asset_id: str,
    *,
    value: str = "150",
    source: str,
) -> ValuationRecord:
    return ValuationRecord(
        valuation_id=valuation_id,
        asset_id=asset_id,
        asset_type="SPORTS_CARD",
        source=source,
        currency="USD",
        valuation_date=date(2026, 7, 10),
        confidence="HIGH" if source == "EBAY_SOLD" else "LOW",
        market_value=value,
    )


def _batch(
    asset_id: str,
    cert_number: str,
    evidence: EbaySoldEvidence,
) -> EbaySoldEvidenceBatch:
    return EbaySoldEvidenceBatch(
        asset_id=asset_id,
        cert_number=cert_number,
        provider_name="fixture",
        search_url="https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1",
        search_queries=("ohtani psa 10",),
        evidence=(evidence,),
        generated_at=REFERENCE,
    )


def _evidence(
    evidence_id: str,
    asset_id: str,
    cert_number: str,
    *,
    status: str = "VERIFIED",
    raw_metadata: dict | None = None,
    mismatched_fields: tuple[str, ...] = (),
) -> EbaySoldEvidence:
    return EbaySoldEvidence(
        evidence_id=evidence_id,
        asset_id=asset_id,
        cert_number=cert_number,
        provider_name="fixture",
        search_url="https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1",
        sold_item_url=f"https://www.ebay.com/itm/{evidence_id}",
        ebay_item_id=evidence_id,
        title="2018 Topps Update Shohei Ohtani US1 PSA 10",
        sold_price="150",
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
        raw_metadata=raw_metadata or {},
        warnings=(),
    )


class _RuntimeWithoutSync:
    def __init__(self, assets: list[dict[str, str | None]]) -> None:
        self.enriched_runtime_assets = tuple(dict(asset) for asset in assets)
        self.ebay_sold_evidence_batches = ()
        self.generated_at = REFERENCE

    def collection_differences(self) -> tuple:
        return ()
