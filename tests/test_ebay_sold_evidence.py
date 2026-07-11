from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from datetime import datetime
from datetime import timezone
from pathlib import Path

import pytest

from onecool_os.runtime import RuntimeSession
from onecool_os.valuation.evidence import EbaySoldEvidence
from onecool_os.valuation.evidence import EbaySoldEvidenceBatch
from onecool_os.valuation.evidence import EbaySoldEvidenceJsonLoader
from onecool_os.valuation.evidence import EbaySoldEvidenceMapper
from onecool_os.valuation.evidence import EvidenceError
from onecool_os.valuation.evidence import EvidenceStatus

REFERENCE = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)


def test_valid_verified_evidence() -> None:
    evidence = _evidence()

    assert evidence.status == EvidenceStatus.VERIFIED
    assert evidence.sold_price is not None
    assert evidence.currency == "USD"
    assert evidence.warnings == ()


def test_missing_sold_url_is_rejected() -> None:
    evidence = _evidence(sold_item_url=None)

    assert evidence.status == EvidenceStatus.REJECTED
    assert "Missing Sold URL" in evidence.warnings


def test_missing_item_id_is_rejected() -> None:
    evidence = _evidence(ebay_item_id=None)

    assert evidence.status == EvidenceStatus.REJECTED
    assert "Missing Item ID" in evidence.warnings


def test_missing_sold_date_is_rejected() -> None:
    evidence = _evidence(sold_date=None)

    assert evidence.status == EvidenceStatus.REJECTED
    assert "Malformed Date" in evidence.warnings


def test_active_listing_is_rejected() -> None:
    evidence = _evidence(raw_metadata={"listing_status": "ACTIVE"})

    assert evidence.status == EvidenceStatus.REJECTED
    assert "Active Listing Used" in evidence.warnings


def test_grade_mismatch_is_rejected() -> None:
    evidence = _evidence(mismatched_fields=["GRADE"])

    assert evidence.status == EvidenceStatus.REJECTED
    assert "Grade Mismatch" in evidence.warnings


def test_grade_issuer_mismatch_is_rejected() -> None:
    evidence = _evidence(mismatched_fields=["GRADE_ISSUER"])

    assert evidence.status == EvidenceStatus.REJECTED
    assert "Grade Issuer Mismatch" in evidence.warnings


def test_variety_mismatch_is_rejected() -> None:
    evidence = _evidence(mismatched_fields=["VARIETY"])

    assert evidence.status == EvidenceStatus.REJECTED
    assert "Parallel Mismatch" in evidence.warnings


def test_bgs_black_label_mismatch_is_rejected() -> None:
    evidence = _evidence(
        raw_metadata={"special_designation_expected": "Black Label"},
    )

    assert evidence.status == EvidenceStatus.REJECTED
    assert "Black Label Mismatch" in evidence.warnings


def test_best_offer_unknown_needs_review() -> None:
    evidence = _evidence(
        listing_type="BEST_OFFER",
        best_offer_used=True,
        raw_metadata={"best_offer_price_confirmed": False},
    )

    assert evidence.status == EvidenceStatus.NEEDS_REVIEW
    assert "Best Offer Price Unconfirmed" in evidence.warnings


def test_low_confidence_single_comp_needs_review() -> None:
    batch = EbaySoldEvidenceBatch(
        asset_id="PSA-123",
        cert_number="123",
        provider_name="fixture",
        search_url="https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1",
        search_queries=["ohtani psa 10"],
        evidence=[_evidence()],
        generated_at=REFERENCE,
    )

    assert batch.evidence[0].status == EvidenceStatus.NEEDS_REVIEW
    assert "Only One Sold Comp" in batch.evidence[0].warnings


def test_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "ebay_sold_evidence.json"
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(EvidenceError, match="Invalid eBay Sold evidence JSON"):
        EbaySoldEvidenceJsonLoader().load(path)


