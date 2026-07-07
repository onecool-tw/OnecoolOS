import csv
import json
from datetime import datetime
from datetime import timezone
from pathlib import Path

from onecool_os.connectors import ImportAudit
from onecool_os.connectors.collectibles import CardLadderManualImporter
from onecool_os.connectors.collectibles import CollectibleMarketRecord
from onecool_os.connectors.collectibles import CollectibleMarketSource
from onecool_os.connectors.collectibles import source_role_for_source


REFERENCE = datetime(2026, 7, 5, tzinfo=timezone.utc)


def test_card_ladder_valid_csv_import(tmp_path: Path) -> None:
    path = write_csv(tmp_path, [card_ladder_row()])

    result = CardLadderManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.imported_rows == 1
    assert result.summary.invalid_rows == 0
    assert isinstance(result.records[0], CollectibleMarketRecord)
    assert result.records[0].source == CollectibleMarketSource.CARD_LADDER
    assert result.records[0].external_id == "CL-001"
    assert result.records[0].sale_price is not None
    assert result.records[0].raw_payload["source_role"] == (
        "VALIDATION_SOURCE"
    )


def test_card_ladder_valid_json_import(tmp_path: Path) -> None:
    path = tmp_path / "card_ladder.json"
    path.write_text(
        json.dumps({"records": [card_ladder_row(external_id="CL-JSON-1")]}),
        encoding="utf-8",
    )

    result = CardLadderManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.imported_rows == 1
    assert result.records[0].external_id == "CL-JSON-1"
    assert result.records[0].currency == "USD"


def test_card_ladder_missing_valuation(tmp_path: Path) -> None:
    result = import_one(tmp_path, valuation_value="", market_value="")

    assert result.summary.imported_rows == 0
    assert result.summary.invalid_rows == 1
    assert "valuation_value" in result.summary.warnings[0]


def test_card_ladder_missing_currency(tmp_path: Path) -> None:
    result = import_one(tmp_path, currency="")

    assert result.summary.invalid_rows == 1
    assert "currency" in result.summary.warnings[0]


def test_card_ladder_missing_date(tmp_path: Path) -> None:
    result = import_one(tmp_path, valuation_date="")

    assert result.summary.invalid_rows == 1
    assert "valuation_date" in result.summary.warnings[0]


def test_card_ladder_missing_asset(tmp_path: Path) -> None:
    result = import_one(
        tmp_path,
        asset_id="",
        player="",
        year="",
        brand="",
        card_number="",
        grade_company="",
        grade="",
        title="",
        asset_hint="",
    )

    assert result.summary.invalid_rows == 1
    assert "asset_id or asset_hint" in result.summary.warnings[0]


def test_card_ladder_missing_external_id_or_url(tmp_path: Path) -> None:
    result = import_one(tmp_path, external_id="", url="", reference="")

    assert result.summary.invalid_rows == 1
    assert "external_id or url/reference" in result.summary.warnings[0]


def test_card_ladder_invalid_date(tmp_path: Path) -> None:
    result = import_one(tmp_path, valuation_date="not-a-date")

    assert result.summary.invalid_rows == 1
    assert "valuation_date" in result.summary.warnings[0]


def test_card_ladder_negative_valuation(tmp_path: Path) -> None:
    result = import_one(tmp_path, valuation_value="-1")

    assert result.summary.invalid_rows == 1
    assert "valuation_value" in result.summary.warnings[0]


def test_card_ladder_duplicate_external_id(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        [
            card_ladder_row(external_id="DUP-1"),
            card_ladder_row(external_id="DUP-1"),
        ],
    )

    result = CardLadderManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.imported_rows == 1
    assert result.summary.duplicate_rows == 1
    assert result.summary.skipped_rows == 1
    assert "Duplicate Card Ladder external_id" in result.summary.warnings[0]


def test_card_ladder_duplicate_url(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        [
            card_ladder_row(
                external_id="CL-1",
                url="https://example.test/card-ladder/1",
            ),
            card_ladder_row(
                external_id="CL-2",
                url="https://example.test/card-ladder/1",
            ),
        ],
    )

    result = CardLadderManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.imported_rows == 1
    assert result.summary.duplicate_rows == 1
    assert "Duplicate Card Ladder url/reference" in (
        result.summary.warnings[0]
    )


