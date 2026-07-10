"""Interactive Onecool OS launcher for beta dogfooding."""

from __future__ import annotations

import csv
import re
from collections.abc import Callable
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation
from pathlib import Path
from typing import Any

from onecool_os.connectors.collectibles import PSACollectionImporter
from onecool_os.connectors.collectibles import PSAImportError
from onecool_os.connectors.collectibles import PSAImportResult
from onecool_os.valuation.models import ValuationRecord

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
MISSING_COLLECTION_MESSAGE = (
    "No collection has been imported yet.\n"
    "Please select:\n"
    "1. Import PSA Collection"
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
        clock: Callable[[], datetime] | None = None,
        runtime_valuation_records: Sequence[ValuationRecord] | None = None,
        cwd: Path | str = ".",
    ) -> None:
        self._input = input_func
        self._output = output_func
        self._clock = clock or (lambda: datetime.now(UTC))
        self._cwd = Path(cwd)
        self._psa_import_result: PSAImportResult | None = None
        self._runtime_valuation_records = tuple(runtime_valuation_records or ())

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
        if choice == "2":
            self.show_dashboard()
            return True
        if choice == "3":
            self.show_daily_report()
            return True
        if choice == "4":
            self.show_decision_queue()
            return True
        if choice == "5":
            self.show_ofai_context()
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
                reference_datetime=self._clock(),
            )
        except PSAImportError as exc:
            self._output(f"PSA import failed: {exc}")
            return

        self._psa_import_result = result
        self._runtime_valuation_records = _valuation_records_for_import(
            self._runtime_valuation_records,
            result,
        )
        for line in psa_import_diagnostic_lines(psa_path, result):
            self._output(line)

    def show_dashboard(self) -> None:
        """Display the in-memory collection dashboard."""

        if self._psa_import_result is None:
            for line in MISSING_COLLECTION_MESSAGE.splitlines():
                self._output(line)
            return
        for line in collection_dashboard_lines(
            self._psa_import_result,
            self._runtime_valuation_records,
        ):
            self._output(line)

    def show_daily_report(self) -> None:
        """Display the in-memory daily collection report."""

        if self._psa_import_result is None:
            for line in MISSING_COLLECTION_MESSAGE.splitlines():
                self._output(line)
            return
        for line in daily_report_lines(
            self._psa_import_result,
            self._runtime_valuation_records,
        ):
            self._output(line)

    def show_decision_queue(self) -> None:
        """Display the in-memory decision review queue."""

        if self._psa_import_result is None:
            for line in MISSING_COLLECTION_MESSAGE.splitlines():
                self._output(line)
            return
        for line in decision_queue_lines(
            self._psa_import_result,
            self._runtime_valuation_records,
        ):
            self._output(line)

    def show_ofai_context(self) -> None:
        """Display the in-memory OFAI context summary."""

        if self._psa_import_result is None:
            for line in MISSING_COLLECTION_MESSAGE.splitlines():
                self._output(line)
            return
        for line in ofai_context_lines(
            self._psa_import_result,
            self._runtime_valuation_records,
        ):
            self._output(line)

    def attach_runtime_valuations(
        self,
        valuation_records: Sequence[ValuationRecord],
    ) -> None:
        """Attach runtime valuation records to this launcher session."""

        self._runtime_valuation_records = tuple(valuation_records)
        if self._psa_import_result is not None:
            self._runtime_valuation_records = _valuation_records_for_import(
                self._runtime_valuation_records,
                self._psa_import_result,
            )

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


