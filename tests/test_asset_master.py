from __future__ import annotations

import zipfile
from datetime import datetime
from datetime import timezone
from pathlib import Path

from onecool_os.assets.master import AssetMasterLoader
from onecool_os.assets.master import AssetMasterRecord
from onecool_os.assets.master import merge_asset_master

REFERENCE = datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc)
VALID_EBAY_URL = "https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1"
VALID_PSA_URL = "https://www.psacard.com/cert/12345678"


def test_valid_csv_load(tmp_path: Path) -> None:
    csv_path = _write_asset_master_csv(
        tmp_path,
        [
            {
                "Cert Number": "12345678",
                "Card Name": "Shohei Ohtani US1",
                "eBay Sold Search URL": VALID_EBAY_URL,
                "PSA URL": VALID_PSA_URL,
                "REF Score": "88",
                "Watch Status": "Watch",
                "Target Price": "250",
                "Notes": "Review comps weekly",
            }
        ],
    )

    result = AssetMasterLoader().load(
        csv_path,
        reference_datetime=REFERENCE,
    )

    assert len(result.records) == 1
    assert result.records[0].cert_number == "12345678"
    assert result.records[0].ref_score == 88
    assert result.errors == ()
    assert result.source_file == str(csv_path)


def test_valid_xlsx_load(tmp_path: Path) -> None:
    xlsx_path = tmp_path / "asset_master.xlsx"
    _write_simple_xlsx(
        xlsx_path,
        [
            ["Cert Number", "Card Name", "PSA URL"],
            ["12345678", "Shohei Ohtani US1", VALID_PSA_URL],
        ],
    )

    result = AssetMasterLoader().load(
        xlsx_path,
        reference_datetime=REFERENCE,
    )

    assert len(result.records) == 1
    assert result.records[0].cert_number == "12345678"
    assert result.records[0].card_name == "Shohei Ohtani US1"
    assert result.errors == ()


def test_duplicate_cert_detection(tmp_path: Path) -> None:
    csv_path = _write_asset_master_csv(
        tmp_path,
        [
            {"Cert Number": "12345678", "Card Name": "First"},
            {"Cert Number": "12345678", "Card Name": "Second"},
        ],
    )

    result = AssetMasterLoader().load(
        csv_path,
        reference_datetime=REFERENCE,
    )

    assert result.duplicate_cert_numbers == ("12345678",)
    assert any("Duplicate cert number" in warning for warning in result.warnings)
    assert any(
        "Conflicting duplicate metadata" in error for error in result.errors
    )


def test_missing_cert_number(tmp_path: Path) -> None:
    csv_path = _write_asset_master_csv(
        tmp_path,
        [{"Cert Number": "", "Card Name": "Missing Cert"}],
    )

    result = AssetMasterLoader().load(
        csv_path,
        reference_datetime=REFERENCE,
    )

    assert result.records == ()
    assert any("cert_number is required" in error for error in result.errors)


def test_valid_ebay_sold_url(tmp_path: Path) -> None:
    csv_path = _write_asset_master_csv(
        tmp_path,
        [{"Cert Number": "12345678", "eBay Sold Search URL": VALID_EBAY_URL}],
    )

    result = AssetMasterLoader().load(
        csv_path,
        reference_datetime=REFERENCE,
    )

    assert len(result.records) == 1
    assert result.errors == ()


def test_invalid_ebay_url(tmp_path: Path) -> None:
    csv_path = _write_asset_master_csv(
        tmp_path,
        [
            {
                "Cert Number": "12345678",
                "eBay Sold Search URL": "https://www.ebay.com/sch/i.html?_nkw=ohtani",
            }
        ],
    )

    result = AssetMasterLoader().load(
        csv_path,
        reference_datetime=REFERENCE,
    )

    assert result.records == ()
    assert any("LH_Sold=1" in error for error in result.errors)


def test_valid_psa_url(tmp_path: Path) -> None:
    csv_path = _write_asset_master_csv(
        tmp_path,
        [{"Cert Number": "12345678", "PSA URL": VALID_PSA_URL}],
    )

    result = AssetMasterLoader().load(
        csv_path,
        reference_datetime=REFERENCE,
    )

    assert len(result.records) == 1
    assert result.errors == ()


