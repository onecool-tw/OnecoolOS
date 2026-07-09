from datetime import datetime
from datetime import timezone
from pathlib import Path

from onecool_os.cli.launcher import DEFAULT_PSA_COLLECTION_PATH
from onecool_os.cli.launcher import OnecoolLauncher

REFERENCE = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)


def test_runtime_context_with_imported_session(tmp_path: Path) -> None:
    _write_psa_collection(
        tmp_path,
        [_row(player="Shohei Ohtani", cert_number="PSA0001")],
    )
    output: list[str] = []

    result = OnecoolLauncher(
        input_func=_inputs("1", "5", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()

    assert result == 0
    assert "Onecool OFAI Context" in output
    assert "Total Cards: 1" in output
    assert "  PSA: 1" in output
    assert "Imported: 1" in output
    assert "Runtime Session Ready" in output
    assert "Not generated." in output
    assert "Context only." in output


def test_runtime_context_without_import(tmp_path: Path) -> None:
    output: list[str] = []

    result = OnecoolLauncher(
        input_func=_inputs("5", "0"),
        output_func=output.append,
        cwd=tmp_path,
    ).run()

    assert result == 0
    assert "No collection has been imported yet." in output
    assert "Please select:" in output
    assert "1. Import PSA Collection" in output


def test_runtime_context_psa_only(tmp_path: Path) -> None:
    _write_psa_collection(
        tmp_path,
        [
            _row(player="Shohei Ohtani", cert_number="PSA0001"),
            _row(player="Shohei Ohtani", cert_number="PSA0002"),
        ],
    )
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "5", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()

    assert "Total Cards: 2" in output
    assert "  PSA: 2" in output
    assert "Critical: 2" in output
    assert "Medium: 4" in output


def test_runtime_context_psa_and_bgs(tmp_path: Path) -> None:
    _write_psa_collection(
        tmp_path,
        [
            _row(player="Shohei Ohtani", cert_number="PSA0001"),
            _row(
                player="Michael Jordan",
                cert_number="BGS0001",
                grade_issuer="BGS",
                grade="9.5",
            ),
        ],
    )
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "5", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()

    assert "Total Cards: 2" in output
    assert "  BGS: 1" in output
    assert "  PSA: 1" in output


def test_runtime_context_output_is_deterministic(tmp_path: Path) -> None:
    _write_psa_collection(
        tmp_path,
        [
            _row(player="Shohei Ohtani", cert_number="PSA0001"),
            _row(
                player="Michael Jordan",
                cert_number="BGS0001",
                grade_issuer="BGS",
            ),
        ],
    )
    first_output: list[str] = []
    second_output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "5", "0"),
        output_func=first_output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()
    OnecoolLauncher(
        input_func=_inputs("1", "5", "0"),
        output_func=second_output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()

    assert _context_lines(first_output) == _context_lines(second_output)


def test_runtime_context_has_no_recommendation_language(tmp_path: Path) -> None:
    _write_psa_collection(
        tmp_path,
        [_row(player="Shohei Ohtani", cert_number="PSA0001")],
    )
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "5", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()

    rendered = "\n".join(_context_lines(output)).lower()
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "recommendation" in rendered
    assert "not generated" in rendered


def test_runtime_context_has_no_prediction_language(tmp_path: Path) -> None:
    _write_psa_collection(
        tmp_path,
        [_row(player="Shohei Ohtani", cert_number="PSA0001")],
    )
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "5", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()

    rendered = "\n".join(_context_lines(output)).lower()
    assert "predict" not in rendered
    assert "prediction" not in rendered


def _inputs(*values: str):
    iterator = iter(values)

    def _input(_: str) -> str:
        return next(iterator)

    return _input


def _context_lines(output: list[str]) -> list[str]:
    start = output.index("=====================================")
    return output[start:]


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
    grade_issuer: str = "PSA",
    grade: str = "10",
) -> dict[str, str]:
    return {
        "Item": f"Demo Card {player}",
        "Subject": player,
        "Year": "2018",
        "Set": "Demo Set",
        "Card Number": "1",
        "Grade Issuer": grade_issuer,
        "Grade": grade,
        "Cert Number": cert_number,
        "My Cost": "120.00",
        "Date Acquired": "2026-06-01",
        "Source": "PSA Collection",
        "My Notes": "Runtime OFAI context sample",
    }
