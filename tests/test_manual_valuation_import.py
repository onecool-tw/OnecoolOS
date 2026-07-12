import csv
import json
from datetime import datetime
from datetime import timezone
from pathlib import Path

from onecool_os.connectors import ImportAudit
from onecool_os.valuation import ManualValuationImporter
from onecool_os.valuation import ValuationRecord
from onecool_os.valuation import ValuationSource


REFERENCE = datetime(2026, 7, 5, tzinfo=timezone.utc)


def test_manual_valuation_valid_csv_import(tmp_path: Path) -> None:
    path = write_csv(tmp_path, [valuation_row()])

    result = ManualValuationImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.imported_rows == 1
    assert result.summary.invalid_rows == 0
    assert isinstance(result.records[0].valuation_record, ValuationRecord)
    assert result.records[0].valuation_record.source == ValuationSource.MANUAL
    assert result.records[0].metadata["validation_source"] is True
    assert result.records[0].metadata["primary_market_price"] is False
    assert result.records[0].metadata["source_role"] == "MANUAL_FALLBACK"


def test_manual_valuation_valid_json_import(tmp_path: Path) -> None:
    path = tmp_path / "manual.json"
    path.write_text(
        json.dumps(
            {
                "valuations": [
                    valuation_row(
                        valuation_id="manual-1",
                        market_value="",
                        estimated_value="305.00",
                    )
                ]
            }
        ),
        encoding="utf-8",
    )

    result = ManualValuationImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.imported_rows == 1
    assert result.records[0].valuation_record.valuation_id == "manual-1"
    assert result.records[0].valuation_record.estimated_value is not None


def test_manual_valuation_missing_asset_id(tmp_path: Path) -> None:
    result = import_one(tmp_path, asset_id="")

    assert result.summary.imported_rows == 0
    assert result.summary.invalid_rows == 1
    assert "asset_id" in result.summary.warnings[0]


def test_manual_valuation_missing_currency(tmp_path: Path) -> None:
    result = import_one(tmp_path, currency="")

    assert result.summary.invalid_rows == 1
    assert "currency" in result.summary.warnings[0]


def test_manual_valuation_missing_valuation_date(tmp_path: Path) -> None:
    result = import_one(tmp_path, valuation_date="")

    assert result.summary.invalid_rows == 1
    assert "valuation_date" in result.summary.warnings[0]


def test_manual_valuation_missing_value(tmp_path: Path) -> None:
    result = import_one(tmp_path, market_value="", estimated_value="")

    assert result.summary.invalid_rows == 1
    assert "estimated_value or market_value" in result.summary.warnings[0]


def test_manual_valuation_negative_value(tmp_path: Path) -> None:
    result = import_one(tmp_path, market_value="-10.00")

    assert result.summary.invalid_rows == 1
    assert "market_value" in result.summary.warnings[0]


def test_manual_valuation_invalid_date(tmp_path: Path) -> None:
    result = import_one(tmp_path, valuation_date="not-a-date")

    assert result.summary.invalid_rows == 1
    assert "valuation_date" in result.summary.warnings[0]


def test_manual_valuation_duplicate_valuation_id(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        [
            valuation_row(valuation_id="manual-duplicate"),
            valuation_row(valuation_id="manual-duplicate"),
        ],
    )

    result = ManualValuationImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.imported_rows == 1
    assert result.summary.duplicate_rows == 1
    assert result.summary.skipped_rows == 1
    assert "Duplicate valuation_id" in result.summary.warnings[0]


def test_manual_valuation_import_summary(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        [
            valuation_row(valuation_id="manual-1"),
            valuation_row(valuation_id="manual-1"),
            valuation_row(asset_id=""),
        ],
    )

    result = ManualValuationImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.to_dict() == {
        "imported_rows": 1,
        "skipped_rows": 1,
        "duplicate_rows": 1,
        "invalid_rows": 1,
        "warnings": [
            "Duplicate valuation_id at row 3: manual-1",
            "Missing manual valuation value at row 4: asset_id",
        ],
    }


def test_manual_valuation_import_audit(tmp_path: Path) -> None:
    path = write_csv(tmp_path, [valuation_row()])

    result = ManualValuationImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert isinstance(result.audit, ImportAudit)
    assert result.audit.source == "MANUAL_VALUATION"
    assert result.audit.source_filename == "manual.csv"
    assert result.audit.total_rows == 1
    assert result.audit.imported_rows == 1
    assert result.audit.checksum is not None
    assert "raw_payload" not in result.audit.to_dict()


def test_manual_valuation_injected_reference_datetime(tmp_path: Path) -> None:
    reference = datetime(2026, 8, 1, tzinfo=timezone.utc)
    path = write_csv(tmp_path, [valuation_row()])

    result = ManualValuationImporter().import_file(
        path,
        reference_datetime=reference,
    )

    assert result.audit.reference_datetime == reference
    assert result.audit.imported_at == reference


def test_manual_valuation_no_mutation(tmp_path: Path) -> None:
    path = write_csv(tmp_path, [valuation_row()])
    before = path.read_text(encoding="utf-8")

    ManualValuationImporter().import_file(path, reference_datetime=REFERENCE)

    assert path.read_text(encoding="utf-8") == before


def test_manual_valuation_preserved_as_independent_output(
    tmp_path: Path,
) -> None:
    path = write_csv(
        tmp_path,
        [
            valuation_row(
                valuation_id="manual-independent",
                note="Owner estimate",
                reference="collector spreadsheet",
                tags="manual,review",
                raw_payload='{"source_row": 1}',
            )
        ],
    )

    result = ManualValuationImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )
    record = result.records[0]

    assert record.valuation_record.valuation_id == "manual-independent"
    assert record.valuation_record.source == ValuationSource.MANUAL
    assert record.valuation_record.source_priority == 8
    assert record.valuation_record.note == "Owner estimate"
    assert record.valuation_record.tags == ("manual", "review")
    assert record.metadata["reference"] == "collector spreadsheet"
    assert record.metadata["raw_payload"] == {"source_row": 1}
    assert record.metadata["primary_market_price"] is False


def import_one(tmp_path: Path, **overrides):
    path = write_csv(tmp_path, [valuation_row(**overrides)])
    return ManualValuationImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )


def write_csv(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "manual.csv"
    columns = [
        "valuation_id",
        "asset_id",
        "asset_type",
        "currency",
        "valuation_date",
        "market_value",
        "estimated_value",
        "note",
        "url",
        "reference",
        "tags",
        "raw_payload",
    ]
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


def valuation_row(
    *,
    valuation_id: str = "",
    asset_id: str = "CARD-GOLDEN-OHTANI-US1-PSA10",
    asset_type: str = "SPORTS_CARD",
    currency: str = "USD",
    valuation_date: str = "2026-07-05",
    market_value: str = "300.00",
    estimated_value: str = "",
    note: str = "",
    url: str = "https://example.test/manual/card",
    reference: str = "",
    tags: str = "manual",
    raw_payload: str = "",
) -> dict[str, str]:
    return {
        "valuation_id": valuation_id,
        "asset_id": asset_id,
        "asset_type": asset_type,
        "currency": currency,
        "valuation_date": valuation_date,
        "market_value": market_value,
        "estimated_value": estimated_value,
        "note": note,
        "url": url,
        "reference": reference,
        "tags": tags,
        "raw_payload": raw_payload,
    }