def test_card_ladder_import_summary(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        [
            card_ladder_row(external_id="CL-1"),
            card_ladder_row(external_id="CL-1"),
            card_ladder_row(valuation_value=""),
        ],
    )

    result = CardLadderManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.to_dict() == {
        "imported_rows": 1,
        "skipped_rows": 1,
        "duplicate_rows": 1,
        "invalid_rows": 1,
        "warnings": [
            "Duplicate Card Ladder external_id at row 3: CL-1",
            "Missing Card Ladder value at row 4: valuation_value",
        ],
    }


def test_card_ladder_import_audit(tmp_path: Path) -> None:
    path = write_csv(tmp_path, [card_ladder_row()])

    result = CardLadderManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert isinstance(result.audit, ImportAudit)
    assert result.audit.source == "CARD_LADDER"
    assert result.audit.source_filename == "card_ladder.csv"
    assert result.audit.total_rows == 1
    assert result.audit.imported_rows == 1
    assert result.audit.checksum is not None
    assert "raw_payload" not in result.audit.to_dict()


def test_card_ladder_deterministic_replay(tmp_path: Path) -> None:
    path = write_csv(tmp_path, [card_ladder_row()])
    importer = CardLadderManualImporter()

    first = importer.import_file(path, reference_datetime=REFERENCE).to_dict()
    second = importer.import_file(path, reference_datetime=REFERENCE).to_dict()

    assert first == second


def test_card_ladder_no_mutation(tmp_path: Path) -> None:
    path = write_csv(tmp_path, [card_ladder_row()])
    before = path.read_text(encoding="utf-8")

    CardLadderManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert path.read_text(encoding="utf-8") == before


def test_card_ladder_collectible_market_record_output(
    tmp_path: Path,
) -> None:
    path = write_csv(
        tmp_path,
        [
            card_ladder_row(
                population="120",
                sales_count="18",
                raw_payload='{"index": "ladder"}',
                note="Manual export",
                tags="card-ladder,validation",
            )
        ],
    )

    result = CardLadderManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )
    record = result.records[0]

    assert record.to_dict()["source"] == "CARD_LADDER"
    assert record.raw_payload["valuation_value"] == "315.00"
    assert record.raw_payload["population"] == "120"
    assert record.raw_payload["sales_count"] == "18"
    assert record.raw_payload["note"] == "Manual export"
    assert record.raw_payload["tags"] == ["card-ladder", "validation"]
    assert record.raw_payload["index"] == "ladder"


def test_card_ladder_source_role_is_validation_source() -> None:
    assert source_role_for_source(
        CollectibleMarketSource.CARD_LADDER
    ).value == "VALIDATION_SOURCE"


def import_one(tmp_path: Path, **overrides):
    path = write_csv(tmp_path, [card_ladder_row(**overrides)])
    return CardLadderManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )


def write_csv(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "card_ladder.csv"
    columns = [
        "external_id",
        "asset_id",
        "asset_hint",
        "valuation_value",
        "market_value",
        "currency",
        "valuation_date",
        "source",
        "url",
        "reference",
        "title",
        "player",
        "year",
        "brand",
        "card_number",
        "grade_company",
        "grade",
        "population",
        "sales_count",
        "card_ladder_value",
        "raw_payload",
        "note",
        "tags",
    ]
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


def card_ladder_row(
    *,
    external_id: str = "CL-001",
    asset_id: str = "CARD-GOLDEN-OHTANI-US1-PSA10",
    asset_hint: str = "",
    valuation_value: str = "315.00",
    market_value: str = "",
    currency: str = "USD",
    valuation_date: str = "2026-07-04",
    source: str = "CARD_LADDER",
    url: str = "https://example.test/card-ladder/CL-001",
    reference: str = "",
    title: str = "2018 Topps Update Shohei Ohtani US1 PSA 10",
    player: str = "Shohei Ohtani",
    year: str = "2018",
    brand: str = "Topps Update",
    card_number: str = "US1",
    grade_company: str = "PSA",
    grade: str = "10",
    population: str = "",
    sales_count: str = "",
    card_ladder_value: str = "",
    raw_payload: str = "",
    note: str = "",
    tags: str = "",
) -> dict[str, str]:
    return {
        "external_id": external_id,
        "asset_id": asset_id,
        "asset_hint": asset_hint,
        "valuation_value": valuation_value,
        "market_value": market_value,
        "currency": currency,
        "valuation_date": valuation_date,
        "source": source,
        "url": url,
        "reference": reference,
        "title": title,
        "player": player,
        "year": year,
        "brand": brand,
        "card_number": card_number,
        "grade_company": grade_company,
        "grade": grade,
        "population": population,
        "sales_count": sales_count,
        "card_ladder_value": card_ladder_value,
        "raw_payload": raw_payload,
        "note": note,
        "tags": tags,
    }

