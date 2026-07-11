from __future__ import annotations

import csv
import zipfile
from datetime import UTC
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

import pytest

from onecool_os.assets.master import AssetMasterBuildError
from onecool_os.assets.master import AssetMasterBuilder

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REFERENCE = datetime(2026, 7, 11, 8, 0, tzinfo=UTC)


def test_builder_updates_exact_cert_match_and_preserves_user_fields(tmp_path: Path) -> None:
    workbook = _write_workbook(
        tmp_path / "source.xlsx",
        [_row(cert="123", item="Old Item", subject="Old Player")],
    )
    collection = _write_collection(
        tmp_path / "collection.csv",
        [_collection_row(cert="123", item="New Item", subject="Shohei Ohtani")],
    )
    output = tmp_path / "asset_master.xlsx"

    result = AssetMasterBuilder().build(
        workbook,
        collection,
        output,
        reference_datetime=REFERENCE,
    )
    rows = _sheet_rows(output)

    assert result.latest_collection_count == 1
    assert result.final_unique_card_count == 1
    assert result.exact_cert_matches == 1
    assert rows[0]["Item"] == "New Item"
    assert rows[0]["Subject"] == "Shohei Ohtani"
    assert rows[0]["REF"] == "=IFERROR(1,0)"
    assert rows[0]["操作建議"] == "Keep"
    assert "LH_Sold=1" in rows[0]["eBay Sold Search URL"]
    assert "psacard.com/cert/123" in rows[0]["PSA URL"]


def test_builder_fallback_identity_updates_cert_without_duplicate(tmp_path: Path) -> None:
    workbook = _write_workbook(
        tmp_path / "source.xlsx",
        [_row(cert="OLD", year="2018", card_number="US1", subject="Shohei Ohtani")],
    )
    collection = _write_collection(
        tmp_path / "collection.csv",
        [
            _collection_row(
                cert="NEW",
                year="2018",
                card_number="US1",
                subject="Shohei Ohtani",
            )
        ],
    )
    output = tmp_path / "asset_master.xlsx"

    result = AssetMasterBuilder().build(
        workbook,
        collection,
        output,
        reference_datetime=REFERENCE,
    )
    rows = _sheet_rows(output)

    assert result.fallback_identity_matches == 1
    assert result.appended_cards == 0
    assert len(rows) == 1
    assert rows[0]["Cert Number"] == "NEW"


def test_builder_appends_new_card_with_generated_links_and_template_formulas(
    tmp_path: Path,
) -> None:
    workbook = _write_workbook(tmp_path / "source.xlsx", [_row(cert="123")])
    collection = _write_collection(
        tmp_path / "collection.csv",
        [
            _collection_row(cert="123"),
            _collection_row(cert="456", card_number="US285", subject="Shohei Ohtani"),
        ],
    )
    output = tmp_path / "asset_master.xlsx"

    result = AssetMasterBuilder().build(
        workbook,
        collection,
        output,
        reference_datetime=REFERENCE,
    )
    rows = _sheet_rows(output)
    sheet_xml = _read(output, "xl/worksheets/sheet1.xml").decode()

    assert result.appended_cards == 1
    assert rows[1]["Cert Number"] == "456"
    assert "LH_Sold=1" in rows[1]["eBay Sold Search URL"]
    assert "LH_Complete=1" in rows[1]["eBay Sold Search URL"]
    assert "psacard.com/cert/456" in rows[1]["PSA URL"]
    assert rows[1]["REF"] == "=IFERROR(1,0)"
    assert 's="7"' in sheet_xml


def test_builder_does_not_create_psa_url_for_bgs_and_preserves_black_label(
    tmp_path: Path,
) -> None:
    workbook = _write_workbook(tmp_path / "source.xlsx", [_row(cert="123")])
    collection = _write_collection(
        tmp_path / "collection.csv",
        [
            _collection_row(cert="123"),
            _collection_row(
                cert="BGS1",
                grade_issuer="BGS",
                grade="10 Black Label",
                subject="Kobe Bryant",
            ),
        ],
    )
    output = tmp_path / "asset_master.xlsx"

    result = AssetMasterBuilder().build(
        workbook,
        collection,
        output,
        reference_datetime=REFERENCE,
    )
    rows = _sheet_rows(output)

    assert result.bgs_cards == 1
    assert rows[1]["Grade Issuer"] == "BGS"
    assert rows[1]["Grade"] == "10 Black Label"
    assert "Black+Label" in rows[1]["eBay Sold Search URL"]
    assert rows[1]["PSA URL"] == ""


