from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from datetime import timezone

from onecool_os.assets.master import AssetMasterRecord
from onecool_os.runtime import RuntimeSession

REFERENCE = datetime(2026, 7, 10, 11, 0, tzinfo=timezone.utc)
VALID_EBAY_URL = "https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1"
VALID_PSA_URL = "https://www.psacard.com/cert/12345678"


def test_runtime_initialization() -> None:
    runtime = RuntimeSession(generated_at=REFERENCE)

    assert runtime.imported_records == ()
    assert runtime.asset_master_records == ()
    assert runtime.enriched_runtime_assets == ()
    assert runtime.sync_report.imported_records == 0
    assert runtime.collection_health == 100


def test_runtime_sync_execution() -> None:
    runtime = RuntimeSession(
        imported_records=(_imported_record(),),
        asset_master_records=(_master_record(),),
        generated_at=REFERENCE,
    )

    assert runtime.sync_report.matched_records == 1
    assert runtime.collection_health == 100
    assert runtime.has_sync_issues() is False


def test_runtime_does_not_mutate_imported_records() -> None:
    imported = [_imported_record()]
    before = deepcopy(imported)

    RuntimeSession(
        imported_records=imported,
        asset_master_records=(_master_record(),),
        generated_at=REFERENCE,
    )

    assert imported == before


def test_runtime_health_propagation() -> None:
    runtime = RuntimeSession(
        imported_records=(_imported_record(),),
        asset_master_records=(),
        generated_at=REFERENCE,
    )

    assert runtime.collection_health == runtime.sync_report.collection_health
    assert runtime.collection_health == 68
    assert runtime.sync_report.health_state == "ATTENTION"


def test_runtime_difference_propagation() -> None:
    runtime = RuntimeSession(
        imported_records=(_imported_record(grade="10"),),
        asset_master_records=(_master_record(grade="9"),),
        generated_at=REFERENCE,
    )

    assert runtime.collection_differences() == runtime.sync_report.differences
    assert runtime.has_sync_issues() is True
    assert runtime.has_critical_sync_issues() is True
    assert runtime.critical_sync_issues()[0].difference_type == "GRADE_CHANGED"


def test_runtime_deterministic_replay() -> None:
    first = RuntimeSession(
        imported_records=(_imported_record(),),
        asset_master_records=(_master_record(),),
        generated_at=REFERENCE,
    )
    second = RuntimeSession(
        imported_records=(_imported_record(),),
        asset_master_records=(_master_record(),),
        generated_at=REFERENCE,
    )

    assert first.sync_report.to_dict() == second.sync_report.to_dict()
    assert first.enriched_runtime_assets == second.enriched_runtime_assets


def test_runtime_repeated_imports() -> None:
    runtime = RuntimeSession(
        imported_records=(_imported_record(cert_number="12345678"),),
        asset_master_records=(_master_record(cert_number="12345678"),),
        generated_at=REFERENCE,
    )

    updated = runtime.with_imported_records(
        (
            _imported_record(cert_number="12345678"),
            _imported_record(cert_number="87654321", asset_id="PSA-87654321"),
        )
    )

    assert runtime.sync_report.imported_records == 1
    assert updated.sync_report.imported_records == 2
    assert any(
        difference.difference_type == "MISSING_IN_ASSET_MASTER"
        for difference in updated.collection_differences()
    )


def test_runtime_asset_master_update() -> None:
    runtime = RuntimeSession(
        imported_records=(_imported_record(),),
        asset_master_records=(),
        generated_at=REFERENCE,
    )

    updated = runtime.with_asset_master_records((_master_record(),))

    assert runtime.has_sync_issues() is True
    assert updated.has_sync_issues() is False
    assert updated.collection_health == 100


def test_runtime_empty_collection() -> None:
    runtime = RuntimeSession(
        imported_records=(),
        asset_master_records=(),
        generated_at=REFERENCE,
    )

    assert runtime.collection_health == 100
    assert runtime.collection_differences() == ()


def test_runtime_no_asset_master() -> None:
    runtime = RuntimeSession(
        imported_records=(_imported_record(),),
        asset_master_records=(),
        generated_at=REFERENCE,
    )

    assert runtime.has_sync_issues() is True
    assert runtime.high_priority_sync_issues()
    assert runtime.metadata_sync_issues() == ()


def test_runtime_metadata_sync_helpers() -> None:
    runtime = RuntimeSession(
        imported_records=(_imported_record(notes="Imported"),),
        asset_master_records=(
            _master_record(
                ebay_sold_search_url=None,
                psa_url=None,
                target_price=None,
                notes="Master",
                cost_override="95",
            ),
        ),
        generated_at=REFERENCE,
    )

    metadata_types = {
        difference.difference_type
        for difference in runtime.metadata_sync_issues()
    }
    assert {
        "COST_OVERRIDE",
        "EBAY_URL_MISSING",
        "PSA_URL_MISSING",
        "TARGET_PRICE_MISSING",
        "NOTES_CHANGED",
    } <= metadata_types


def _imported_record(
    *,
    cert_number: str = "12345678",
    asset_id: str | None = None,
    grade: str = "10",
    notes: str = "",
) -> dict[str, str]:
    return {
        "asset_id": asset_id or f"PSA-{cert_number}",
        "cert_number": cert_number,
        "year": "2018",
        "set": "Topps Update",
        "card_number": "US1",
        "player": "Shohei Ohtani",
        "grade_company": "PSA",
        "grade": grade,
        "cost": "120",
        "notes": notes,
    }


def _master_record(
    *,
    cert_number: str = "12345678",
    grade: str = "10",
    ebay_sold_search_url: str | None = VALID_EBAY_URL,
    psa_url: str | None = VALID_PSA_URL,
    target_price: str | None = "250",
    notes: str | None = None,
    cost_override: str | None = None,
) -> AssetMasterRecord:
    return AssetMasterRecord(
        cert_number=cert_number,
        grade_issuer="PSA",
        grade=grade,
        ebay_sold_search_url=ebay_sold_search_url,
        psa_url=psa_url,
        target_price=target_price,
        notes=notes,
        cost_override=cost_override,
        metadata={
            "year": "2018",
            "set": "Topps Update",
            "card_number": "US1",
            "subject": "Shohei Ohtani",
        },
        imported_at=REFERENCE,
    )
