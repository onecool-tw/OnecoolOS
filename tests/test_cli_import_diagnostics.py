from pathlib import Path

from onecool_os.cli.launcher import DEFAULT_PSA_COLLECTION_PATH
from onecool_os.cli.launcher import OnecoolLauncher


def test_skipped_row_details_shown(tmp_path: Path) -> None:
    _write_psa_collection(
        tmp_path,
        [
            _psa_row(cert_number="12345678"),
            _psa_row(
                item="1996 Demo Insert Michael Jordan J23",
                cert_number="23456789",
                grade_issuer="SGC",
            ),
        ],
    )
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=output.append,
        cwd=tmp_path,
    ).run()

    assert "Skipped rows: 1" in output
    assert "Skipped row details:" in output
    assert any(
        "row 3 | item: 1996 Demo Insert Michael Jordan J23"
        " | cert: 23456789 | grade issuer: SGC"
        " | reason: Unsupported grader at row 3: SGC"
        == line.removeprefix("- ")
        for line in output
    )


def test_warning_details_shown(tmp_path: Path) -> None:
    _write_psa_collection(
        tmp_path,
        [
            _psa_row(cert_number="12345678"),
            _psa_row(
                item="2020 Demo Tribute Kobe Bryant KB24",
                cert_number="34567890",
                grade="11",
            ),
        ],
    )
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=output.append,
        cwd=tmp_path,
    ).run()

    assert "Warnings: 1" in output
    assert "Warning details:" in output
    assert any(
        "row 3 | item: 2020 Demo Tribute Kobe Bryant KB24"
        " | cert: 34567890 | grade issuer: PSA"
        " | reason: Invalid PSA grade at row 3: 11"
        == line.removeprefix("- ")
        for line in output
    )


def test_private_notes_not_printed(tmp_path: Path) -> None:
    private_note = "private vault shelf and owner note"
    _write_psa_collection(
        tmp_path,
        [
            _psa_row(cert_number="12345678"),
            _psa_row(cert_number="45678901", grade="11", notes=private_note),
        ],
    )
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=output.append,
        cwd=tmp_path,
    ).run()

    assert private_note not in "\n".join(output)


def test_total_row_count_shown(tmp_path: Path) -> None:
    _write_psa_collection(
        tmp_path,
        [
            _psa_row(cert_number="12345678"),
            _psa_row(cert_number="23456789"),
            _psa_row(cert_number="34567890"),
        ],
    )
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=output.append,
        cwd=tmp_path,
    ).run()

    assert "Total rows detected: 3" in output


def test_existing_import_still_works(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_psa_row(cert_number="12345678")])
    output: list[str] = []

    result = OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=output.append,
        cwd=tmp_path,
    ).run()

    assert result == 0
    assert "Imported cards: 1" in output
    assert "Skipped rows: 0" in output
    assert "Warnings: 0" in output


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


def _psa_row(
    *,
    item: str = "2018 Topps Update Shohei Ohtani US1",
    cert_number: str,
    grade_issuer: str = "PSA",
    grade: str = "10",
    notes: str = "Dogfooding sample",
) -> dict[str, str]:
    return {
        "Item": item,
        "Subject": "Shohei Ohtani",
        "Year": "2018",
        "Set": "Topps Update",
        "Card Number": "US1",
        "Grade Issuer": grade_issuer,
        "Grade": grade,
        "Cert Number": cert_number,
        "My Cost": "120.00",
        "Date Acquired": "2026-06-01",
        "Source": "PSA Collection",
        "My Notes": notes,
    }
