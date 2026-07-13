from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from datetime import timezone

from onecool_os.assets.master import AssetMasterRecord
from onecool_os.sync import compare_collection
from onecool_os.sync import sync_report_lines

REFERENCE = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
VALID_EBAY_URL = "https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1"
VALID_PSA_URL = "https://www.psacard.com/cert/12345678"


def test_identical_collections() -> None:
    report = compare_collection(
        [_imported_record()],
        [_master_record()],
        reference_datetime=REFERENCE,
    )

    assert report.imported_records == 1
    assert report.asset_master_records == 1
    assert report.matched_records == 1
    assert report.collection_health == 100
    assert report.differences == ()


def test_missing_cards() -> None:
    report = compare_collection(
        [_imported_record(cert_number="12345678")],
        [],
        reference_datetime=REFERENCE,
    )

    types = _difference_types(report)
    assert "NEW_CARD" in types
    assert "MISSING_IN_ASSET_MASTER" in types
    assert report.collection_health == 68
    assert report.health_state == "ATTENTION"


def test_duplicate_cert() -> None:
    report = compare_collection(
        [
            _imported_record(cert_number="12345678"),
            _imported_record(cert_number="12345678", asset_id="PSA-DUPE"),
        ],
        [_master_record(cert_number="12345678")],
        reference_datetime=REFERENCE,
    )

    difference = _first_difference(report, "DUPLICATE_CERT")
    assert difference.severity == "CRITICAL"
    assert report.health_state == "CRITICAL"
    assert report.collection_health < 70


def test_grade_changed() -> None:
    report = compare_collection(
        [_imported_record(grade="10")],
        [_master_record(grade="9")],
        reference_datetime=REFERENCE,
    )

    difference = _first_difference(report, "GRADE_CHANGED")
    assert difference.severity == "CRITICAL"
    assert difference.source_value == "10"
    assert difference.target_value == "9"
    assert report.health_state == "CRITICAL"
    assert report.collection_health < 70


def test_new_card() -> None:
    report = compare_collection(
        [_imported_record(cert_number="99999999", asset_id="PSA-99999999")],
        [
            _master_record(
                cert_number="12345678",
                metadata={"subject": "Michael Jordan"},
            )
        ],
        reference_datetime=REFERENCE,
    )

    assert "NEW_CARD" in _difference_types(report)
    assert "MISSING_IN_IMPORT" in _difference_types(report)


def test_orphan_asset_master() -> None:
    report = compare_collection(
        [],
        [_master_record(cert_number="12345678")],
        reference_datetime=REFERENCE,
    )

    difference = _first_difference(report, "MISSING_IN_IMPORT")
    assert difference.cert_number == "12345678"
    assert report.collection_health == 68
    assert report.health_state == "ATTENTION"


def test_orphan_import() -> None:
    report = compare_collection(
        [_imported_record(cert_number="12345678")],
        [],
        reference_datetime=REFERENCE,
    )

    difference = _first_difference(report, "MISSING_IN_ASSET_MASTER")
    assert difference.cert_number == "12345678"


def test_metadata_differences() -> None:
    report = compare_collection(
        [_imported_record(notes="Imported note")],
        [
            _master_record(
                ebay_sold_search_url=None,
                psa_url=None,
                target_price=None,
                notes="Master note",
                cost_override="90",
            )
        ],
        reference_datetime=REFERENCE,
    )

    types = _difference_types(report)
    assert "EBAY_URL_MISSING" in types
    assert "PSA_URL_MISSING" in types
    assert "TARGET_PRICE_MISSING" in types
    assert "NOTES_CHANGED" in types
    assert "COST_OVERRIDE" in types
    assert report.collection_health == 97
    assert report.health_state == "EXCELLENT"


def test_deterministic_replay() -> None:
    imported = [_imported_record()]
    master = [_master_record()]

    first = compare_collection(imported, master, reference_datetime=REFERENCE)
    second = compare_collection(imported, master, reference_datetime=REFERENCE)

    assert first.to_dict() == second.to_dict()
    assert sync_report_lines(first) == sync_report_lines(second)


def test_no_mutation() -> None:
    imported = [_imported_record(notes="Imported note")]
    master = [_master_record(notes="Master note")]
    imported_before = deepcopy(imported)
    master_metadata_before = deepcopy(master[0].metadata)

    compare_collection(imported, master, reference_datetime=REFERENCE)

    assert imported == imported_before
    assert master[0].metadata == master_metadata_before


def test_grade_issuer_changed() -> None:
    report = compare_collection(
        [_imported_record(grade_company="PSA")],
        [_master_record(grade_issuer="BGS")],
        reference_datetime=REFERENCE,
    )

    difference = _first_difference(report, "GRADE_ISSUER_CHANGED")
    assert difference.severity == "CRITICAL"


def test_variety_changed() -> None:
    report = compare_collection(
        [_imported_record(parallel="Refractor")],
        [_master_record(metadata={"parallel": "Base"})],
        reference_datetime=REFERENCE,
    )

    difference = _first_difference(report, "VARIETY_CHANGED")
    assert difference.severity == "LOW"
    assert difference.trust_category == "NORMALIZATION"


def test_duplicate_asset() -> None:
    report = compare_collection(
        [
            _imported_record(cert_number="12345678", asset_id="PSA-SAME"),
            _imported_record(cert_number="87654321", asset_id="PSA-SAME"),
        ],
        [
            _master_record(cert_number="12345678"),
            _master_record(cert_number="87654321"),
        ],
        reference_datetime=REFERENCE,
    )

    difference = _first_difference(report, "DUPLICATE_ASSET")
    assert difference.asset_id == "PSA-SAME"
    assert report.health_state == "CRITICAL"
    assert report.collection_health < 70


def test_fallback_identity_match() -> None:
    report = compare_collection(
        [_imported_record(cert_number="IMPORT-CERT")],
        [
            _master_record(
                cert_number="MASTER-CERT",
                metadata={
                    "year": "2018",
                    "set": "Topps Update",
                    "card_number": "US1",
                    "subject": "Shohei Ohtani",
                },
            )
        ],
        reference_datetime=REFERENCE,
    )

    assert report.matched_records == 1
    assert "MISSING_IN_ASSET_MASTER" not in _difference_types(report)


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
) -> dict[str, str]:
    return {
        "asset_id": asset_id or f"PSA-{cert_number}",
        "cert_number": cert_number,
        "year": "2018",
        "set": "Topps Update",
        "card_number": "US1",
        "player": "Shohei Ohtani",
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
