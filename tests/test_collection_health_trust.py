from __future__ import annotations

from datetime import datetime
from datetime import timezone

from onecool_os.assets.master import AssetMasterRecord
from onecool_os.sync import compare_collection
from onecool_os.sync import sync_report_lines

REFERENCE = datetime(2026, 7, 13, 9, 0, tzinfo=timezone.utc)
VALID_EBAY_URL = "https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1"
VALID_PSA_URL = "https://www.psacard.com/cert/12345678"


def test_identity_critical_issues_drive_trust_state() -> None:
    report = compare_collection(
        [_imported_record(grade="10")],
        [_master_record(grade="9")],
        reference_datetime=REFERENCE,
    )

    difference = _first_difference(report, "GRADE_CHANGED")

    assert difference.trust_category == "IDENTITY"
    assert difference.severity == "CRITICAL"
    assert report.health_state == "CRITICAL"
    assert report.health_components["identity_integrity"]["weight"] == "50%"
    assert report.issue_groups["IDENTITY"]["issue_count"] == 1


def test_normalization_difference_is_low_impact() -> None:
    report = compare_collection(
        [_imported_record(parallel="Refractor")],
        [_master_record(metadata={"parallel": "Base"})],
        reference_datetime=REFERENCE,
    )

    difference = _first_difference(report, "VARIETY_CHANGED")

    assert difference.trust_category == "NORMALIZATION"
    assert difference.severity == "LOW"
    assert report.collection_health == 100
    assert report.health_state == "EXCELLENT"
    assert report.issue_groups["NORMALIZATION"]["issue_count"] == 1


def test_metadata_completeness_does_not_create_critical_health() -> None:
    report = compare_collection(
        [_imported_record()],
        [_master_record(psa_url=None)],
        reference_datetime=REFERENCE,
    )

    difference = _first_difference(report, "PSA_URL_MISSING")

    assert difference.trust_category == "METADATA"
    assert difference.severity == "LOW"
    assert report.collection_health == 98
    assert report.health_state == "EXCELLENT"
    assert report.issue_groups["METADATA"]["recommended_action"] == (
        "Complete durable Asset Master metadata."
    )


def test_decision_metadata_does_not_reduce_collection_health() -> None:
    report = compare_collection(
        [_imported_record(notes="Imported note")],
        [
            _master_record(
                target_price=None,
                notes="Master note",
                cost_override="90",
            )
        ],
        reference_datetime=REFERENCE,
    )

    decision_types = {
        difference.difference_type
        for difference in report.differences
        if difference.trust_category == "DECISION"
    }

    assert {"TARGET_PRICE_MISSING", "NOTES_CHANGED", "COST_OVERRIDE"} <= decision_types
    assert report.collection_health == 100
    assert report.issue_groups["DECISION"]["issue_count"] == 3


def test_evidence_readiness_is_separate_from_identity() -> None:
    report = compare_collection(
        [_imported_record()],
        [_master_record(ebay_sold_search_url=None)],
        reference_datetime=REFERENCE,
    )

    difference = _first_difference(report, "EBAY_URL_MISSING")

    assert difference.trust_category == "EVIDENCE"
    assert report.health_components["evidence_readiness"]["weight"] == "10%"
    assert report.collection_health == 99
    assert report.issue_groups["EVIDENCE"]["issue_count"] == 1


def test_health_report_is_grouped() -> None:
    report = compare_collection(
        [_imported_record(parallel="Refractor")],
        [_master_record(ebay_sold_search_url=None, psa_url=None, metadata={"parallel": "Base"})],
        reference_datetime=REFERENCE,
    )

    lines = sync_report_lines(report)

    assert "Health Report" in lines
    assert "Identity" in lines
    assert "Normalization" in lines
    assert "Metadata" in lines
    assert "Decision" in lines
    assert "Evidence" in lines


def test_known_alias_style_normalization_prevents_false_identity_issue() -> None:
    report = compare_collection(
        [
            _imported_record(
                player=" Shohei Ohtani ",
                set_name="topps update",
            )
        ],
        [
            _master_record(
                metadata={
                    "subject": "SHOHEI OHTANI",
                    "set": "Topps Update",
                }
            )
        ],
        reference_datetime=REFERENCE,
    )

    assert "PLAYER_CHANGED" not in _difference_types(report)
    assert "SET_CHANGED" not in _difference_types(report)
    assert report.collection_health == 100


def test_player_mismatch_is_identity_issue() -> None:
    report = compare_collection(
        [_imported_record(player="Shohei Ohtani")],
        [_master_record(metadata={"subject": "Michael Jordan"})],
        reference_datetime=REFERENCE,
    )

    difference = _first_difference(report, "PLAYER_CHANGED")

    assert difference.trust_category == "IDENTITY"
    assert report.health_state == "CRITICAL"


def _first_difference(report, difference_type: str):
    return next(
        difference
        for difference in report.differences
        if difference.difference_type == difference_type
    )


def _difference_types(report) -> set[str]:
    return {difference.difference_type for difference in report.differences}


def _imported_record(
    *,
    cert_number: str = "12345678",
    asset_id: str | None = None,
    grade: str = "10",
    grade_company: str = "PSA",
    notes: str = "",
    parallel: str = "",
    player: str = "Shohei Ohtani",
    set_name: str = "Topps Update",
) -> dict[str, str]:
    return {
        "asset_id": asset_id or f"PSA-{cert_number}",
        "cert_number": cert_number,
        "year": "2018",
        "set": set_name,
        "card_number": "US1",
        "player": player,
        "grade_company": grade_company,
        "grade": grade,
        "parallel": parallel,
        "cost": "120",
        "notes": notes,
    }


def _master_record(
    *,
    cert_number: str = "12345678",
    grade_issuer: str = "PSA",
    grade: str = "10",
    ebay_sold_search_url: str | None = VALID_EBAY_URL,
    psa_url: str | None = VALID_PSA_URL,
    target_price: str | None = "250",
    notes: str | None = None,
    cost_override: str | None = None,
    metadata: dict[str, str] | None = None,
) -> AssetMasterRecord:
    base_metadata = {
        "year": "2018",
        "set": "Topps Update",
        "card_number": "US1",
        "subject": "Shohei Ohtani",
    }
    if metadata is not None:
        base_metadata.update(metadata)
    return AssetMasterRecord(
        cert_number=cert_number,
        grade_issuer=grade_issuer,
        grade=grade,
        ebay_sold_search_url=ebay_sold_search_url,
        psa_url=psa_url,
        target_price=target_price,
        notes=notes,
        cost_override=cost_override,
        metadata=base_metadata,
        imported_at=REFERENCE,
    )
