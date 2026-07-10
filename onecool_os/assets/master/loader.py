"""Load Asset Master metadata from local user-owned files."""

from __future__ import annotations

import csv
import zipfile
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from onecool_os.assets.master.models import AssetMasterLoadResult
from onecool_os.assets.master.models import AssetMasterRecord
from onecool_os.assets.master.validation import AssetMasterError
from onecool_os.assets.master.validation import validate_ebay_sold_search_url
from onecool_os.assets.master.validation import validate_psa_url

FIELD_ALIASES = {
    "asset_id": "asset_id",
    "asset id": "asset_id",
    "cert_number": "cert_number",
    "cert number": "cert_number",
    "cert": "cert_number",
    "card_name": "card_name",
    "card name": "card_name",
    "grade_issuer": "grade_issuer",
    "grade issuer": "grade_issuer",
    "grader": "grade_issuer",
    "grade": "grade",
    "cost_override": "cost_override",
    "cost override": "cost_override",
    "cost_currency": "cost_currency",
    "cost currency": "cost_currency",
    "ebay_sold_search_url": "ebay_sold_search_url",
    "ebay sold search url": "ebay_sold_search_url",
    "ebay url": "ebay_sold_search_url",
    "psa_url": "psa_url",
    "psa url": "psa_url",
    "ref_score": "ref_score",
    "ref score": "ref_score",
    "watch_status": "watch_status",
    "watch status": "watch_status",
    "target_price": "target_price",
    "target price": "target_price",
    "notes": "notes",
}


