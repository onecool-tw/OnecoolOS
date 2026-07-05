import csv
import json
from datetime import datetime
from datetime import timezone
from pathlib import Path

from onecool_os.connectors import ImportAudit
from onecool_os.connectors.collectibles import CollectibleMarketRecord
from onecool_os.connectors.collectibles import CollectibleMarketSource
from onecool_os.connectors.collectibles import EbaySoldManualImporter
from onecool_os.connectors.collectibles import source_role_for_source


REFERENCE = datetime(2026, 7, 5, tzinfo=timezone.utc)


def test_ebay_sold_valid_csv_import(tmp_path: Path) -> None:
    path = write_csv(tmp_path, [ebay_row()])

    result = EbaySoldManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.imported_rows == 1
    assert result.summary.invalid_rows == 0
    assert isinstance(result.records[0], CollectibleMarketRecord)
    assert result.records[0].source == CollectibleMarketSource.EBAY_SOLD
    assert result.records[0].external_id == "EBAY-001"
    assert result.records[0].sale_price is not None
    assert result.records[0].raw_payload["source_role"] == (
        "PRIMARY_MARKET_PRICE"
    )


def test_ebay_sold_valid_json_import(tmp_path: Path) -> None:
    path = tmp_path / "ebay.json"
    path.write_text(
        json.dumps({"records": [ebay_row(external_id="EBAY-JSON-1")]}),
        encoding="utf-8",
    )

    result = EbaySoldManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.imported_rows == 1
    assert result.records[0].external_id == "EBAY-JSON-1"
    assert result.records[0].currency == "USD"


def test_ebay_sold_missing_sale_price(tmp_path: Path) -> None:
    result = import_one(tmp_path, sale_price="")

    assert result.summary.imported_rows == 0
    assert result.summary.invalid_rows == 1
    assert "sale_price" in result.summary.warnings[0]


def test_ebay_sold_missing_currency(tmp_path: Path) -> None:
    result = import_one(tmp_path, currency="")

    assert result.summary.invalid_rows == 1
    assert "currency" in result.summary.warnings[0]


def test_ebay_sold_missing_sale_date(tmp_path: Path) -> None:
    result = import_one(tmp_path, sale_date="")

    assert result.summary.invalid_rows == 1
    assert "sale_date" in result.summary.warnings[0]


def test_ebay_sold_missing_external_id_or_url(tmp_path: Path) -> None:
    result = import_one(tmp_path, external_id="", url="", reference="")

    assert result.summary.invalid_rows == 1
    assert "external_id or url/reference" in result.summary.warnings[0]


def test_ebay_sold_missing_asset_id_or_asset_hint(tmp_path: Path) -> None:
    result = import_one(
        tmp_path,
        asset_id="",
        player="",
        year="",
        brand="",
        card_number="",
        grade_company="",
        grade="",
        title="",
        asset_hint="",
    )

    assert result.summary.invalid_rows == 1
    assert "asset_id or asset_hint" in result.summary.warnings[0]


def test_ebay_sold_negative_sale_price(tmp_path: Path) -> None:
    result = import_one(tmp_path, sale_price="-1")

    assert result.summary.invalid_rows == 1
    assert "sale_price" in result.summary.warnings[0]


def test_ebay_sold_invalid_date(tmp_path: Path) -> None:
    result = import_one(tmp_path, sale_date="not-a-date")

    assert result.summary.invalid_rows == 1
    assert "sale_date" in result.summary.warnings[0]


def test_ebay_sold_duplicate_external_id(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        [ebay_row(external_id="DUP-1"), ebay_row(external_id="DUP-1")],
    )

    result = EbaySoldManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.imported_rows == 1
    assert result.summary.duplicate_rows == 1
    assert result.summary.skipped_rows == 1
    assert "Duplicate eBay external_id" in result.summary.warnings[0]


def test_ebay_sold_duplicate_url(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        [
            ebay_row(external_id="EBAY-1", url="https://example.test/sold/1"),
            ebay_row(external_id="EBAY-2", url="https://example.test/sold/1"),
        ],
    )

    result = EbaySoldManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.imported_rows == 1
    assert result.summary.duplicate_rows == 1
    assert "Duplicate eBay url/reference" in result.summary.warnings[0]


def test_ebay_sold_import_summary(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        [
            ebay_row(external_id="EBAY-1"),
            ebay_row(external_id="EBAY-1"),
            ebay_row(sale_price=""),
        ],
    )

    result = EbaySoldManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert result.summary.to_dict() == {
        "imported_rows": 1,
        "skipped_rows": 1,
        "duplicate_rows": 1,
        "invalid_rows": 1,
        "warnings": [
            "Duplicate eBay external_id at row 3: EBAY-1",
            "Missing eBay Sold value at row 4: sale_price",
        ],
    }


