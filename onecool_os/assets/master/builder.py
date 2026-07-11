"""Build an updated Asset Master workbook from PSA/BGS collection CSV."""

from __future__ import annotations

import csv
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from onecool_os.assets.master.validation import AssetMasterError

DEFAULT_SOURCE_WORKBOOK = Path("imports/asset_master/source/球員卡投組.xlsx")
DEFAULT_COLLECTION_CSV = Path("imports/psa/collection.csv")
DEFAULT_OUTPUT_WORKBOOK = Path("imports/asset_master/asset_master.xlsx")

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
ElementTree.register_namespace("", MAIN_NS)
ElementTree.register_namespace("r", REL_NS)

REQUIRED_COLLECTION_COLUMNS = (
    "Item",
    "Cert Number",
    "Grade Issuer",
    "Grade",
    "Year",
    "Set",
    "Card Number",
    "Subject",
    "My Cost",
    "Date Acquired",
)
IDENTITY_FIELDS = (
    "Item",
    "Cert Number",
    "Grade Issuer",
    "Grade",
    "Year",
    "Set",
    "Card Number",
    "Subject",
    "Variety",
    "My Cost",
    "Date Acquired",
)
USER_MAINTAINED_FIELDS = frozenset(
    {
        "即時價格",
        "REF",
        "操作建議",
        "Watch Status",
        "Target Price",
        "Notes",
    }
)
GENERATED_LINK_FIELDS = ("eBay Sold Search URL", "PSA URL")
HEADER_ALIASES = {
    "item": "Item",
    "品項": "Item",
    "cert number": "Cert Number",
    "cert": "Cert Number",
    "證書號碼": "Cert Number",
    "認證號碼": "Cert Number",
    "grade issuer": "Grade Issuer",
    "grader": "Grade Issuer",
    "評級公司": "Grade Issuer",
    "grade": "Grade",
    "評分": "Grade",
    "year": "Year",
    "年份": "Year",
    "set": "Set",
    "系列": "Set",
    "card number": "Card Number",
    "卡號": "Card Number",
    "subject": "Subject",
    "player": "Subject",
    "球員": "Subject",
    "variety": "Variety",
    "parallel": "Variety",
    "my cost": "My Cost",
    "成本": "My Cost",
    "date acquired": "Date Acquired",
    "購入日期": "Date Acquired",
    "ebay sold search url": "eBay Sold Search URL",
    "ebay url": "eBay Sold Search URL",
    "ebay 即時成交價": "eBay Sold Search URL",
    "psa url": "PSA URL",
    "psa 官網快速連結 (手動核對)": "PSA URL",
}
_ACTIVE_SHARED_STRINGS: tuple[str, ...] = ()


class AssetMasterBuildError(AssetMasterError):
    """Raised when Asset Master workbook build fails."""


@dataclass(frozen=True)
class AssetMasterBuildResult:
    """Summary of one Asset Master build."""

    source_workbook: str
    source_collection: str
    output_workbook: str
    original_valid_card_count: int
    latest_collection_count: int
    exact_cert_matches: int
    fallback_identity_matches: int
    appended_cards: int
    unmatched_old_rows: int
    ambiguous_matches: int
    duplicate_cert_numbers: int
    final_unique_card_count: int
    ebay_links_present: int
    psa_links_present: int
    bgs_cards: int
    generated_at: datetime


