from __future__ import annotations

import zipfile
from datetime import datetime
from datetime import timezone
from html import escape
from pathlib import Path

from onecool_os.cli.launcher import DEFAULT_ASSET_MASTER_CSV_PATH
from onecool_os.cli.launcher import DEFAULT_ASSET_MASTER_XLSX_PATH
from onecool_os.cli.launcher import DEFAULT_PSA_COLLECTION_PATH
from onecool_os.cli.launcher import OnecoolLauncher

REFERENCE = datetime(2026, 7, 10, 13, 0, tzinfo=timezone.utc)
VALID_EBAY_URL = "https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1"
VALID_PSA_URL = "https://www.psacard.com/cert/PSA0001"


def test_xlsx_asset_master_loads_after_collection_import(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_psa_row(cert_number="PSA0001")])
    _write_asset_master_xlsx(
        tmp_path,
        [_asset_master_row(cert_number="PSA0001")],
    )
    output: list[str] = []

    launcher = OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    )
    launcher.run()

    assert "Status: Loaded" in output
    assert "Records Loaded: 1" in output
    assert launcher._runtime_session is not None
    assert len(launcher._runtime_session.asset_master_records) == 1
    assert len(launcher._runtime_session.enriched_runtime_assets) == 1
    assert launcher._runtime_session.sync_report.matched_records == 1


def test_csv_fallback_loads(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_psa_row(cert_number="PSA0001")])
    _write_asset_master_csv(
        tmp_path,
        [_asset_master_row(cert_number="PSA0001")],
    )
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()

    assert "Status: Loaded" in output
    assert f"Source File: {tmp_path / DEFAULT_ASSET_MASTER_CSV_PATH}" in output


def test_xlsx_preferred_when_both_exist(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_psa_row(cert_number="PSA0001")])
    _write_asset_master_csv(
        tmp_path,
        [_asset_master_row(cert_number="CSVONLY")],
    )
    _write_asset_master_xlsx(
        tmp_path,
        [_asset_master_row(cert_number="PSA0001")],
    )
    output: list[str] = []

    launcher = OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    )
    launcher.run()

    assert f"Source File: {tmp_path / DEFAULT_ASSET_MASTER_XLSX_PATH}" in output
    assert "Both Asset Master XLSX and CSV found; using XLSX." in "\n".join(output)
    assert launcher._runtime_session.sync_report.matched_records == 1


def test_no_asset_master_continues_safely(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_psa_row(cert_number="PSA0001")])
    output: list[str] = []

    launcher = OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    )
    launcher.run()

    assert "Status: Not Found" in output
    assert (
        "Asset Master not found. Runtime will continue with collection data only."
        in output
    )
    assert launcher._runtime_session is not None
    assert launcher._runtime_session.sync_report.imported_records == 1


def test_malformed_asset_master_does_not_destroy_collection_session(
    tmp_path: Path,
) -> None:
    _write_psa_collection(tmp_path, [_psa_row(cert_number="PSA0001")])
    asset_master_path = tmp_path / DEFAULT_ASSET_MASTER_XLSX_PATH
    asset_master_path.parent.mkdir(parents=True)
    asset_master_path.write_text("not a valid xlsx", encoding="utf-8")
    output: list[str] = []

    launcher = OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    )
    launcher.run()

    assert "Status: Failed" in output
    assert "Imported Cards: 1" in output
    assert launcher._runtime_session is not None
    assert launcher._runtime_session.imported_records
    assert launcher._runtime_session.asset_master_records == ()


def test_duplicate_cert_warnings_displayed(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_psa_row(cert_number="PSA0001")])
    _write_asset_master_csv(
        tmp_path,
        [
            _asset_master_row(cert_number="PSA0001", card_name="First"),
            _asset_master_row(cert_number="PSA0001", card_name="Second"),
        ],
    )
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()

    assert "Duplicate Cert Numbers: 1" in output
    assert "Asset Master Warning Details:" in output


def test_runtime_session_contains_enriched_assets(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_psa_row(cert_number="PSA0001")])
    _write_asset_master_csv(
        tmp_path,
        [_asset_master_row(cert_number="PSA0001", ref_score="88")],
    )

    launcher = OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=lambda _: None,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    )
    launcher.run()

    enriched = launcher._runtime_session.enriched_runtime_assets[0]
    assert enriched["asset_master"]["ref_score"] == 88
    assert launcher._runtime_session.collection_health <= 100


def test_sync_report_generated(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_psa_row(cert_number="PSA0001")])
    _write_asset_master_csv(
        tmp_path,
        [_asset_master_row(cert_number="PSA0001")],
    )

    launcher = OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=lambda _: None,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    )
    launcher.run()

    assert launcher._runtime_session.sync_report.generated_at == REFERENCE
    assert launcher._runtime_session.collection_health == 100