def test_deterministic_merge() -> None:
    imported = [_imported_record()]
    master = [_asset_master_record()]

    first = merge_asset_master(imported, master)
    second = merge_asset_master(imported, master)

    assert first == second


def test_identity_fields_not_overwritten() -> None:
    imported = [_imported_record()]
    master = [
        AssetMasterRecord(
            cert_number="12345678",
            card_name="Different Display Name",
            grade_issuer="BGS",
            grade="9.5",
            imported_at=REFERENCE,
        )
    ]

    enriched = merge_asset_master(imported, master)[0]

    assert enriched["player"] == "Shohei Ohtani"
    assert enriched["grade_company"] == "PSA"
    assert enriched["grade"] == "10"
    assert enriched["cert_number"] == "12345678"
    assert enriched["asset_master"]["card_name"] == "Different Display Name"


def test_metadata_enrichment() -> None:
    enriched = merge_asset_master([_imported_record()], [_asset_master_record()])[0]

    assert enriched["asset_master"]["ebay_sold_search_url"] == VALID_EBAY_URL
    assert enriched["asset_master"]["psa_url"] == VALID_PSA_URL
    assert enriched["asset_master"]["metadata"]["Custom Field"] == "Custom"


def test_cost_override_remains_explicit() -> None:
    imported = [_imported_record()]
    master = [
        AssetMasterRecord(
            cert_number="12345678",
            cost_override="95",
            cost_currency="USD",
            imported_at=REFERENCE,
        )
    ]

    enriched = merge_asset_master(imported, master)[0]

    assert enriched["cost"] == "120"
    assert enriched["asset_master_cost_override"] == {
        "amount": "95",
        "currency": "USD",
    }
    assert enriched["cost_override_applied"] is False


def test_merge_does_not_mutate_inputs() -> None:
    imported = [_imported_record()]
    master = [_asset_master_record()]
    before = [dict(imported[0])]

    merge_asset_master(imported, master)

    assert imported == before


def test_private_file_paths_are_ignored_by_git_rules() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "imports/**/*.csv" in gitignore
    assert "imports/**/*.xlsx" in gitignore


def test_invalid_target_price_and_ref_score(tmp_path: Path) -> None:
    csv_path = _write_asset_master_csv(
        tmp_path,
        [
            {
                "Cert Number": "12345678",
                "Target Price": "-1",
                "REF Score": "-2",
            }
        ],
    )

    result = AssetMasterLoader().load(
        csv_path,
        reference_datetime=REFERENCE,
    )

    assert result.records == ()
    assert any("Invalid target_price" in error for error in result.errors)


def _asset_master_record() -> AssetMasterRecord:
    return AssetMasterRecord(
        cert_number="12345678",
        ebay_sold_search_url=VALID_EBAY_URL,
        psa_url=VALID_PSA_URL,
        metadata={"Custom Field": "Custom"},
        imported_at=REFERENCE,
    )


def _imported_record() -> dict[str, str]:
    return {
        "asset_id": "PSA-12345678",
        "cert_number": "12345678",
        "player": "Shohei Ohtani",
        "year": "2018",
        "set": "Topps Update",
        "card_number": "US1",
        "grade_company": "PSA",
        "grade": "10",
        "cost": "120",
        "currency": "USD",
    }


def _write_asset_master_csv(
    tmp_path: Path,
    rows: list[dict[str, str]],
) -> Path:
    path = tmp_path / "asset_master.csv"
    columns = [
        "Cert Number",
        "Card Name",
        "Grade Issuer",
        "Grade",
        "Cost Override",
        "Cost Currency",
        "eBay Sold Search URL",
        "PSA URL",
        "REF Score",
        "Watch Status",
        "Target Price",
        "Notes",
    ]
    lines = [",".join(columns)]
    for row in rows:
        lines.append(",".join(row.get(column, "") for column in columns))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_simple_xlsx(path: Path, rows: list[list[str]]) -> None:
    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cell_ref = f"{_column_name(column_index)}{row_index}"
            cells.append(
                f'<c r="{cell_ref}" t="inlineStr"><is><t>{value}</t></is></c>'
            )
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        "</worksheet>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "")
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name