def collection_dashboard_lines(
    result: PSAImportResult,
    valuation_records: Sequence[ValuationRecord] | None = None,
) -> tuple[str, ...]:
    """Return a display-only dashboard from in-memory import data."""

    records = tuple(result.records)
    valuation_lookup = _valuation_lookup(valuation_records)
    cost_by_currency = _sum_by_currency(records, "cost", "currency")
    market_by_currency = _sum_market_values_by_currency(
        records,
        valuation_lookup,
    )
    missing_market_values = sum(
        1
        for record in records
        if _market_value(record, valuation_lookup) is None
    )
    missing_cost_basis = sum(
        1 for record in records if _decimal_value(record.get("cost")) is None
    )
    performance_count = sum(
        1
        for record in records
        if _decimal_value(record.get("cost")) is not None
        and _market_value(record, valuation_lookup) is not None
    )
    lines = [
        "=====================================",
        "Onecool Collection Dashboard",
        "=====================================",
        "",
        "Collection",
        "----------",
        f"Total Cards: {len(records)}",
        "By Grading Company",
    ]
    lines.extend(_count_lines(records, "grade_company"))
    lines.append("By Sport")
    lines.extend(_count_lines(records, "sport", fallback="Other"))
    lines.extend(
        (
            "",
            "Players",
            "-------",
        )
    )
    lines.extend(_players_lines(records))
    lines.extend(
        (
            "",
            "Portfolio",
            "---------",
            "Total Cost Basis (group by currency)",
        )
    )
    lines.extend(_money_lines(cost_by_currency))
    lines.append("Estimated Market Value (if available)")
    lines.extend(_money_lines(market_by_currency))
    lines.extend(
        (
            f"Missing Market Values: {missing_market_values}",
            f"Missing Cost Basis: {missing_cost_basis}",
            "",
            "Performance",
            "-----------",
            f"Cards with Performance Data: {performance_count}",
            f"Cards Missing Performance Data: {len(records) - performance_count}",
            "",
            "Data Quality",
            "------------",
            f"Warnings: {len(result.summary.warnings)}",
            f"Import Time: {result.audit.imported_at.isoformat()}",
            "Last Import Summary",
            f"  Imported: {result.summary.imported_rows}",
            f"  Skipped: {result.summary.skipped_rows}",
            f"  Duplicates: {result.summary.duplicate_rows}",
            f"  Invalid: {result.summary.invalid_rows}",
        )
    )
    return tuple(lines)


def daily_report_lines(
    result: PSAImportResult,
    valuation_records: Sequence[ValuationRecord] | None = None,
) -> tuple[str, ...]:
    """Return a presentation-only daily report from imported session data."""

    records = tuple(result.records)
    valuation_lookup = _valuation_lookup(valuation_records)
    cost_by_currency = _sum_by_currency(records, "cost", "currency")
    market_by_currency = _sum_market_values_by_currency(
        records,
        valuation_lookup,
    )
    missing_market_values = sum(
        1
        for record in records
        if _market_value(record, valuation_lookup) is None
    )
    missing_cost_basis = sum(
        1 for record in records if _decimal_value(record.get("cost")) is None
    )
    performance_count = sum(
        1
        for record in records
        if _decimal_value(record.get("cost")) is not None
        and _market_value(record, valuation_lookup) is not None
    )
    warnings = tuple(result.summary.warnings)
    lines = [
        "=====================================",
        "Onecool Daily Collection Report",
        "=====================================",
        "",
        "Collection Summary",
        "------------------",
        f"Total Cards: {len(records)}",
    ]
    lines.extend(_count_lines(records, "grade_company"))
    lines.extend(
        (
            "",
            "Players",
            "-------",
        )
    )
    lines.extend(_top_player_lines(records))
    lines.extend(
        (
            "",
            "Portfolio Status",
            "----------------",
            "Cost Basis by Currency",
        )
    )
    lines.extend(_money_lines(cost_by_currency))
    lines.append("Estimated Market Value (if available)")
    lines.extend(_money_lines(market_by_currency))
    lines.extend(
        (
            f"Cards Missing Market Value: {missing_market_values}",
            f"Cards Missing Cost Basis: {missing_cost_basis}",
            "",
            "Performance Status",
            "------------------",
            f"Cards with Performance Data: {performance_count}",
            f"Cards Missing Performance Data: {len(records) - performance_count}",
            "",
            "Import Health",
            "-------------",
            f"Import Time: {result.audit.imported_at.isoformat()}",
            f"Imported: {result.summary.imported_rows}",
            f"Skipped: {result.summary.skipped_rows}",
            f"Warnings: {len(warnings)}",
            f"Invalid: {result.summary.invalid_rows}",
            "",
            "Review Needed",
            "-------------",
            f"Missing Cost Basis: {missing_cost_basis}",
            f"Missing Market Value: {missing_market_values}",
            f"Unsupported Metadata: {_unsupported_metadata_count(warnings)}",
            f"Other existing warnings: {_other_warning_count(warnings)}",
        )
    )
    return tuple(lines)


