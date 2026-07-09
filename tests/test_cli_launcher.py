from pathlib import Path

from onecool_os.cli.launcher import DEFAULT_PSA_COLLECTION_PATH
from onecool_os.cli.launcher import MISSING_BETA_DATA_MESSAGE
from onecool_os.cli.launcher import MISSING_PSA_MESSAGE
from onecool_os.cli.launcher import OnecoolLauncher
from onecool_os.cli.launcher import menu_lines
from onecool_os.cli.main import main


def test_launcher_imports_successfully() -> None:
    assert OnecoolLauncher is not None
    assert callable(main)


def test_menu_renders() -> None:
    assert menu_lines() == (
        "Onecool OS v0.4.0-beta",
        "",
        "1. Import PSA Collection",
        "2. Show Dashboard",
        "3. Show Daily Radar Report",
        "4. Show Decision Queue",
        "5. Show OFAI Context",
        "0. Exit",
    )


def test_exit_works(tmp_path: Path) -> None:
    output: list[str] = []
    launcher = OnecoolLauncher(
        input_func=_inputs("0"),
        output_func=output.append,
        cwd=tmp_path,
    )

    result = launcher.run()

    assert result == 0
    assert output[-1] == "Exiting Onecool OS."


def test_missing_psa_file_handled(tmp_path: Path) -> None:
    output: list[str] = []
    launcher = OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=output.append,
        cwd=tmp_path,
    )

    result = launcher.run()

    assert result == 0
    assert MISSING_PSA_MESSAGE in output


def test_successful_psa_import_prints_summary(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path)
    output: list[str] = []
    launcher = OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=output.append,
        cwd=tmp_path,
    )

    result = launcher.run()

    assert result == 0
    assert "Total rows detected: 1" in output
    assert "Imported cards: 1" in output
    assert "Skipped rows: 0" in output
    assert "Warnings: 0" in output


def test_malformed_psa_csv_prints_error(tmp_path: Path) -> None:
    csv_path = tmp_path / DEFAULT_PSA_COLLECTION_PATH
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text("not,a,psa,csv\n1,2,3,4\n", encoding="utf-8")
    output: list[str] = []
    launcher = OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=output.append,
        cwd=tmp_path,
    )

    result = launcher.run()

    assert result == 0
    assert any(
        line.startswith("PSA import failed: Missing PSA CSV column:")
        for line in output
    )


def test_repeated_psa_import_is_deterministic(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path)
    first_output: list[str] = []
    second_output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=first_output.append,
        cwd=tmp_path,
    ).run()
    OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=second_output.append,
        cwd=tmp_path,
    ).run()

    assert _summary_lines(first_output) == _summary_lines(second_output)


def test_session_import_allows_beta_placeholder(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path)
    output: list[str] = []
    launcher = OnecoolLauncher(
        input_func=_inputs("1", "2", "0"),
        output_func=output.append,
        cwd=tmp_path,
    )

    result = launcher.run()

    assert result == 0
    assert MISSING_BETA_DATA_MESSAGE not in output
    assert "Onecool Collection Dashboard" in output


def test_missing_beta_data_handled(tmp_path: Path) -> None:
    output: list[str] = []
    launcher = OnecoolLauncher(
        input_func=_inputs("2", "3", "4", "5", "0"),
        output_func=output.append,
        cwd=tmp_path,
    )

    result = launcher.run()

    assert result == 0
    assert output.count(MISSING_BETA_DATA_MESSAGE) == 0


def test_launcher_does_not_write_private_data(tmp_path: Path) -> None:
    output: list[str] = []
    launcher = OnecoolLauncher(
        input_func=_inputs("1", "0"),
        output_func=output.append,
        cwd=tmp_path,
    )

    launcher.run()

    assert not (tmp_path / DEFAULT_PSA_COLLECTION_PATH).exists()
    assert not (tmp_path / "data/portfolio/sports_cards.json").exists()


def test_deterministic_menu_output() -> None:
    first: list[str] = []
    second: list[str] = []

    OnecoolLauncher(output_func=first.append).render_menu()
    OnecoolLauncher(output_func=second.append).render_menu()

    assert first == second


def _inputs(*values: str):
    iterator = iter(values)

    def _input(_: str) -> str:
        return next(iterator)

    return _input


def _summary_lines(output: list[str]) -> list[str]:
    return [
        line
        for line in output
        if line.startswith(
            (
                "Total rows detected:",
                "Imported cards:",
                "Skipped rows:",
                "Warnings:",
            )
        )
    ]


def _write_psa_collection(tmp_path: Path) -> Path:
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
    row = (
        "2018 Topps Update Shohei Ohtani US1",
        "Shohei Ohtani",
        "2018",
        "Topps Update",
        "US1",
        "PSA",
        "10",
        "12345678",
        "120.00",
        "2026-06-01",
        "PSA Collection",
        "Launcher import sample",
    )
    csv_path.write_text(
        ",".join(columns) + "\n" + ",".join(row) + "\n",
        encoding="utf-8",
    )
    return csv_path
