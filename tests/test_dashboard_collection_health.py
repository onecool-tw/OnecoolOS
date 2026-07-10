from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from datetime import timezone
from pathlib import Path

from onecool_os.assets.master import AssetMasterRecord
from onecool_os.cli.launcher import DEFAULT_PSA_COLLECTION_PATH
from onecool_os.cli.launcher import OnecoolLauncher
from onecool_os.dashboard import CollectibleDashboardBuilder
from onecool_os.dashboard import collection_health_lines
from onecool_os.dashboard import collection_health_section
from onecool_os.runtime import RuntimeSession

REFERENCE = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
VALID_EBAY_URL = "https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1"
VALID_PSA_URL = "https://www.psacard.com/cert/12345678"


def test_healthy_collection() -> None:
    runtime = RuntimeSession(
        imported_records=(_imported_record(),),
        asset_master_records=(_master_record(),),
        generated_at=REFERENCE,
    )

    content = collection_health_section(runtime).content

    assert content["runtime_state"] == "HEALTHY"
    assert content["collection_health_score"] == 100
    assert content["total_differences"] == 0
    assert content["critical_issues"] == 0


def test_degraded_collection() -> None:
    runtime = RuntimeSession(
        imported_records=(_imported_record(),),
        asset_master_records=(
            _master_record(
                ebay_sold_search_url=None,
                psa_url=None,
                target_price=None,
            ),
        ),
        generated_at=REFERENCE,
    )

    content = collection_health_section(runtime).content

    assert content["runtime_state"] == "DEGRADED"
    assert content["metadata_issues"] == 3
    assert content["difference_summary"]["EBAY_URL_MISSING"] == 1


def test_critical_collection() -> None:
    runtime = RuntimeSession(
        imported_records=(_imported_record(grade="10"),),
        asset_master_records=(_master_record(grade="9"),),
        generated_at=REFERENCE,
    )

    content = collection_health_section(runtime).content

    assert content["runtime_state"] == "CRITICAL"
    assert content["collection_health_score"] == 0
    assert content["critical_issues"] == 1


def test_no_asset_master() -> None:
    runtime = RuntimeSession(
        imported_records=(_imported_record(),),
        asset_master_records=(),
        generated_at=REFERENCE,
    )

    lines = collection_health_lines(runtime)

    assert "Asset Master Records: 0" in lines
    assert "Asset Master not loaded. Collection integrity comparison is limited." in lines


def test_no_sync_report() -> None:
    lines = collection_health_lines(None)
    section = collection_health_section(None)

    assert "Collection Sync has not run yet." in lines
    assert section.content["message"] == "Collection Sync has not run yet."


def test_mixed_difference_types() -> None:
    runtime = RuntimeSession(
        imported_records=(
            _imported_record(cert_number="12345678", grade="10"),
            _imported_record(cert_number="87654321", asset_id="PSA-87654321"),
            _imported_record(cert_number="87654321", asset_id="PSA-DUP"),
        ),
        asset_master_records=(
            _master_record(cert_number="12345678", grade="9"),
            _master_record(
                cert_number="99999999",
                metadata={"subject": "Michael Jordan"},
            ),
        ),
        generated_at=REFERENCE,
    )

    summary = collection_health_section(runtime).content["difference_summary"]

    assert summary["GRADE_CHANGED"] == 1
    assert summary["DUPLICATE_CERT"] == 1
    assert summary["MISSING_IN_IMPORT"] == 1
    assert summary["MISSING_IN_ASSET_MASTER"] >= 1