def decision_queue_lines(
    result: PSAImportResult,
    valuation_records: Sequence[ValuationRecord] | None = None,
) -> tuple[str, ...]:
    """Return a presentation-only review queue from imported session data."""

    records = tuple(result.records)
    valuation_lookup = _valuation_lookup(valuation_records)
    warnings = tuple(result.summary.warnings)
    missing_market_values = sum(
        1
        for record in records
        if _market_value(record, valuation_lookup) is None
    )
    missing_cost_basis = sum(
        1 for record in records if _decimal_value(record.get("cost")) is None
    )
    performance_count = sum(
        1
        for record in records
        if _decimal_value(record.get("cost")) is not None
        and _market_value(record, valuation_lookup) is not None
    )
    missing_holding_date = sum(
        1 for record in records if not _safe_value(record.get("purchase_date"))
    )
    unknown_sport = sum(
        1
        for record in records
        if _safe_value(record.get("sport")).upper() in {"", "UNKNOWN"}
    )
    currency_mismatch = sum(
        1
        for record in records
        if _safe_value(record.get("market_currency"))
        and _safe_value(record.get("currency"))
        and _safe_value(record.get("market_currency"))
        != _safe_value(record.get("currency"))
    )
    player_review = sum(
        1 for record in records if not _safe_value(record.get("player"))
    )
    metadata_cleanup = sum(
        1
        for record in records
        if not _safe_value(record.get("box"))
        and not _safe_value(record.get("location"))
    )
    lines = [
        "=====================================",
        "Onecool Decision Queue",
        "=====================================",
        "",
        "Critical",
        "--------",
        f"Missing Cost Basis: {missing_cost_basis}",
        f"Missing Market Value: {missing_market_values}",
        "",
        "High",
        "----",
        f"Insufficient Data: {missing_market_values + missing_cost_basis}",
        f"Import Warnings: {len(warnings)}",
        f"Currency Mismatch: {currency_mismatch}",
        "",
        "Medium",
        "------",
        f"Missing Performance Data: {len(records) - performance_count}",
        f"Missing Holding Date: {missing_holding_date}",
        f"Unknown Sport Classification: {unknown_sport}",
        "",
        "Low",
        "---",
        f"Player Normalization Review: {player_review}",
        f"Metadata Cleanup: {metadata_cleanup}",
        "",
        "Info",
        "----",
        f"Imported Cards: {result.summary.imported_rows}",
        f"Skipped Rows: {result.summary.skipped_rows}",
        f"Invalid Rows: {result.summary.invalid_rows}",
        f"Duplicate Rows: {result.summary.duplicate_rows}",
    ]
    return tuple(lines)