def test_dashboard_reuses_session(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_psa_row(cert_number="PSA0001")])
    asset_master_path = _write_asset_master_csv(
        tmp_path,
        [_asset_master_row(cert_number="PSA0001")],
    )
    output: list[str] = []

    def _input_sequence():
        values = iter(("1", "2", "0"))
        called = {"count": 0}

        def _input(_: str) -> str:
            value = next(values)
            called["count"] += 1
            if called["count"] == 2:
                asset_master_path.write_text("broken after import", encoding="utf-8")
            return value

        return _input

    OnecoolLauncher(
        input_func=_input_sequence(),
        output_func=output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()

    assert "Asset Master Records: 1" in output
    assert "Runtime State: HEALTHY" in output


def test_asset_master_is_not_reloaded_by_dashboard(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_psa_row(cert_number="PSA0001")])
    asset_master_path = _write_asset_master_csv(
        tmp_path,
        [_asset_master_row(cert_number="PSA0001")],
    )
    launcher = OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=lambda _: None,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    )
    launcher.run()
    asset_master_path.write_text("broken after import", encoding="utf-8")
    output: list[str] = []
    launcher._output = output.append

    launcher.show_dashboard()

    assert "Asset Master Records: 1" in output
    assert "Runtime State: HEALTHY" in output


def test_no_mutation(tmp_path: Path) -> None:
    psa_path = _write_psa_collection(tmp_path, [_psa_row(cert_number="PSA0001")])
    master_path = _write_asset_master_csv(
        tmp_path,
        [_asset_master_row(cert_number="PSA0001")],
    )
    before_psa = psa_path.read_bytes()
    before_master = master_path.read_bytes()

    OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=lambda _: None,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()

    assert psa_path.read_bytes() == before_psa
    assert master_path.read_bytes() == before_master


def test_deterministic_replay(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_psa_row(cert_number="PSA0001")])
    _write_asset_master_csv(
        tmp_path,
        [_asset_master_row(cert_number="PSA0001")],
    )
    first_output: list[str] = []
    second_output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=first_output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()
    OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=second_output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()

    assert first_output == second_output


def test_private_notes_not_displayed(tmp_path: Path) -> None:
    private_note = "PRIVATE ASSET MASTER NOTE"
    _write_psa_collection(tmp_path, [_psa_row(cert_number="PSA0001")])
    _write_asset_master_csv(
        tmp_path,
        [_asset_master_row(cert_number="PSA0001", notes=private_note)],
    )
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "2", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()

    assert private_note not in "\n".join(output)


def test_local_private_files_remain_ignored_by_git() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "imports/**/*.csv" in gitignore
    assert "imports/**/*.xlsx" in gitignore


def _inputs(*values: str):
    iterator = iter(values)

    def _input(_: str) -> str:
        return next(iterator)

    return _input


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


def _write_asset_master_csv(
    tmp_path: Path,
    rows: list[dict[str, str]],
) -> Path:
    path = tmp_path / DEFAULT_ASSET_MASTER_CSV_PATH
    path.parent.mkdir(parents=True)
    columns = _asset_master_columns()
    lines = [",".join(columns)]
    for row in rows:
        lines.append(",".join(row.get(column, "") for column in columns))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_asset_master_xlsx(
    tmp_path: Path,
    rows: list[dict[str, str]],
) -> Path:
    path = tmp_path / DEFAULT_ASSET_MASTER_XLSX_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = _asset_master_columns()
    xlsx_rows = [columns]
    xlsx_rows.extend([[row.get(column, "") for column in columns] for row in rows])
    _write_simple_xlsx(path, xlsx_rows)
    return path


def _psa_row(cert_number: str) -> dict[str, str]:
    return {
        "Item": "2018 Topps Update Shohei Ohtani US1",
        "Subject": "Shohei Ohtani",
        "Year": "2018",
        "Set": "Topps Update",
        "Card Number": "US1",
        "Grade Issuer": "PSA",
        "Grade": "10",
        "Cert Number": cert_number,
        "My Cost": "120.00",
        "Date Acquired": "2026-06-01",
        "Source": "PSA Collection",
        "My Notes": "Runtime import sample",
    }


def _asset_master_row(
    *,
    cert_number: str,
    card_name: str = "Shohei Ohtani US1",
    ref_score: str = "",
    notes: str = "",
) -> dict[str, str]:
    return {
        "Cert Number": cert_number,
        "Card Name": card_name,
        "Grade Issuer": "PSA",
        "Grade": "10",
        "eBay Sold Search URL": VALID_EBAY_URL,
        "PSA URL": VALID_PSA_URL,
        "REF Score": ref_score,
        "Watch Status": "Watch",
        "Target Price": "250",
        "Notes": notes,
        "year": "2018",
        "set": "Topps Update",
        "card_number": "US1",
        "subject": "Shohei Ohtani",
    }


def _asset_master_columns() -> list[str]:
    return [
        "Cert Number",
        "Card Name",
        "Grade Issuer",
        "Grade",
        "eBay Sold Search URL",
        "PSA URL",
        "REF Score",
        "Watch Status",
        "Target Price",
        "Notes",
        "year",
        "set",
        "card_number",
        "subject",
    ]


def _write_simple_xlsx(path: Path, rows: list[list[str]]) -> None:
    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cell_ref = f"{_column_name(column_index)}{row_index}"
            cells.append(
                f'<c r="{cell_ref}" t="inlineStr"><is><t>'
                f'{escape(value)}</t></is></c>'
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