def test_builder_preserves_workbook_structure_and_replaces_sync_report(
    tmp_path: Path,
) -> None:
    workbook = _write_workbook(
        tmp_path / "source.xlsx",
        [_row(cert="123")],
        include_existing_sync_report=True,
    )
    collection = _write_collection(tmp_path / "collection.csv", [_collection_row(cert="123")])
    output = tmp_path / "asset_master.xlsx"

    AssetMasterBuilder().build(
        workbook,
        collection,
        output,
        reference_datetime=REFERENCE,
    )
    workbook_xml = _read(output, "xl/workbook.xml").decode()
    sheet_xml = _read(output, "xl/worksheets/sheet1.xml").decode()
    sync_report = _sync_report_rows(output)

    assert "Original Extra Sheet" in workbook_xml
    assert workbook_xml.count("Sync Report") == 1
    assert "<cols>" in sheet_xml
    assert "frozenSplit" in sheet_xml
    assert "autoFilter" in sheet_xml
    assert ["latest collection count", "1"] in sync_report


def test_builder_rejects_duplicate_collection_certs(tmp_path: Path) -> None:
    workbook = _write_workbook(tmp_path / "source.xlsx", [_row(cert="123")])
    collection = _write_collection(
        tmp_path / "collection.csv",
        [_collection_row(cert="123"), _collection_row(cert="123")],
    )

    with pytest.raises(AssetMasterBuildError, match="duplicate cert"):
        AssetMasterBuilder().build(
            workbook,
            collection,
            tmp_path / "asset_master.xlsx",
            reference_datetime=REFERENCE,
        )


def test_builder_missing_input_does_not_create_partial_output(tmp_path: Path) -> None:
    collection = _write_collection(tmp_path / "collection.csv", [_collection_row(cert="123")])
    output = tmp_path / "asset_master.xlsx"

    with pytest.raises(AssetMasterBuildError, match="Source workbook not found"):
        AssetMasterBuilder().build(
            tmp_path / "missing.xlsx",
            collection,
            output,
            reference_datetime=REFERENCE,
        )

    assert not output.exists()


def test_builder_does_not_mutate_source_workbook(tmp_path: Path) -> None:
    workbook = _write_workbook(tmp_path / "source.xlsx", [_row(cert="123")])
    before = workbook.read_bytes()
    collection = _write_collection(tmp_path / "collection.csv", [_collection_row(cert="123")])

    AssetMasterBuilder().build(
        workbook,
        collection,
        tmp_path / "asset_master.xlsx",
        reference_datetime=REFERENCE,
    )

    assert workbook.read_bytes() == before


def test_builder_supports_shared_string_headers_and_excel_numeric_identity(
    tmp_path: Path,
) -> None:
    workbook = _write_workbook(
        tmp_path / "source.xlsx",
        [
            _row(
                cert="1.1100372E8",
                grade="10.0",
                year="2018.0",
                card_number="1.0",
            )
        ],
        shared_strings=True,
    )
    collection = _write_collection(
        tmp_path / "collection.csv",
        [_collection_row(cert="111003720", grade="10", year="2018", card_number="1")],
    )
    output = tmp_path / "asset_master.xlsx"

    result = AssetMasterBuilder().build(
        workbook,
        collection,
        output,
        reference_datetime=REFERENCE,
    )
    rows = _sheet_rows(output)

    assert result.exact_cert_matches == 1
    assert rows[0]["Cert Number"] == "111003720"


