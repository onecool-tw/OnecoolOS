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


def test_missing_beta_data_handled(tmp_path: Path) -> None:
    output: list[str] = []
    launcher = OnecoolLauncher(
        input_func=_inputs("2", "3", "4", "5", "0"),
        output_func=output.append,
        cwd=tmp_path,
    )

    result = launcher.run()

    assert result == 0
    assert output.count(MISSING_BETA_DATA_MESSAGE) == 4


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
