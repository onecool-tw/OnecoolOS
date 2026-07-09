"""Interactive Onecool OS launcher for beta dogfooding."""

from __future__ import annotations

import csv
import re
from collections.abc import Callable
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

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
WARNING_ROW_PATTERN = re.compile(r"row (?P<row_number>\d+)")
SKIPPED_WARNING_PREFIXES = (
    "Duplicate PSA cert number",
    "Unsupported grader",
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
        for line in psa_import_diagnostic_lines(psa_path, result):
            self._output(line)

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


def psa_import_diagnostic_lines(
    csv_path: Path,
    result: PSAImportResult,
) -> tuple[str, ...]:
    """Return safe, deterministic PSA import diagnostic output."""

    summary = result.summary
    warnings = tuple(summary.warnings)
    safe_rows = _safe_psa_rows_by_number(csv_path)
    lines = [
        f"Total rows detected: {result.audit.total_rows}",
        f"Imported cards: {summary.imported_rows}",
        f"Skipped rows: {summary.skipped_rows}",
        f"Warnings: {len(warnings)}",
        "Skipped row details:",
    ]
    skipped_warnings = tuple(
        warning
        for warning in warnings
        if warning.startswith(SKIPPED_WARNING_PREFIXES)
    )
    lines.extend(_detail_lines(skipped_warnings, safe_rows))
    lines.append("Warning details:")
    lines.extend(_detail_lines(warnings, safe_rows))
    return tuple(lines)


def _detail_lines(
    warnings: tuple[str, ...],
    safe_rows: dict[int, dict[str, str]],
) -> list[str]:
    if not warnings:
        return ["- None"]
    return [
        _safe_warning_detail_line(warning, safe_rows)
        for warning in warnings
    ]


def _safe_warning_detail_line(
    warning: str,
    safe_rows: dict[int, dict[str, str]],
) -> str:
    row_number = _warning_row_number(warning)
    row = safe_rows.get(row_number, {})
    parts = [
        f"row {row_number}" if row_number else "row unknown",
        f"item: {_safe_value(row.get('Item'))}",
        f"cert: {_safe_value(row.get('Cert Number'))}",
        f"grade issuer: {_safe_value(row.get('Grade Issuer'))}",
        f"reason: {warning}",
    ]
    return "- " + " | ".join(parts)


def _warning_row_number(warning: str) -> int | None:
    match = WARNING_ROW_PATTERN.search(warning)
    if match is None:
        return None
    return int(match.group("row_number"))


def _safe_psa_rows_by_number(csv_path: Path) -> dict[int, dict[str, str]]:
    try:
        text = csv_path.read_bytes().decode("utf-8-sig")
        reader = csv.DictReader(text.splitlines())
        return {
            row_number: _safe_psa_row(row)
            for row_number, row in enumerate(reader, start=2)
        }
    except (OSError, UnicodeDecodeError, csv.Error):
        return {}


def _safe_psa_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        "Item": _safe_value(row.get("Item")),
        "Cert Number": _safe_value(row.get("Cert Number")),
        "Grade Issuer": _safe_value(row.get("Grade Issuer")),
    }


def _safe_value(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()