def _row(
    *,
    cert: str,
    item: str = "2018 TOPPS UPDATE #US1 SHOHEI OHTANI",
    grade_issuer: str = "PSA",
    grade: str = "10",
    year: str = "2018",
    card_number: str = "US1",
    subject: str = "Shohei Ohtani",
) -> dict[str, str]:
    return {
        "Item": item,
        "Cert Number": cert,
        "Grade Issuer": grade_issuer,
        "Grade": grade,
        "Year": year,
        "Set": "TOPPS UPDATE",
        "Card Number": card_number,
        "Subject": subject,
        "Variety": "-",
        "My Cost": "100",
        "即時價格": "150",
        "Gain/Loss": "=K2-J2",
        "ROI": "=L2/J2",
        "Date Acquired": "2026-01-01",
        "REF": "=IFERROR(1,0)",
        "操作建議": "Keep",
        "eBay Sold Search URL": '=HYPERLINK("https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1","查看 eBay 成交")',
        "PSA URL": f'=HYPERLINK("https://www.psacard.com/cert/{cert}","點我查看 PSA 官方紀錄")',
    }


def _collection_row(
    *,
    cert: str,
    item: str = "2018 TOPPS UPDATE #US1 SHOHEI OHTANI",
    grade_issuer: str = "PSA",
    grade: str = "10",
    year: str = "2018",
    card_number: str = "US1",
    subject: str = "Shohei Ohtani",
) -> dict[str, str]:
    return {
        "Item": item,
        "Cert Number": cert,
        "Grade Issuer": grade_issuer,
        "Grade": grade,
        "Year": year,
        "Set": "TOPPS UPDATE",
        "Card Number": card_number,
        "Subject": subject,
        "Variety": "-",
        "My Cost": "100",
        "Date Acquired": "2026-01-01",
    }