def test_valid_json_load(tmp_path: Path) -> None:
    path = tmp_path / "ebay_sold_evidence.json"
    payload = {
        "batches": [
            {
                "asset_id": "PSA-123",
                "cert_number": "123",
                "provider_name": "fixture",
                "search_url": "https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1",
                "search_queries": ["ohtani psa 10"],
                "evidence": [_evidence().to_dict(), _evidence(evidence_id="ev-2").to_dict()],
                "warnings": ["provider warning"],
                "generated_at": REFERENCE.isoformat(),
            }
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = EbaySoldEvidenceJsonLoader().load(path)

    assert len(result.batches) == 1
    assert result.batches[0].evidence[0].status == EvidenceStatus.VERIFIED
    assert result.warnings == ("provider warning",)


def test_evidence_batch_attachment() -> None:
    runtime = RuntimeSession(
        imported_records=(_imported_record(),),
        generated_at=REFERENCE,
    )
    batch = _batch()

    updated = runtime.attach_ebay_evidence_batch(batch)

    assert runtime.ebay_sold_evidence_batches == ()
    assert updated.ebay_sold_evidence_batches == (batch,)
    assert len(updated.verified_ebay_sold_evidence()) == 2


def test_verified_evidence_mapping() -> None:
    mapping = EbaySoldEvidenceMapper().map_evidence(_evidence())

    assert mapping.valuation_record.source.value == "EBAY_SOLD"
    assert mapping.valuation_record.market_value is not None
    assert mapping.metadata["source_role"] == "PRIMARY_MARKET_PRICE"
    assert mapping.metadata["evidence_id"] == "ev-1"


def test_review_evidence_cannot_auto_map() -> None:
    evidence = _evidence(raw_metadata={"title_ambiguous": True})

    with pytest.raises(EvidenceError, match="Only VERIFIED"):
        EbaySoldEvidenceMapper().map_evidence(evidence)


def test_rejected_evidence_cannot_map() -> None:
    evidence = _evidence(mismatched_fields=["SUBJECT"])

    with pytest.raises(EvidenceError, match="Only VERIFIED"):
        EbaySoldEvidenceMapper().map_evidence(evidence)


def test_runtime_review_and_rejected_helpers() -> None:
    batch = EbaySoldEvidenceBatch(
        asset_id="PSA-123",
        cert_number="123",
        provider_name="fixture",
        search_url="https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1",
        search_queries=["ohtani psa 10"],
        evidence=[
            _evidence(raw_metadata={"title_ambiguous": True}),
            _evidence(evidence_id="ev-bad", mismatched_fields=["GRADE"]),
        ],
        generated_at=REFERENCE,
    )
    runtime = RuntimeSession(
        imported_records=(_imported_record(),),
        ebay_sold_evidence_batches=(batch,),
        generated_at=REFERENCE,
    )

    assert len(runtime.review_required_ebay_evidence()) == 1
    assert len(runtime.rejected_ebay_evidence()) == 1


def test_evidence_coverage() -> None:
    runtime = RuntimeSession(
        imported_records=(
            _imported_record(asset_id="PSA-123"),
            _imported_record(asset_id="PSA-999", cert_number="999"),
        ),
        ebay_sold_evidence_batches=(_batch(),),
        generated_at=REFERENCE,
    )

    assert runtime.ebay_evidence_coverage() == {
        "total_assets": 2,
        "covered_assets": 1,
        "missing_assets": 1,
    }


def test_deterministic_replay() -> None:
    first = _batch().to_dict()
    second = _batch().to_dict()

    assert first == second


def test_no_mutation() -> None:
    payload = _evidence().to_dict()
    before = deepcopy(payload)

    EbaySoldEvidence(**payload)

    assert payload == before


def test_private_evidence_files_ignored() -> None:
    result = subprocess.run(
        ["git", "check-ignore", "-q", "imports/valuation/ebay_sold_evidence.json"],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
    )

    assert result.returncode == 0


def _batch() -> EbaySoldEvidenceBatch:
    return EbaySoldEvidenceBatch(
        asset_id="PSA-123",
        cert_number="123",
        provider_name="fixture",
        search_url="https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1",
        search_queries=["ohtani psa 10"],
        evidence=(_evidence(), _evidence(evidence_id="ev-2", ebay_item_id="item-2")),
        generated_at=REFERENCE,
    )


def _evidence(**overrides) -> EbaySoldEvidence:
    payload = {
        "evidence_id": "ev-1",
        "asset_id": "PSA-123",
        "cert_number": "123",
        "provider_name": "fixture",
        "search_url": "https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1",
        "sold_item_url": "https://www.ebay.com/itm/item-1",
        "ebay_item_id": "item-1",
        "title": "2018 Topps Update US1 Shohei Ohtani PSA 10",
        "sold_price": "250.00",
        "currency": "USD",
        "shipping_amount": "5.00",
        "sold_date": "2026-07-01",
        "listing_type": "AUCTION",
        "best_offer_used": False,
        "exact_match": True,
        "matched_fields": [
            "YEAR",
            "SET",
            "CARD_NUMBER",
            "SUBJECT",
            "GRADE_ISSUER",
            "GRADE",
        ],
        "mismatched_fields": [],
        "confidence": "HIGH",
        "status": "VERIFIED",
        "collected_at": REFERENCE.isoformat(),
        "reference_datetime": REFERENCE.isoformat(),
        "raw_metadata": {},
        "warnings": [],
    }
    payload.update(overrides)
    if payload.get("raw_metadata", {}).get("special_designation_expected"):
        payload["matched_fields"] = [
            field
            for field in payload["matched_fields"]
            if field != "SPECIAL_DESIGNATION"
        ]
    return EbaySoldEvidence(**payload)


def _imported_record(
    *,
    asset_id: str = "PSA-123",
    cert_number: str = "123",
) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "cert_number": cert_number,
        "year": "2018",
        "set": "Topps Update",
        "card_number": "US1",
        "player": "Shohei Ohtani",
        "grade_company": "PSA",
        "grade": "10",
    }