def ofai_context_lines(
    result: PSAImportResult,
    valuation_records: Sequence[ValuationRecord] | None = None,
) -> tuple[str, ...]:
    """Return deterministic OFAI context from imported session data."""

    records = tuple(result.records)
    valuation_lookup = _valuation_lookup(valuation_records)
    cost_by_currency = _sum_by_currency(records, "cost", "currency")
    market_by_currency = _sum_market_values_by_currency(
        records,
        valuation_lookup,
    )
    missing_market_values = sum(
        1
        for record in records
        if _market_value(record, valuation_lookup) is None
    )
    missing_cost_basis = sum(
        1 for record in records if _decimal_value(record.get("cost")) is None
    )
    performance_count = sum(
        1
        for record in records
        if _decimal_value(record.get("cost")) is not None
        and _market_value(record, valuation_lookup) is not None
    )
    valuation_count = len(
        {
            _safe_value(record.get("asset_id"))
            for record in records
            if _market_value(record, valuation_lookup) is not None
        }
    )
    queue_counts = _decision_priority_counts(
        decision_queue_lines(result, valuation_records)
    )
    lines = [
        "=====================================",
        "Onecool OFAI Context",
        "=====================================",
        "",
        "Collection Overview",
        "-------------------",
        f"Total Cards: {len(records)}",
    ]
    lines.extend(_count_lines(records, "grade_company"))
    lines.extend(
        (
            "",
            "Import Status",
            "-------------",
            f"Import Time: {result.audit.imported_at.isoformat()}",
            f"Imported: {result.summary.imported_rows}",
            f"Skipped: {result.summary.skipped_rows}",
            f"Warnings: {len(result.summary.warnings)}",
            f"Invalid: {result.summary.invalid_rows}",
            "",
            "Portfolio Status",
            "----------------",
            "Cost Basis by Currency",
        )
    )
    lines.extend(_money_lines(cost_by_currency))
    lines.append("Estimated Market Value (if available)")
    lines.extend(_money_lines(market_by_currency))
    lines.extend(
        (
            f"Missing Market Values: {missing_market_values}",
            f"Missing Cost Basis: {missing_cost_basis}",
            "",
            "Performance Status",
            "------------------",
            f"Cards with Performance Data: {performance_count}",
            f"Cards Missing Performance Data: {len(records) - performance_count}",
            f"Valuation Coverage: {valuation_count}/{len(records)}",
            "",
            "Review Priorities",
            "-----------------",
            f"Critical: {queue_counts['critical']}",
            f"High: {queue_counts['high']}",
            f"Medium: {queue_counts['medium']}",
            f"Low: {queue_counts['low']}",
            "",
            "Current Warnings",
            "----------------",
        )
    )
    lines.extend(_warning_summary_lines(tuple(result.summary.warnings)))
    lines.extend(
        (
            "",
            "Context Status",
            "--------------",
            "Runtime Session Ready",
            "",
            "AI Recommendation",
            "-----------------",
            "Not generated.",
            "Context only.",
        )
    )
    return tuple(lines)


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


def _count_lines(
    records: tuple[dict[str, Any], ...],
    field_name: str,
    *,
    fallback: str = "Unknown",
) -> list[str]:
    counts: dict[str, int] = {}
    for record in records:
        value = _safe_value(record.get(field_name)) or fallback
        if field_name == "sport" and value.upper() == "UNKNOWN":
            value = "Other"
        counts[value] = counts.get(value, 0) + 1
    if not counts:
        return ["  None: 0"]
    return [f"  {key}: {counts[key]}" for key in sorted(counts)]


def _players_lines(records: tuple[dict[str, Any], ...]) -> list[str]:
    players = sorted(
        {
            player
            for record in records
            if (player := _safe_value(record.get("player")))
        }
    )
    if not players:
        return ["None"]
    return players


def _top_player_lines(records: tuple[dict[str, Any], ...]) -> list[str]:
    counts: dict[str, int] = {}
    for record in records:
        player = _safe_value(record.get("player"))
        if not player:
            continue
        counts[player] = counts.get(player, 0) + 1
    if not counts:
        return ["None"]
    return [
        f"{player}: {counts[player]}"
        for player in sorted(counts, key=lambda key: (-counts[key], key))
    ]


def _sum_by_currency(
    records: tuple[dict[str, Any], ...],
    value_field: str,
    currency_field: str,
) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for record in records:
        value = _decimal_value(record.get(value_field))
        currency = _safe_value(record.get(currency_field))
        if value is None or not currency:
            continue
        totals[currency] = totals.get(currency, Decimal("0")) + value
    return totals