def _write_collection(path: Path, rows: list[dict[str, str]]) -> Path:
    fieldnames = [
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
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_workbook(
    path: Path,
    rows: list[dict[str, str]],
    *,
    include_existing_sync_report: bool = False,
    shared_strings: bool = False,
) -> Path:
    headers = list(rows[0].keys())
    sheet_xml, shared_values = _worksheet_xml(headers, rows, shared_strings=shared_strings)
    content_types = _content_types(include_existing_sync_report)
    workbook = _workbook_xml(include_existing_sync_report)
    rels = _workbook_rels(include_existing_sync_report)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", _root_rels())
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        archive.writestr("xl/worksheets/sheet2.xml", _simple_sheet("Original Extra Sheet"))
        if include_existing_sync_report:
            archive.writestr("xl/worksheets/sheet3.xml", _simple_sheet("Old Sync Report"))
        if shared_strings:
            archive.writestr("xl/sharedStrings.xml", _shared_strings_xml(shared_values))
    return path


def _worksheet_xml(
    headers: list[str],
    rows: list[dict[str, str]],
    *,
    shared_strings: bool,
) -> tuple[str, list[str]]:
    shared_values: list[str] = []

    def cell(column: int, row: int, value: str, style: str = "") -> str:
        ref = f"{_column_name(column)}{row}"
        style_attr = f' s="{style}"' if style else ""
        if value.startswith("="):
            return f'<c r="{ref}"{style_attr}><f>{_escape(value[1:])}</f></c>'
        if shared_strings:
            shared_values.append(value)
            index = len(shared_values) - 1
            return f'<c r="{ref}" t="s"{style_attr}><v>{index}</v></c>'
        return f'<c r="{ref}" t="inlineStr"{style_attr}><is><t>{_escape(value)}</t></is></c>'

    header_cells = "".join(cell(index, 1, header) for index, header in enumerate(headers, 1))
    row_xml = [f'<row r="1">{header_cells}</row>']
    for row_index, row in enumerate(rows, 2):
        cells = "".join(
            cell(index, row_index, row.get(header, ""), style="7")
            for index, header in enumerate(headers, 1)
        )
        row_xml.append(f'<row r="{row_index}" ht="20" customHeight="1">{cells}</row>')
    xml = (
        f'<worksheet xmlns="{NS}" xmlns:r="{REL_NS}">'
        '<dimension ref="A1:S2"/>'
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" state="frozenSplit"/></sheetView></sheetViews>'
        '<cols><col min="1" max="1" width="40" customWidth="1"/></cols>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '<autoFilter ref="A1:S2"/>'
        "</worksheet>"
    )
    return xml, shared_values


def _sheet_rows(path: Path) -> list[dict[str, str]]:
    root = ElementTree.fromstring(_read(path, "xl/worksheets/sheet1.xml"))
    shared = _shared_strings(path)
    rows = root.find(f"{{{NS}}}sheetData").findall(f"{{{NS}}}row")
    headers = [
        _cell_value(cell, shared)
        for cell in rows[0].findall(f"{{{NS}}}c")
    ]
    parsed = []
    for row in rows[1:]:
        values = {}
        for cell in row.findall(f"{{{NS}}}c"):
            column = _column_index(cell.attrib["r"])
            if column - 1 < len(headers):
                values[headers[column - 1]] = _cell_value(cell, shared)
        parsed.append(values)
    return parsed


def _sync_report_rows(path: Path) -> list[list[str]]:
    workbook = ElementTree.fromstring(_read(path, "xl/workbook.xml"))
    rels = ElementTree.fromstring(_read(path, "xl/_rels/workbook.xml.rels"))
    sheets = workbook.find(f"{{{NS}}}sheets")
    rel_id = None
    for sheet in sheets.findall(f"{{{NS}}}sheet"):
        if sheet.attrib.get("name") == "Sync Report":
            rel_id = sheet.attrib[f"{{{REL_NS}}}id"]
    assert rel_id is not None
    target = None
    for rel in rels:
        if rel.attrib.get("Id") == rel_id:
            target = rel.attrib["Target"]
    assert target is not None
    root = ElementTree.fromstring(_read(path, f"xl/{target}"))
    parsed = []
    for row in root.find(f"{{{NS}}}sheetData").findall(f"{{{NS}}}row"):
        parsed.append([
            _cell_value(cell, ())
            for cell in row.findall(f"{{{NS}}}c")
        ])
    return parsed


def _cell_value(cell: ElementTree.Element, shared: tuple[str, ...]) -> str:
    formula = cell.find(f"{{{NS}}}f")
    if formula is not None:
        return f"={formula.text or ''}"
    value = cell.find(f"{{{NS}}}v")
    if cell.attrib.get("t") == "s" and value is not None:
        return shared[int(value.text or "0")]
    inline = cell.find(f"{{{NS}}}is/{{{NS}}}t")
    if inline is not None:
        return inline.text or ""
    return value.text if value is not None and value.text else ""


def _read(path: Path, entry: str) -> bytes:
    with zipfile.ZipFile(path, "r") as archive:
        return archive.read(entry)


def _shared_strings(path: Path) -> tuple[str, ...]:
    with zipfile.ZipFile(path, "r") as archive:
        if "xl/sharedStrings.xml" not in archive.namelist():
            return ()
        root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    return tuple(
        "".join(text.text or "" for text in item.iter(f"{{{NS}}}t"))
        for item in root.findall(f"{{{NS}}}si")
    )


def _content_types(include_existing_sync_report: bool) -> str:
    extra = (
        '<Override PartName="/xl/worksheets/sheet3.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        if include_existing_sync_report
        else ""
    )
    return (
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        f"{extra}</Types>"
    )


def _workbook_xml(include_existing_sync_report: bool) -> str:
    sync = '<sheet name="Sync Report" sheetId="3" r:id="rId3"/>' if include_existing_sync_report else ""
    return (
        f'<workbook xmlns="{NS}" xmlns:r="{REL_NS}"><sheets>'
        '<sheet name="Asset Master" sheetId="1" r:id="rId1"/>'
        '<sheet name="Original Extra Sheet" sheetId="2" r:id="rId2"/>'
        f"{sync}</sheets></workbook>"
    )


def _workbook_rels(include_existing_sync_report: bool) -> str:
    sync = (
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>'
        if include_existing_sync_report
        else ""
    )
    return (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
        f"{sync}</Relationships>"
    )


def _root_rels() -> str:
    return (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _simple_sheet(value: str) -> str:
    return (
        f'<worksheet xmlns="{NS}"><sheetData><row r="1"><c r="A1" t="inlineStr">'
        f"<is><t>{_escape(value)}</t></is></c></row></sheetData></worksheet>"
    )


def _shared_strings_xml(values: list[str]) -> str:
    items = "".join(f"<si><t>{_escape(value)}</t></si>" for value in values)
    return f'<sst xmlns="{NS}" count="{len(values)}" uniqueCount="{len(values)}">{items}</sst>'


def _escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name


def _column_index(cell_ref: str) -> int:
    letters = "".join(character for character in cell_ref if character.isalpha())
    index = 0
    for character in letters:
        index = index * 26 + (ord(character.upper()) - ord("A") + 1)
    return index