class AssetMasterLoader:
    """Read Asset Master CSV or XLSX files without mutating them."""

    def load(
        self,
        path: str | Path,
        *,
        reference_datetime: datetime | None = None,
    ) -> AssetMasterLoadResult:
        """Load one Asset Master file."""

        source_path = Path(path)
        generated_at = reference_datetime or datetime.now(UTC)
        if not source_path.exists():
            raise AssetMasterError(f"Asset Master file not found: {source_path}")
        suffix = source_path.suffix.lower()
        if suffix == ".csv":
            raw_rows = self._read_csv(source_path)
        elif suffix == ".xlsx":
            raw_rows = self._read_xlsx(source_path)
        else:
            raise AssetMasterError(
                "Asset Master supports only CSV and XLSX files."
            )
        return self._load_rows(
            raw_rows,
            source_file=str(source_path),
            generated_at=generated_at,
        )

    def _read_csv(self, path: Path) -> list[dict[str, Any]]:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                return [dict(row) for row in csv.DictReader(handle)]
        except csv.Error as exc:
            raise AssetMasterError(f"Invalid Asset Master CSV: {exc}") from exc
        except OSError as exc:
            raise AssetMasterError(
                f"Asset Master CSV cannot be read: {path}"
            ) from exc

    def _read_xlsx(self, path: Path) -> list[dict[str, Any]]:
        try:
            rows = _read_simple_xlsx_rows(path)
        except (OSError, KeyError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
            raise AssetMasterError(
                f"Invalid Asset Master XLSX: {path}"
            ) from exc
        if not rows:
            return []
        headers = [str(value or "").strip() for value in rows[0]]
        return [
            {
                headers[index]: row[index] if index < len(row) else ""
                for index in range(len(headers))
            }
            for row in rows[1:]
            if any(str(value or "").strip() for value in row)
        ]

    def _load_rows(
        self,
        raw_rows: list[dict[str, Any]],
        *,
        source_file: str,
        generated_at: datetime,
    ) -> AssetMasterLoadResult:
        records: list[AssetMasterRecord] = []
        warnings: list[str] = []
        errors: list[str] = []
        duplicate_cert_numbers: list[str] = []
        seen_by_cert: dict[str, AssetMasterRecord] = {}
        for row_number, row in enumerate(raw_rows, start=2):
            normalized_row = _normalize_row(row)
            normalized_row["source_row"] = row_number
            normalized_row["imported_at"] = generated_at
            try:
                record = AssetMasterRecord(**normalized_row)
            except TypeError as exc:
                errors.append(f"Unsupported Asset Master field at row {row_number}: {exc}")
                continue
            except AssetMasterError as exc:
                errors.append(f"Asset Master row {row_number}: {exc}")
                continue
            row_errors = _record_validation_errors(record)
            if row_errors:
                errors.extend(
                    f"Asset Master row {row_number}: {error}"
                    for error in row_errors
                )
                continue
            previous = seen_by_cert.get(record.cert_number)
            if previous is not None:
                if record.cert_number not in duplicate_cert_numbers:
                    duplicate_cert_numbers.append(record.cert_number)
                warnings.append(
                    f"Duplicate cert number at row {row_number}: "
                    f"{record.cert_number}"
                )
                if previous.to_metadata() != record.to_metadata():
                    errors.append(
                        "Conflicting duplicate metadata for cert number "
                        f"{record.cert_number} at row {row_number}"
                    )
                continue
            seen_by_cert[record.cert_number] = record
            records.append(record)
        return AssetMasterLoadResult(
            records=tuple(records),
            warnings=tuple(warnings),
            errors=tuple(errors),
            duplicate_cert_numbers=tuple(sorted(duplicate_cert_numbers)),
            source_file=source_file,
            generated_at=generated_at,
        )


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {"metadata": {}}
    for raw_key, value in row.items():
        if raw_key is None:
            continue
        key = str(raw_key).strip()
        if not key:
            continue
        canonical_key = FIELD_ALIASES.get(key.lower().replace("-", " "))
        if canonical_key:
            normalized[canonical_key] = value
        elif str(value or "").strip():
            normalized["metadata"][key] = value
    return normalized


def _record_validation_errors(record: AssetMasterRecord) -> tuple[str, ...]:
    errors = []
    ebay_error = validate_ebay_sold_search_url(record.ebay_sold_search_url)
    if ebay_error:
        errors.append(ebay_error)
    psa_error = validate_psa_url(record.psa_url)
    if psa_error:
        errors.append(psa_error)
    return tuple(errors)


def _read_simple_xlsx_rows(path: Path) -> list[list[str]]:
    """Read first-sheet values from a simple XLSX using only stdlib."""

    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        shared_strings = _read_shared_strings(archive, namespace)
        sheet_xml = archive.read("xl/worksheets/sheet1.xml")
    root = ElementTree.fromstring(sheet_xml)
    parsed_rows: list[list[str]] = []
    for row in root.findall(".//main:sheetData/main:row", namespace):
        cells: dict[int, str] = {}
        for cell in row.findall("main:c", namespace):
            cell_ref = cell.attrib.get("r", "")
            column_index = _column_index(cell_ref)
            cell_type = cell.attrib.get("t")
            value_element = cell.find("main:v", namespace)
            inline_element = cell.find("main:is/main:t", namespace)
            if inline_element is not None:
                value = inline_element.text or ""
            elif value_element is None:
                value = ""
            elif cell_type == "s":
                value = shared_strings[int(value_element.text or "0")]
            else:
                value = value_element.text or ""
            cells[column_index] = value
        if cells:
            parsed_rows.append(
                [cells.get(index, "") for index in range(max(cells) + 1)]
            )
    return parsed_rows


def _read_shared_strings(
    archive: zipfile.ZipFile,
    namespace: dict[str, str],
) -> list[str]:
    try:
        shared_xml = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ElementTree.fromstring(shared_xml)
    strings: list[str] = []
    for item in root.findall("main:si", namespace):
        strings.append(
            "".join(
                text.text or ""
                for text in item.findall(".//main:t", namespace)
            )
        )
    return strings


def _column_index(cell_ref: str) -> int:
    letters = "".join(character for character in cell_ref if character.isalpha())
    index = 0
    for character in letters:
        index = index * 26 + (ord(character.upper()) - ord("A") + 1)
    return max(index - 1, 0)
