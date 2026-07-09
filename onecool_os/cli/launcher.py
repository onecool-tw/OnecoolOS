"""Interactive Onecool OS launcher for beta dogfooding."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC
from datetime import datetime
from pathlib import Path

from onecool_os.connectors.collectibles import PSACollectionImporter
from onecool_os.connectors.collectibles import PSAImportError
from onecool_os.connectors.collectibles import PSAImportResult

ONECOOL_VERSION = "v0.4.0-beta"
DEFAULT_PSA_COLLECTION_PATH = Path("imports/psa/collection.csv")
DEFAULT_BETA_DATA_PATH = Path("data/portfolio/sports_cards.json")
MISSING_PSA_MESSAGE = (
    "PSA Collection file not found. Please place CSV at "
    "imports/psa/collection.csv"
)
MISSING_BETA_DATA_MESSAGE = (
    "No local beta data found yet. Please import PSA Collection first."
)


class OnecoolLauncher:
    """Small interactive launcher for local beta dogfooding."""

    def __init__(
        self,
        *,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
        cwd: Path | str = ".",
    ) -> None:
        self._input = input_func
        self._output = output_func
        self._cwd = Path(cwd)
        self._psa_import_result: PSAImportResult | None = None

    def run(self) -> int:
        """Run the interactive launcher loop."""

        running = True
        while running:
            self.render_menu()
            try:
                choice = self._input("Select option: ").strip()
            except EOFError:
                self._output("Exiting Onecool OS.")
                return 0
            running = self.handle_choice(choice)
        return 0

    def render_menu(self) -> None:
        """Render the launcher menu."""

        for line in menu_lines():
            self._output(line)

    def handle_choice(self, choice: str) -> bool:
        """Handle one menu choice.

        Returns ``True`` when the launcher should continue running.
        """

        if choice == "0":
            self._output("Exiting Onecool OS.")
            return False
        if choice == "1":
            self.import_psa_collection()
            return True
        if choice in {"2", "3", "4", "5"}:
            self.show_beta_placeholder(choice)
            return True
        self._output("Unknown option. Please choose 0, 1, 2, 3, 4, or 5.")
        return True

    def import_psa_collection(self) -> None:
        """Handle the PSA Collection launcher option."""

        psa_path = self._cwd / DEFAULT_PSA_COLLECTION_PATH
        if not psa_path.exists():
            self._output(MISSING_PSA_MESSAGE)
            return
        try:
            result = PSACollectionImporter().import_csv(
                psa_path,
                reference_datetime=datetime.now(UTC),
            )
        except PSAImportError as exc:
            self._output(f"PSA import failed: {exc}")
            return

        self._psa_import_result = result
        summary = result.summary
        self._output(f"Imported cards: {summary.imported_rows}")
        self._output(f"Skipped: {summary.skipped_rows}")
        self._output(f"Warnings: {len(summary.warnings)}")

    def show_beta_placeholder(self, choice: str) -> None:
        """Handle placeholder report/dashboard options."""

        data_path = self._cwd / DEFAULT_BETA_DATA_PATH
        if not data_path.exists() and self._psa_import_result is None:
            self._output(MISSING_BETA_DATA_MESSAGE)
            return
        labels = {
            "2": "Dashboard",
            "3": "Daily Radar Report",
            "4": "Decision Queue",
            "5": "OFAI Context",
        }
        self._output(
            f"{labels[choice]} wiring will be available in a future "
            "beta dogfooding sprint."
        )


def menu_lines() -> tuple[str, ...]:
    """Return deterministic launcher menu lines."""

    return (
        f"Onecool OS {ONECOOL_VERSION}",
        "",
        "1. Import PSA Collection",
        "2. Show Dashboard",
        "3. Show Daily Radar Report",
        "4. Show Decision Queue",
        "5. Show OFAI Context",
        "0. Exit",
    )