def _sum_market_values_by_currency(
    records: tuple[dict[str, Any], ...],
    valuation_lookup: dict[str, ValuationRecord] | None = None,
) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for record in records:
        valuation = _valuation_for_record(record, valuation_lookup)
        value = _market_value(record, valuation_lookup)
        currency = (
            valuation.currency
            if valuation is not None
            else _safe_value(record.get("market_currency"))
            or _safe_value(record.get("currency"))
        )
        if value is None or not currency:
            continue
        totals[currency] = totals.get(currency, Decimal("0")) + value
    return totals


def _market_value(
    record: dict[str, Any],
    valuation_lookup: dict[str, ValuationRecord] | None = None,
) -> Decimal | None:
    valuation = _valuation_for_record(record, valuation_lookup)
    if valuation is not None:
        return _valuation_amount(valuation)
    for field_name in (
        "estimated_market_value",
        "market_value",
        "current_market_value",
    ):
        value = _decimal_value(record.get(field_name))
        if value is not None:
            return value
    return None


def _valuation_lookup(
    valuation_records: Sequence[ValuationRecord] | None,
) -> dict[str, ValuationRecord]:
    lookup: dict[str, ValuationRecord] = {}
    for valuation in valuation_records or ():
        if not isinstance(valuation, ValuationRecord):
            continue
        current = lookup.get(valuation.asset_id)
        if current is None or valuation.valuation_date > current.valuation_date:
            lookup[valuation.asset_id] = valuation
    return lookup


def _valuation_for_record(
    record: dict[str, Any],
    valuation_lookup: dict[str, ValuationRecord] | None,
) -> ValuationRecord | None:
    if not valuation_lookup:
        return None
    asset_id = _safe_value(record.get("asset_id"))
    if not asset_id:
        return None
    return valuation_lookup.get(asset_id)


def _valuation_amount(valuation: ValuationRecord) -> Decimal | None:
    return valuation.market_value or valuation.estimated_value


def _valuation_records_for_import(
    valuation_records: Sequence[ValuationRecord],
    result: PSAImportResult,
) -> tuple[ValuationRecord, ...]:
    imported_asset_ids = {
        _safe_value(record.get("asset_id"))
        for record in result.records
        if _safe_value(record.get("asset_id"))
    }
    return tuple(
        valuation
        for valuation in valuation_records
        if isinstance(valuation, ValuationRecord)
        and valuation.asset_id in imported_asset_ids
    )


def _decimal_value(value: Any) -> Decimal | None:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not parsed.is_finite():
        return None
    return parsed


def _money_lines(values_by_currency: dict[str, Decimal]) -> list[str]:
    if not values_by_currency:
        return ["  None"]
    return [
        f"  {currency}: {_format_decimal_amount(values_by_currency[currency])}"
        for currency in sorted(values_by_currency)
    ]


def _format_decimal_amount(value: Decimal) -> str:
    return f"{value.normalize():f}"


def _unsupported_metadata_count(warnings: tuple[str, ...]) -> int:
    return sum(
        1
        for warning in warnings
        if warning.startswith("Unsupported grader")
    )


def _other_warning_count(warnings: tuple[str, ...]) -> int:
    return len(warnings) - _unsupported_metadata_count(warnings)


def _decision_priority_counts(lines: tuple[str, ...]) -> dict[str, int]:
    sections = {
        "critical": ("Missing Cost Basis:", "Missing Market Value:"),
        "high": ("Insufficient Data:", "Import Warnings:", "Currency Mismatch:"),
        "medium": (
            "Missing Performance Data:",
            "Missing Holding Date:",
            "Unknown Sport Classification:",
        ),
        "low": ("Player Normalization Review:", "Metadata Cleanup:"),
    }
    counts: dict[str, int] = {}
    for section, prefixes in sections.items():
        counts[section] = sum(
            _line_count_value(line)
            for line in lines
            if line.startswith(prefixes)
        )
    return counts


def _line_count_value(line: str) -> int:
    try:
        return int(line.rsplit(": ", maxsplit=1)[1])
    except (IndexError, ValueError):
        return 0


def _warning_summary_lines(warnings: tuple[str, ...]) -> list[str]:
    if not warnings:
        return ["None"]
    return [f"- {warning}" for warning in warnings]


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