class AssetMasterBuilder:
    """Update an existing workbook using the latest PSA/BGS collection CSV."""

    def build(
        self,
        source_workbook: str | Path = DEFAULT_SOURCE_WORKBOOK,
        collection_csv: str | Path = DEFAULT_COLLECTION_CSV,
        output_workbook: str | Path = DEFAULT_OUTPUT_WORKBOOK,
        *,
        reference_datetime: datetime | None = None,
    ) -> AssetMasterBuildResult:
        """Build the updated Asset Master workbook."""

        source_path = Path(source_workbook)
        collection_path = Path(collection_csv)
        output_path = Path(output_workbook)
        generated_at = reference_datetime or datetime.now(UTC)
        if not source_path.exists():
            raise AssetMasterBuildError(
                f"Source workbook not found: {source_path}"
            )
        if not collection_path.exists():
            raise AssetMasterBuildError(
                f"Collection CSV not found: {collection_path}"
            )
        collection_records = _read_collection_records(collection_path)
        if not collection_records:
            raise AssetMasterBuildError("Collection CSV has no valid cards.")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_output = Path(temp_dir) / output_path.name
            result = self._build_temp(
                source_path,
                collection_path,
                temp_output,
                collection_records,
                generated_at,
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(temp_output, output_path)
            return AssetMasterBuildResult(
                **{
                    **result.__dict__,
                    "output_workbook": str(output_path),
                }
            )

    def _build_temp(
        self,
        source_path: Path,
        collection_path: Path,
        output_path: Path,
        collection_records: tuple[dict[str, str], ...],
        generated_at: datetime,
    ) -> AssetMasterBuildResult:
        with zipfile.ZipFile(source_path, "r") as source_zip:
            entries = {name: source_zip.read(name) for name in source_zip.namelist()}

        workbook = _WorkbookXml(entries)
        sheet_path = workbook.first_sheet_path()
        sheet = _WorksheetXml(entries[sheet_path], _shared_strings(entries))
        header_map = _ensure_headers(sheet)
        existing_rows = _existing_card_rows(sheet, header_map)
        original_valid_count = len(existing_rows)
        match_result = _match_records(existing_rows, collection_records, header_map)
        _update_matched_rows(sheet, header_map, match_result)
        _append_new_rows(sheet, header_map, match_result.append_records)
        sheet.refresh_dimension()
        entries[sheet_path] = sheet.to_bytes()
        entries = _replace_sync_report(
            entries,
            workbook,
            _sync_rows(
                source_path,
                collection_path,
                original_valid_count,
                collection_records,
                match_result,
                sheet,
                header_map,
                generated_at,
            ),
        )
        _write_zip(output_path, entries)
        _validate_output(output_path, len(collection_records))
        summary = _summarize_output(
            output_path,
            source_path,
            collection_path,
            original_valid_count,
            collection_records,
            match_result,
            generated_at,
        )
        return summary


@dataclass(frozen=True)
class _MatchResult:
    exact_cert_matches: tuple[tuple[Any, dict[str, str]], ...]
    fallback_identity_matches: tuple[tuple[Any, dict[str, str]], ...]
    append_records: tuple[dict[str, str], ...]
    unmatched_old_rows: tuple[Any, ...]
    ambiguous_records: tuple[dict[str, str], ...]
    duplicate_cert_numbers: tuple[str, ...]


class _WorksheetXml:
    def __init__(
        self,
        xml_bytes: bytes,
        shared_strings: tuple[str, ...] = (),
    ) -> None:
        global _ACTIVE_SHARED_STRINGS
        _ACTIVE_SHARED_STRINGS = shared_strings
        self.shared_strings = shared_strings
        self.root = ElementTree.fromstring(xml_bytes)
        self.sheet_data = self.root.find(_main("sheetData"))
        if self.sheet_data is None:
            raise AssetMasterBuildError("Workbook sheet is missing sheetData.")

    def rows(self) -> list[ElementTree.Element]:
        return list(self.sheet_data.findall(_main("row")))

    def header_row(self) -> ElementTree.Element:
        rows = self.rows()
        if not rows:
            row = ElementTree.Element(_main("row"), {"r": "1"})
            self.sheet_data.append(row)
            return row
        return rows[0]

    def last_valid_row_index(self, header_map: dict[str, int]) -> int:
        indexes = [
            int(row.attrib.get("r", "0"))
            for row in self.rows()[1:]
            if _row_cert(row, header_map)
        ]
        return max(indexes or [1])

    def row_by_index(self, row_index: int) -> ElementTree.Element | None:
        for row in self.rows():
            if int(row.attrib.get("r", "0")) == row_index:
                return row
        return None

    def append_row_from_template(
        self,
        template_row: ElementTree.Element | None,
        row_index: int,
    ) -> ElementTree.Element:
        if template_row is not None:
            old_row_index = int(template_row.attrib.get("r", str(row_index)))
            row = ElementTree.fromstring(ElementTree.tostring(template_row))
            row.attrib["r"] = str(row_index)
            for cell in row.findall(_main("c")):
                old_ref = cell.attrib.get("r", "")
                cell.attrib["r"] = f"{_cell_letters(old_ref)}{row_index}"
                formula = cell.find(_main("f"))
                if formula is not None and formula.text:
                    formula.text = _shift_formula_rows(
                        formula.text,
                        old_row_index,
                        row_index,
                    )
                    value = cell.find(_main("v"))
                    if value is not None:
                        cell.remove(value)
                else:
                    _clear_cell_value(cell)
        else:
            row = ElementTree.Element(_main("row"), {"r": str(row_index)})
        self.sheet_data.append(row)
        return row

    def refresh_dimension(self) -> None:
        dimension = self.root.find(_main("dimension"))
        if dimension is None:
            dimension = ElementTree.Element(_main("dimension"))
            self.root.insert(0, dimension)
        max_row = max((int(row.attrib.get("r", "1")) for row in self.rows()), default=1)
        max_col = 1
        for row in self.rows():
            for cell in row.findall(_main("c")):
                max_col = max(max_col, _column_index(cell.attrib.get("r", "A1")) + 1)
        dimension.attrib["ref"] = f"A1:{_column_name(max_col)}{max_row}"

    def to_bytes(self) -> bytes:
        return ElementTree.tostring(
            self.root,
            encoding="utf-8",
            xml_declaration=True,
        )


class _WorkbookXml:
    def __init__(self, entries: dict[str, bytes]) -> None:
        self.entries = entries
        self.workbook_root = ElementTree.fromstring(entries["xl/workbook.xml"])
        self.rels_root = ElementTree.fromstring(entries["xl/_rels/workbook.xml.rels"])
        self.content_types_root = ElementTree.fromstring(entries["[Content_Types].xml"])

    def first_sheet_path(self) -> str:
        sheet = self.workbook_root.find(f"{_main('sheets')}/{_main('sheet')}")
        if sheet is None:
            raise AssetMasterBuildError("Workbook has no worksheets.")
        relationship_id = sheet.attrib[f"{{{REL_NS}}}id"]
        target = self._relationship_target(relationship_id)
        return _target_to_entry(target)

    def remove_sync_report(self) -> None:
        sheets = self.workbook_root.find(_main("sheets"))
        if sheets is None:
            return
        removed_relationship_ids = []
        for sheet in list(sheets.findall(_main("sheet"))):
            if sheet.attrib.get("name") == "Sync Report":
                removed_relationship_ids.append(sheet.attrib.get(f"{{{REL_NS}}}id"))
                sheets.remove(sheet)
        for relationship in list(self.rels_root):
            if relationship.attrib.get("Id") in removed_relationship_ids:
                target = relationship.attrib.get("Target", "")
                self.entries.pop(_target_to_entry(target), None)
                self.rels_root.remove(relationship)

    def add_sync_report(self, sheet_xml: bytes) -> None:
        self.remove_sync_report()
        sheets = self.workbook_root.find(_main("sheets"))
        if sheets is None:
            sheets = ElementTree.SubElement(self.workbook_root, _main("sheets"))
        next_sheet_id = _next_sheet_id(sheets)
        next_rel_id = _next_rel_id(self.rels_root)
        next_sheet_number = _next_sheet_number(self.entries)
        target = f"worksheets/sheet{next_sheet_number}.xml"
        entry = f"xl/{target}"
        ElementTree.SubElement(
            sheets,
            _main("sheet"),
            {
                "name": "Sync Report",
                "sheetId": str(next_sheet_id),
                f"{{{REL_NS}}}id": next_rel_id,
            },
        )
        ElementTree.SubElement(
            self.rels_root,
            f"{{{PKG_REL_NS}}}Relationship",
            {
                "Id": next_rel_id,
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
                "Target": target,
            },
        )
        _ensure_content_type(self.content_types_root, f"/{entry}")
        self.entries[entry] = sheet_xml
        self.entries["xl/workbook.xml"] = ElementTree.tostring(
            self.workbook_root,
            encoding="utf-8",
            xml_declaration=True,
        )
        self.entries["xl/_rels/workbook.xml.rels"] = ElementTree.tostring(
            self.rels_root,
            encoding="utf-8",
            xml_declaration=True,
        )
        self.entries["[Content_Types].xml"] = ElementTree.tostring(
            self.content_types_root,
            encoding="utf-8",
            xml_declaration=True,
        )

    def _relationship_target(self, relationship_id: str) -> str:
        for relationship in self.rels_root:
            if relationship.attrib.get("Id") == relationship_id:
                return relationship.attrib["Target"]
        raise AssetMasterBuildError(f"Missing worksheet relationship: {relationship_id}")


def _read_collection_records(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise AssetMasterBuildError("Collection CSV is missing headers.")
        missing = sorted(set(REQUIRED_COLLECTION_COLUMNS) - set(reader.fieldnames))
        if missing:
            raise AssetMasterBuildError(
                f"Collection CSV missing columns: {', '.join(missing)}"
            )
        records = []
        seen_certs = set()
        duplicate_certs = set()
        for row in reader:
            record = _normalize_collection_row(row)
            if not record:
                continue
            cert_number = record["Cert Number"]
            if cert_number in seen_certs:
                duplicate_certs.add(cert_number)
            seen_certs.add(cert_number)
            records.append(record)
        if duplicate_certs:
            raise AssetMasterBuildError(
                "Collection CSV duplicate cert numbers: "
                f"{', '.join(sorted(duplicate_certs))}"
            )
        return tuple(records)


def _normalize_collection_row(row: dict[str, str]) -> dict[str, str] | None:
    record = {
        field: str(row.get(field) or "").strip()
        for field in set(IDENTITY_FIELDS) | {"Black Label"}
    }
    if not all(record.get(field) for field in REQUIRED_COLLECTION_COLUMNS):
        return None
    if _parse_positive_decimal(record["My Cost"]) is None:
        return None
    return record


def _ensure_headers(sheet: _WorksheetXml) -> dict[str, int]:
    header_row = sheet.header_row()
    existing = {
        _canonical_header(_cell_text(cell)): _column_index(cell.attrib.get("r", "A1"))
        for cell in header_row.findall(_main("c"))
        if _canonical_header(_cell_text(cell))
    }
    required = tuple(IDENTITY_FIELDS) + GENERATED_LINK_FIELDS
    next_column = max(existing.values(), default=-1) + 1
    for header in required:
        if header not in existing:
            _set_text_cell(header_row, next_column, 1, header)
            existing[header] = next_column
            next_column += 1
    return existing


def _existing_card_rows(
    sheet: _WorksheetXml,
    header_map: dict[str, int],
) -> tuple[ElementTree.Element, ...]:
    return tuple(
        row for row in sheet.rows()[1:] if _row_cert(row, header_map)
    )


def _match_records(
    existing_rows: tuple[ElementTree.Element, ...],
    collection_records: tuple[dict[str, str], ...],
    header_map: dict[str, int],
) -> _MatchResult:
    rows_by_cert = {
        _row_cert(row, header_map): row
        for row in existing_rows
        if _row_cert(row, header_map)
    }
    exact_matches = []
    fallback_matches = []
    append_records = []
    ambiguous = []
    matched_row_ids = set()
    seen_collection_certs = set()
    duplicate_certs = []
    for record in collection_records:
        cert_number = _normalize(record["Cert Number"])
        if cert_number in seen_collection_certs:
            duplicate_certs.append(record["Cert Number"])
        seen_collection_certs.add(cert_number)
        row = rows_by_cert.get(cert_number)
        if row is not None:
            exact_matches.append((row, record))
            matched_row_ids.add(id(row))
            continue
        candidates = [
            old_row
            for old_row in existing_rows
            if id(old_row) not in matched_row_ids
            and (
                _row_identity(old_row, header_map) == _record_identity(record)
                or _row_item_identity(old_row, header_map)
                == _record_item_identity(record)
            )
        ]
        if len(candidates) == 1:
            fallback_matches.append((candidates[0], record))
            matched_row_ids.add(id(candidates[0]))
        elif len(candidates) > 1:
            ambiguous.append(record)
        else:
            append_records.append(record)
    unmatched = tuple(row for row in existing_rows if id(row) not in matched_row_ids)
    return _MatchResult(
        exact_cert_matches=tuple(exact_matches),
        fallback_identity_matches=tuple(fallback_matches),
        append_records=tuple(append_records),
        unmatched_old_rows=unmatched,
        ambiguous_records=tuple(ambiguous),
        duplicate_cert_numbers=tuple(sorted(set(duplicate_certs))),
    )


def _update_matched_rows(
    sheet: _WorksheetXml,
    header_map: dict[str, int],
    match_result: _MatchResult,
) -> None:
    for row, record in (
        match_result.exact_cert_matches + match_result.fallback_identity_matches
    ):
        row_index = int(row.attrib["r"])
        for field in IDENTITY_FIELDS:
            _set_text_cell(row, header_map[field], row_index, record.get(field, ""))


def _append_new_rows(
    sheet: _WorksheetXml,
    header_map: dict[str, int],
    records: tuple[dict[str, str], ...],
) -> None:
    last_index = sheet.last_valid_row_index(header_map)
    template = sheet.row_by_index(last_index)
    for offset, record in enumerate(records, start=1):
        row_index = last_index + offset
        row = sheet.append_row_from_template(template, row_index)
        for field in IDENTITY_FIELDS:
            _set_text_cell(row, header_map[field], row_index, record.get(field, ""))
        _set_formula_cell(
            row,
            header_map["eBay Sold Search URL"],
            row_index,
            _ebay_formula(record),
        )
        if _normalize(record.get("Grade Issuer")) == "PSA":
            _set_formula_cell(
                row,
                header_map["PSA URL"],
                row_index,
                _psa_formula(record["Cert Number"]),
            )
        else:
            _set_text_cell(row, header_map["PSA URL"], row_index, "")


def _sync_rows(
    source_path: Path,
    collection_path: Path,
    original_count: int,
    collection_records: tuple[dict[str, str], ...],
    match_result: _MatchResult,
    sheet: _WorksheetXml,
    header_map: dict[str, int],
    generated_at: datetime,
) -> list[list[str]]:
    rows = [
        ["Metric", "Value"],
        ["source workbook path", str(source_path)],
        ["source collection path", str(collection_path)],
        ["original valid-card count", str(original_count)],
        ["latest collection count", str(len(collection_records))],
        ["exact cert matches", str(len(match_result.exact_cert_matches))],
        ["fallback identity matches", str(len(match_result.fallback_identity_matches))],
        ["appended cards", str(len(match_result.append_records))],
        ["unmatched old rows", str(len(match_result.unmatched_old_rows))],
        ["ambiguous matches", str(len(match_result.ambiguous_records))],
        ["duplicate cert numbers", str(len(match_result.duplicate_cert_numbers))],
        ["final unique-card count", str(_unique_cert_count(sheet, header_map))],
        ["eBay links present", str(_formula_count(sheet, header_map, "eBay Sold Search URL"))],
        ["PSA links present", str(_formula_count(sheet, header_map, "PSA URL"))],
        ["BGS cards", str(_bgs_count(collection_records))],
        ["generated timestamp", generated_at.isoformat()],
        [],
        ["Item", "Cert Number", "Grade Issuer", "Grade", "Match Status", "Notes"],
    ]
    for _, record in match_result.fallback_identity_matches:
        rows.append(_sync_detail_row(record, "Fallback Match", "Cert number updated from identity match."))
    for record in match_result.append_records:
        rows.append(_sync_detail_row(record, "Appended", "New card appended."))
    for record in match_result.ambiguous_records:
        rows.append(_sync_detail_row(record, "Ambiguous", "Multiple potential matches; manual review required."))
    return rows


def _replace_sync_report(
    entries: dict[str, bytes],
    workbook: _WorkbookXml,
    rows: list[list[str]],
) -> dict[str, bytes]:
    workbook.add_sync_report(_build_simple_sheet(rows))
    return workbook.entries


def _validate_output(path: Path, expected_count: int) -> None:
    with zipfile.ZipFile(path, "r") as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    workbook = _WorkbookXml(entries)
    sheet = _WorksheetXml(
        entries[workbook.first_sheet_path()],
        _shared_strings(entries),
    )
    header_map = _ensure_headers(sheet)
    unique_count = _unique_cert_count(sheet, header_map)
    if unique_count != expected_count:
        raise AssetMasterBuildError(
            "Final unique card count does not match collection count: "
            f"{unique_count} != {expected_count}"
        )
    duplicate_certs = _duplicate_sheet_certs(sheet, header_map)
    if duplicate_certs:
        raise AssetMasterBuildError(
            f"Output duplicate cert numbers: {', '.join(duplicate_certs)}"
        )


def _summarize_output(
    path: Path,
    source_path: Path,
    collection_path: Path,
    original_count: int,
    collection_records: tuple[dict[str, str], ...],
    match_result: _MatchResult,
    generated_at: datetime,
) -> AssetMasterBuildResult:
    with zipfile.ZipFile(path, "r") as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    workbook = _WorkbookXml(entries)
    sheet = _WorksheetXml(
        entries[workbook.first_sheet_path()],
        _shared_strings(entries),
    )
    header_map = _ensure_headers(sheet)
    return AssetMasterBuildResult(
        source_workbook=str(source_path),
        source_collection=str(collection_path),
        output_workbook=str(path),
        original_valid_card_count=original_count,
        latest_collection_count=len(collection_records),
        exact_cert_matches=len(match_result.exact_cert_matches),
        fallback_identity_matches=len(match_result.fallback_identity_matches),
        appended_cards=len(match_result.append_records),
        unmatched_old_rows=len(match_result.unmatched_old_rows),
        ambiguous_matches=len(match_result.ambiguous_records),
        duplicate_cert_numbers=len(match_result.duplicate_cert_numbers),
        final_unique_card_count=_unique_cert_count(sheet, header_map),
        ebay_links_present=_formula_count(sheet, header_map, "eBay Sold Search URL"),
        psa_links_present=_formula_count(sheet, header_map, "PSA URL"),
        bgs_cards=_bgs_count(collection_records),
        generated_at=generated_at,
    )


def _build_simple_sheet(rows: list[list[str]]) -> bytes:
    worksheet = ElementTree.Element(_main("worksheet"))
    sheet_data = ElementTree.SubElement(worksheet, _main("sheetData"))
    for row_index, row_values in enumerate(rows, start=1):
        row = ElementTree.SubElement(sheet_data, _main("row"), {"r": str(row_index)})
        for column_index, value in enumerate(row_values):
            _set_text_cell(row, column_index, row_index, value)
    return ElementTree.tostring(worksheet, encoding="utf-8", xml_declaration=True)


def _sync_detail_row(record: dict[str, str], status: str, notes: str) -> list[str]:
    return [
        record.get("Item", ""),
        record.get("Cert Number", ""),
        record.get("Grade Issuer", ""),
        record.get("Grade", ""),
        status,
        notes,
    ]


def _canonical_header(value: str) -> str:
    text = str(value or "").strip()
    return HEADER_ALIASES.get(text.lower(), text)


def _cell_text(cell: ElementTree.Element) -> str:
    formula = cell.find(_main("f"))
    if formula is not None and formula.text:
        return formula.text
    value = cell.find(_main("v"))
    if cell.attrib.get("t") == "s" and value is not None and value.text:
        index = int(value.text)
        if 0 <= index < len(_ACTIVE_SHARED_STRINGS):
            return _ACTIVE_SHARED_STRINGS[index]
    if value is not None and value.text:
        return value.text
    inline = cell.find(f"{_main('is')}/{_main('t')}")
    if inline is not None and inline.text:
        return inline.text
    return ""


def _set_text_cell(
    row: ElementTree.Element,
    column_index: int,
    row_index: int,
    value: str,
) -> None:
    cell = _cell(row, column_index, row_index)
    _clear_cell_value(cell)
    cell.attrib["t"] = "inlineStr"
    inline = ElementTree.SubElement(cell, _main("is"))
    text = ElementTree.SubElement(inline, _main("t"))
    text.text = str(value or "")


def _set_formula_cell(
    row: ElementTree.Element,
    column_index: int,
    row_index: int,
    formula: str,
) -> None:
    cell = _cell(row, column_index, row_index)
    _clear_cell_value(cell)
    cell.attrib.pop("t", None)
    formula_element = ElementTree.SubElement(cell, _main("f"))
    formula_element.text = formula


def _cell(row: ElementTree.Element, column_index: int, row_index: int) -> ElementTree.Element:
    reference = f"{_column_name(column_index + 1)}{row_index}"
    for cell in row.findall(_main("c")):
        if cell.attrib.get("r") == reference:
            return cell
    cell = ElementTree.Element(_main("c"), {"r": reference})
    inserted = False
    for index, existing in enumerate(list(row.findall(_main("c")))):
        if _column_index(existing.attrib.get("r", "A1")) > column_index:
            row.insert(index, cell)
            inserted = True
            break
    if not inserted:
        row.append(cell)
    return cell


def _clear_cell_value(cell: ElementTree.Element) -> None:
    for child in list(cell):
        if child.tag in {_main("v"), _main("f"), _main("is")}:
            cell.remove(child)


def _row_cert(row: ElementTree.Element, header_map: dict[str, int]) -> str:
    return _normalize(_row_value(row, header_map, "Cert Number"))


def _row_value(
    row: ElementTree.Element,
    header_map: dict[str, int],
    field: str,
) -> str:
    column_index = header_map.get(field)
    if column_index is None:
        return ""
    for cell in row.findall(_main("c")):
        if _column_index(cell.attrib.get("r", "A1")) == column_index:
            return _cell_text(cell)
    return ""


def _row_identity(row: ElementTree.Element, header_map: dict[str, int]) -> tuple[str, ...]:
    return tuple(
        _normalize(_row_value(row, header_map, field))
        for field in (
            "Year",
            "Set",
            "Card Number",
            "Subject",
            "Variety",
            "Grade Issuer",
            "Grade",
        )
    )


def _record_identity(record: dict[str, str]) -> tuple[str, ...]:
    return tuple(
        _normalize(record.get(field, ""))
        for field in (
            "Year",
            "Set",
            "Card Number",
            "Subject",
            "Variety",
            "Grade Issuer",
            "Grade",
        )
    )


def _row_item_identity(row: ElementTree.Element, header_map: dict[str, int]) -> tuple[str, ...]:
    return (
        _normalize(_row_value(row, header_map, "Item")),
        _normalize(_row_value(row, header_map, "Grade Issuer")),
        _normalize(_row_value(row, header_map, "Grade")),
    )


def _record_item_identity(record: dict[str, str]) -> tuple[str, ...]:
    return (
        _normalize(record.get("Item", "")),
        _normalize(record.get("Grade Issuer", "")),
        _normalize(record.get("Grade", "")),
    )


def _ebay_formula(record: dict[str, str]) -> str:
    terms = [
        record.get("Year", ""),
        record.get("Set", ""),
        record.get("Card Number", ""),
        record.get("Subject", ""),
        record.get("Variety", ""),
        record.get("Grade Issuer", ""),
        record.get("Grade", ""),
    ]
    if "BLACK LABEL" in _normalize(record.get("Grade", "")):
        terms.append("Black Label")
    query = "+".join(
        re.sub(r"[^A-Za-z0-9]+", "+", term).strip("+")
        for term in terms
        if term
    )
    url = f"https://www.ebay.com/sch/i.html?_nkw={query}&LH_Sold=1&LH_Complete=1"
    return f'HYPERLINK("{url}","查看 eBay 成交")'


def _psa_formula(cert_number: str) -> str:
    return (
        f'HYPERLINK("https://www.psacard.com/cert/{cert_number}",'
        '"點我查看 PSA 官方紀錄")'
    )


def _unique_cert_count(sheet: _WorksheetXml, header_map: dict[str, int]) -> int:
    return len({_row_cert(row, header_map) for row in _existing_card_rows(sheet, header_map)})


def _duplicate_sheet_certs(sheet: _WorksheetXml, header_map: dict[str, int]) -> tuple[str, ...]:
    certs = [_row_cert(row, header_map) for row in _existing_card_rows(sheet, header_map)]
    return tuple(sorted({cert for cert in certs if certs.count(cert) > 1}))


def _formula_count(sheet: _WorksheetXml, header_map: dict[str, int], field: str) -> int:
    count = 0
    column_index = header_map[field]
    for row in _existing_card_rows(sheet, header_map):
        for cell in row.findall(_main("c")):
            if _column_index(cell.attrib.get("r", "A1")) == column_index:
                formula = cell.find(_main("f"))
                if formula is not None and formula.text:
                    count += 1
    return count


def _bgs_count(records: tuple[dict[str, str], ...]) -> int:
    return sum(1 for record in records if _normalize(record.get("Grade Issuer")) == "BGS")


def _parse_positive_decimal(value: str) -> Decimal | None:
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    if not parsed.is_finite() or parsed <= 0:
        return None
    return parsed


def _normalize(value: Any) -> str:
    text = str(value or "").strip()
    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:E[+-]?\d+)?", text, flags=re.IGNORECASE):
        try:
            parsed = Decimal(text)
        except InvalidOperation:
            return text.upper()
        if parsed == parsed.to_integral_value():
            return str(parsed.quantize(Decimal(1))).upper()
    return text.upper()


def _main(name: str) -> str:
    return f"{{{MAIN_NS}}}{name}"


def _shared_strings(entries: dict[str, bytes]) -> tuple[str, ...]:
    content = entries.get("xl/sharedStrings.xml")
    if not content:
        return ()
    root = ElementTree.fromstring(content)
    values = []
    for item in root.findall(_main("si")):
        values.append("".join(text.text or "" for text in item.iter(_main("t"))))
    return tuple(values)


def _shift_formula_rows(formula: str, old_row_index: int, new_row_index: int) -> str:
    return re.sub(
        rf"(?<![A-Za-z0-9_])(\$?[A-Z]{{1,3}})\$?{old_row_index}(?!\d)",
        lambda match: f"{match.group(1)}{new_row_index}",
        formula,
    )


def _target_to_entry(target: str) -> str:
    target = target.lstrip("/")
    if target.startswith("xl/"):
        return target
    return f"xl/{target}"


def _next_sheet_id(sheets: ElementTree.Element) -> int:
    ids = [int(sheet.attrib.get("sheetId", "0")) for sheet in sheets.findall(_main("sheet"))]
    return max(ids or [0]) + 1


def _next_rel_id(rels_root: ElementTree.Element) -> str:
    ids = []
    for relationship in rels_root:
        rel_id = relationship.attrib.get("Id", "")
        if rel_id.startswith("rId") and rel_id[3:].isdigit():
            ids.append(int(rel_id[3:]))
    return f"rId{max(ids or [0]) + 1}"


def _next_sheet_number(entries: dict[str, bytes]) -> int:
    numbers = []
    for entry in entries:
        match = re.fullmatch(r"xl/worksheets/sheet(\d+)\.xml", entry)
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers or [0]) + 1


def _ensure_content_type(root: ElementTree.Element, part_name: str) -> None:
    for override in root.findall(f"{{{CONTENT_TYPES_NS}}}Override"):
        if override.attrib.get("PartName") == part_name:
            return
    ElementTree.SubElement(
        root,
        f"{{{CONTENT_TYPES_NS}}}Override",
        {
            "PartName": part_name,
            "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
        },
    )


def _write_zip(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)


def _column_index(cell_ref: str) -> int:
    letters = _cell_letters(cell_ref)
    index = 0
    for character in letters:
        index = index * 26 + (ord(character.upper()) - ord("A") + 1)
    return max(index - 1, 0)


def _cell_letters(cell_ref: str) -> str:
    return "".join(character for character in cell_ref if character.isalpha()) or "A"


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name