def test_ebay_sold_import_audit(tmp_path: Path) -> None:
    path = write_csv(tmp_path, [ebay_row()])

    result = EbaySoldManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert isinstance(result.audit, ImportAudit)
    assert result.audit.source == "EBAY_SOLD"
    assert result.audit.source_filename == "ebay.csv"
    assert result.audit.total_rows == 1
    assert result.audit.imported_rows == 1
    assert result.audit.checksum is not None
    assert "raw_payload" not in result.audit.to_dict()


def test_ebay_sold_injected_reference_datetime(tmp_path: Path) -> None:
    reference = datetime(2026, 8, 1, tzinfo=timezone.utc)
    path = write_csv(tmp_path, [ebay_row()])

    result = EbaySoldManualImporter().import_file(
        path,
        reference_datetime=reference,
    )

    assert result.audit.reference_datetime == reference
    assert result.audit.imported_at == reference


def test_ebay_sold_checksum_if_applicable(tmp_path: Path) -> None:
    path = write_csv(tmp_path, [ebay_row()])

    result = EbaySoldManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )

    assert len(result.audit.checksum) == 64


def test_ebay_sold_no_mutation(tmp_path: Path) -> None:
    path = write_csv(tmp_path, [ebay_row()])
    before = path.read_text(encoding="utf-8")

    EbaySoldManualImporter().import_file(path, reference_datetime=REFERENCE)

    assert path.read_text(encoding="utf-8") == before


def test_ebay_sold_collectible_market_record_output(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        [
            ebay_row(
                shipping="8.00",
                buyer_country="US",
                seller_country="JP",
                raw_payload='{"condition": "graded"}',
                note="Manual export",
                tags="ebay,primary",
            )
        ],
    )

    result = EbaySoldManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )
    record = result.records[0]

    assert record.to_dict()["source"] == "EBAY_SOLD"
    assert record.raw_payload["shipping"] == "8.00"
    assert record.raw_payload["buyer_country"] == "US"
    assert record.raw_payload["seller_country"] == "JP"
    assert record.raw_payload["note"] == "Manual export"
    assert record.raw_payload["tags"] == ["ebay", "primary"]
    assert record.raw_payload["condition"] == "graded"


def test_ebay_sold_source_role_is_primary_market_price() -> None:
    assert source_role_for_source(
        CollectibleMarketSource.EBAY_SOLD
    ).value == "PRIMARY_MARKET_PRICE"


def import_one(tmp_path: Path, **overrides):
    path = write_csv(tmp_path, [ebay_row(**overrides)])
    return EbaySoldManualImporter().import_file(
        path,
        reference_datetime=REFERENCE,
    )


def write_csv(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "ebay.csv"
    columns = [
        "external_id",
        "asset_id",
        "asset_hint",
        "sale_price",
        "currency",
        "sale_date",
        "source",
        "url",
        "reference",
        "title",
        "player",
        "year",
        "brand",
        "card_number",
        "grade_company",
        "grade",
        "shipping",
        "buyer_country",
        "seller_country",
        "raw_payload",
        "note",
        "tags",
    ]
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


def ebay_row(
    *,
    external_id: str = "EBAY-001",
    asset_id: str = "CARD-GOLDEN-OHTANI-US1-PSA10",
    asset_hint: str = "",
    sale_price: str = "300.00",
    currency: str = "USD",
    sale_date: str = "2026-07-04",
    source: str = "EBAY_SOLD",
    url: str = "https://example.test/ebay/EBAY-001",
    reference: str = "",
    title: str = "2018 Topps Update Shohei Ohtani US1 PSA 10",
    player: str = "Shohei Ohtani",
    year: str = "2018",
    brand: str = "Topps Update",
    card_number: str = "US1",
    grade_company: str = "PSA",
    grade: str = "10",
    shipping: str = "",
    buyer_country: str = "",
    seller_country: str = "",
    raw_payload: str = "",
    note: str = "",
    tags: str = "",
) -> dict[str, str]:
    return {
        "external_id": external_id,
        "asset_id": asset_id,
        "asset_hint": asset_hint,
        "sale_price": sale_price,
        "currency": currency,
        "sale_date": sale_date,
        "source": source,
        "url": url,
        "reference": reference,
        "title": title,
        "player": player,
        "year": year,
        "brand": brand,
        "card_number": card_number,
        "grade_company": grade_company,
        "grade": grade,
        "shipping": shipping,
        "buyer_country": buyer_country,
        "seller_country": seller_country,
        "raw_payload": raw_payload,
        "note": note,
        "tags": tags,
    }
