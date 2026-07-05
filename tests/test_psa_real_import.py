from copy import deepcopy
from datetime import datetime
from datetime import timezone
from pathlib import Path

from onecool_os.connectors.collectibles import PSACollectionImporter
from onecool_os.connectors.collectibles import PSAImportError
from onecool_os.connectors.import_audit import ImportAudit


REFERENCE = datetime(2026, 7, 5, tzinfo=timezone.utc)


def test_psa_real_import_valid_csv(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path, [psa_row()])

    result = PSACollectionImporter().import_csv(
        csv_path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.imported_rows == 1
    assert result.summary.skipped_rows == 0
    assert result.records[0]["asset_id"] == "PSA-12345678"
    assert result.records[0]["cert_number"] == "12345678"
    assert result.records[0]["grade_company"] == "PSA"
    assert result.records[0]["grade"] == "10"
    assert result.records[0]["matching"]["status"] == "NEW"


def test_psa_real_import_duplicate_cert(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path,
        [psa_row(cert_number="12345678"), psa_row(cert_number="12345678")],
    )

    result = PSACollectionImporter().import_csv(
        csv_path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.imported_rows == 1
    assert result.summary.duplicate_rows == 1
    assert result.summary.skipped_rows == 1
    assert "Duplicate PSA cert number" in result.summary.warnings[0]


def test_psa_real_import_invalid_row(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path, [psa_row(grade="11")])

    result = PSACollectionImporter().import_csv(
        csv_path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.imported_rows == 0
    assert result.summary.invalid_rows == 1
    assert "Invalid PSA grade" in result.summary.warnings[0]


def test_psa_real_import_missing_cert(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path, [psa_row(cert_number="")])

    result = PSACollectionImporter().import_csv(
        csv_path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.imported_rows == 0
    assert result.summary.invalid_rows == 1
    assert "Cert Number" in result.summary.warnings[0]


def test_psa_real_import_missing_required_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "psa.csv"
    csv_path.write_text("Item,Subject\nCard,Player\n", encoding="utf-8")

    try:
        PSACollectionImporter().import_csv(
            csv_path,
            reference_datetime=REFERENCE,
        )
    except PSAImportError as exc:
        assert "Missing PSA CSV column" in str(exc)
    else:
        raise AssertionError("Missing required columns should fail.")


def test_psa_real_import_summary(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path,
        [
            psa_row(cert_number="12345678"),
            psa_row(cert_number="12345678"),
            psa_row(cert_number=""),
            psa_row(cert_number="87654321"),
        ],
    )

    result = PSACollectionImporter().import_csv(
        csv_path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.to_dict() == {
        "imported_rows": 2,
        "skipped_rows": 1,
        "duplicate_rows": 1,
        "invalid_rows": 1,
        "warnings": [
            "Duplicate PSA cert number at row 3: 12345678",
            "Missing PSA CSV value at row 4: Cert Number",
        ],
    }


def test_psa_real_import_audit(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path, [psa_row()])

    result = PSACollectionImporter().import_csv(
        csv_path,
        reference_datetime=REFERENCE,
    )

    assert isinstance(result.audit, ImportAudit)
    assert result.audit.source == "PSA Collection CSV"
    assert result.audit.source_filename == "psa.csv"
    assert result.audit.total_rows == 1
    assert result.audit.imported_rows == 1
    assert result.audit.checksum is not None
    assert "raw_payload" not in result.audit.to_dict()


def test_psa_real_import_matching_by_cert(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path, [psa_row(cert_number="12345678")])
    existing = [{"asset_id": "CARD-EXISTING", "cert_number": "12345678"}]

    result = PSACollectionImporter().import_csv(
        csv_path,
        existing_assets=existing,
        reference_datetime=REFERENCE,
    )

    assert result.records[0]["matching"] == {
        "status": "MATCHED",
        "matched_by": "PSA_CERT_NUMBER",
        "matched_asset_id": "CARD-EXISTING",
    }


def test_psa_real_import_matching_by_asset_id(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path, [psa_row(cert_number="12345678")])
    existing = [{"asset_id": "PSA-12345678", "cert_number": "99999999"}]

    result = PSACollectionImporter().import_csv(
        csv_path,
        existing_assets=existing,
        reference_datetime=REFERENCE,
    )

    assert result.records[0]["matching"]["status"] == "MATCHED"
    assert result.records[0]["matching"]["matched_by"] == "ASSET_IDENTIFIER"


def test_psa_real_import_matching_needs_review_for_identity(
    tmp_path: Path,
) -> None:
    csv_path = write_csv(tmp_path, [psa_row(cert_number="12345678")])
    existing = [
        {
            "asset_id": "CARD-OHTANI-OTHER",
            "player": "Shohei Ohtani",
            "year": "2018",
            "set": "Topps Update",
            "card_number": "US1",
            "grade": "10",
        }
    ]

    result = PSACollectionImporter().import_csv(
        csv_path,
        existing_assets=existing,
        reference_datetime=REFERENCE,
    )

    assert result.records[0]["matching"] == {
        "status": "NEEDS_REVIEW",
        "matched_by": "CARD_IDENTITY",
        "matched_asset_id": "CARD-OHTANI-OTHER",
    }


def test_psa_real_import_replay_support(tmp_path: Path) -> None:
    reference = datetime(2026, 8, 1, tzinfo=timezone.utc)
    csv_path = write_csv(tmp_path, [psa_row()])

    result = PSACollectionImporter().import_csv(
        csv_path,
        reference_datetime=reference,
    )

    assert result.audit.reference_datetime == reference
    assert result.audit.imported_at == reference


def test_psa_real_import_is_deterministic(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path, [psa_row()])
    importer = PSACollectionImporter()

    first = importer.import_csv(csv_path, reference_datetime=REFERENCE)
    second = importer.import_csv(csv_path, reference_datetime=REFERENCE)

    assert first.to_dict() == second.to_dict()


def test_psa_real_import_does_not_mutate_source_file(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path, [psa_row()])
    before = csv_path.read_text(encoding="utf-8")

    PSACollectionImporter().import_csv(csv_path, reference_datetime=REFERENCE)

    assert csv_path.read_text(encoding="utf-8") == before


def test_psa_real_import_does_not_mutate_existing_assets(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path, [psa_row()])
    existing = [{"asset_id": "CARD-EXISTING", "cert_number": "99999999"}]
    before = deepcopy(existing)

    PSACollectionImporter().import_csv(
        csv_path,
        existing_assets=existing,
        reference_datetime=REFERENCE,
    )

    assert existing == before


def write_csv(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "psa.csv"
    columns = [
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
    ]
    lines = [",".join(columns)]
    for row in rows:
        lines.append(",".join(row[column] for column in columns))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def psa_row(
    *,
    cert_number: str = "12345678",
    grade: str = "10",
) -> dict[str, str]:
    return {
        "Item": "2018 Topps Update Shohei Ohtani US1",
        "Subject": "Shohei Ohtani",
        "Year": "2018",
        "Set": "Topps Update",
        "Card Number": "US1",
        "Grade Issuer": "PSA",
        "Grade": grade,
        "Cert Number": cert_number,
        "My Cost": "120.00",
        "Date Acquired": "2026-06-01",
        "Source": "PSA Collection",
        "My Notes": "Real import sample",
    }