def test_private_notes_not_displayed() -> None:
    runtime = RuntimeSession(
        imported_records=(_imported_record(notes="PRIVATE IMPORT NOTE"),),
        asset_master_records=(_master_record(notes="PRIVATE MASTER NOTE"),),
        generated_at=REFERENCE,
    )

    lines = collection_health_lines(runtime)
    details = collection_health_section(runtime).content["issue_details"]

    assert "PRIVATE IMPORT NOTE" not in "\n".join(lines)
    assert "PRIVATE MASTER NOTE" not in "\n".join(lines)
    assert "PRIVATE IMPORT NOTE" not in str(details)
    assert "PRIVATE MASTER NOTE" not in str(details)
    assert any(item["difference_type"] == "NOTES_CHANGED" for item in details)


def test_deterministic_output() -> None:
    runtime = RuntimeSession(
        imported_records=(_imported_record(),),
        asset_master_records=(),
        generated_at=REFERENCE,
    )

    assert collection_health_lines(runtime) == collection_health_lines(runtime)
    assert collection_health_section(runtime).to_dict() == (
        collection_health_section(runtime).to_dict()
    )


def test_no_mutation() -> None:
    imported = [_imported_record()]
    master = [_master_record()]
    before_imported = deepcopy(imported)
    before_metadata = deepcopy(master[0].metadata)
    runtime = RuntimeSession(
        imported_records=imported,
        asset_master_records=master,
        generated_at=REFERENCE,
    )

    collection_health_lines(runtime)
    collection_health_section(runtime)

    assert imported == before_imported
    assert master[0].metadata == before_metadata


def test_sync_not_recalculated() -> None:
    runtime = RuntimeSession(
        imported_records=(_imported_record(),),
        asset_master_records=(),
        generated_at=REFERENCE,
    )
    sync_report = runtime.sync_report

    collection_health_lines(runtime)
    collection_health_section(runtime)

    assert runtime.sync_report is sync_report


def test_collectible_dashboard_builder_integration() -> None:
    runtime = RuntimeSession(
        imported_records=(_imported_record(),),
        asset_master_records=(),
        generated_at=REFERENCE,
    )

    dashboard = CollectibleDashboardBuilder().build(runtime_session=runtime)
    section = next(
        section
        for section in dashboard.sections
        if section.section_id == "collection-health"
    )

    assert section.title == "Collection Health"
    assert section.content["runtime_state"] == "DEGRADED"


def test_cli_option_two_displays_collection_health(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_row(player="Shohei Ohtani", cert_number="PSA0001")])
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "2", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()

    assert "Collection Health" in output
    assert "Runtime State: DEGRADED" in output
    assert "Asset Master not loaded. Collection integrity comparison is limited." in output


def _inputs(*values: str):
    iterator = iter(values)

    def _input(_: str) -> str:
        return next(iterator)

    return _input


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
        grade_issuer="PSA",
        grade=grade,
        ebay_sold_search_url=ebay_sold_search_url,
        psa_url=psa_url,
        target_price=target_price,
        notes=notes,
        metadata=base_metadata,
        imported_at=REFERENCE,
    )


def _write_psa_collection(
    tmp_path: Path,
    rows: list[dict[str, str]],
) -> Path:
    csv_path = tmp_path / DEFAULT_PSA_COLLECTION_PATH
    csv_path.parent.mkdir(parents=True)
    columns = (
        "Item",
        "Subject",
        "Year",
        "Set",
        "Card Number",
        "Grade Issuer",
        "Grade",
        "Cert Number",
        "My Cost",
        "Date Acquired",
        "Source",
        "My Notes",
    )
    lines = [",".join(columns)]
    for row in rows:
        lines.append(",".join(row[column] for column in columns))
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path


def _row(
    *,
    player: str,
    cert_number: str,
) -> dict[str, str]:
    return {
        "Item": f"Demo Card {player}",
        "Subject": player,
        "Year": "2018",
        "Set": "Demo Set",
        "Card Number": "1",
        "Grade Issuer": "PSA",
        "Grade": "10",
        "Cert Number": cert_number,
        "My Cost": "120.00",
        "Date Acquired": "2026-06-01",
        "Source": "PSA Collection",
        "My Notes": "Runtime dashboard sample",
    }
