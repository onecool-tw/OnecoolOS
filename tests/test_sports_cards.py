import json
from decimal import Decimal
from pathlib import Path

from onecool_os.__main__ import main
from onecool_os.assets.sports_cards.loader import (
    CardLoader,
    CardLoaderError,
)
from onecool_os.assets.sports_cards.models import (
    CardAsset,
    CardError,
    CardPosition,
    SUPPORTED_INVENTORY_STATUSES,
    VALUATION_SOURCE_PRIORITY,
)
from onecool_os.assets.sports_cards.psa_csv import (
    PsaCsvImportError,
    PsaCsvImporter,
)


def write_settings(config_dir: Path, root_dir: Path) -> None:
    config_dir.mkdir(exist_ok=True)
    (config_dir / "settings.yaml").write_text(
        f"""
app:
  name: Onecool OS
  version: 0.5.0
  timezone: Asia/Taipei
  language: en
database:
  path: {root_dir / "onecool.sqlite3"}
paths:
  data_dir: {root_dir / "data"}
  cache_dir: {root_dir / "cache"}
  logs_dir: {root_dir / "logs"}
  exports_dir: {root_dir / "exports"}
runtime:
  debug: false
  environment: test
logging:
  level: INFO
""".strip(),
        encoding="utf-8",
    )


def test_card_asset_creation() -> None:
    card = sample_card_asset()
    asset = card.to_asset()

    assert card.player == "Michael Jordan"
    assert card.display_name() == "1986 Fleer Base #57"
    assert asset.asset_type == "SPORTS_CARD"
    assert asset.currency == "USD"


def test_card_asset_rejects_invalid_grade() -> None:
    try:
        CardAsset(
            asset_id="bad",
            player="Bad Grade",
            sport="Basketball",
            year="2026",
            brand="Sample",
            set="Base",
            card_number="1",
            grader="PSA",
            grade="11",
            parallel="",
            serial_number="",
            currency="USD",
        )
    except CardError as exc:
        assert "Invalid grade" in str(exc)
    else:
        raise AssertionError("Invalid grade should be rejected.")


def test_card_position_creation() -> None:
    position = CardPosition(
        asset=sample_card_asset(),
        quantity=Decimal("2"),
        purchase_price=Decimal("8500"),
        purchase_date="2026-01-15",
        notes="Sample note.",
    )

    assert position.quantity == Decimal("2")
    assert position.purchase_price == Decimal("8500")
    assert position.total_purchase_cost() == Decimal("17000")


def test_card_position_supports_inventory_metadata() -> None:
    position = CardPosition(
        asset=sample_card_asset(),
        quantity=Decimal("1"),
        purchase_price=Decimal("8500"),
        purchase_date="2026-01-15",
        notes="Sample note.",
        status="Owned",
        inventory_id="INV-PSA-12345678",
        cert_number="12345678",
        owned_quantity=Decimal("1"),
        available_quantity=Decimal("1"),
        listed_quantity=Decimal("0"),
        sold_quantity=Decimal("0"),
        location="Vault",
        cabinet="A",
        box="B1",
        row="R1",
        slot="S1",
        last_inventory_update="2026-01-16",
    )

    assert "Owned" in SUPPORTED_INVENTORY_STATUSES
    assert position.inventory_id == "INV-PSA-12345678"
    assert position.cert_number == "12345678"
    assert position.available_quantity == Decimal("1")
    assert position.location == "Vault"
    assert position.box == "B1"


def test_card_position_rejects_invalid_inventory_quantity() -> None:
    try:
        CardPosition(
            asset=sample_card_asset(),
            quantity=Decimal("1"),
            purchase_price=Decimal("8500"),
            purchase_date="2026-01-15",
            notes="Sample note.",
            owned_quantity=Decimal("1"),
            available_quantity=Decimal("1"),
            listed_quantity=Decimal("1"),
            sold_quantity=Decimal("0"),
        )
    except CardError as exc:
        assert "exceed owned_quantity" in str(exc)
    else:
        raise AssertionError(
            "Invalid inventory allocation should be rejected."
        )


def test_card_loader_valid_json(tmp_path: Path) -> None:
    result = CardLoader().load(write_cards_json(tmp_path))

    assert len(result.positions) == 3
    assert result.positions[0].asset.player == "Michael Jordan"
    assert result.positions[1].quantity == Decimal("2")


def test_card_loader_empty_live_portfolio(tmp_path: Path) -> None:
    json_path = tmp_path / "sports_cards.json"
    json_path.write_text(
        json.dumps(
            {
                "portfolio_name": "Onecool Sports Cards",
                "base_currency": "TWD",
                "cards": [],
            }
        ),
        encoding="utf-8",
    )

    result = CardLoader().load(json_path)

    assert result.portfolio_name == "Onecool Sports Cards"
    assert result.base_currency == "TWD"
    assert result.positions == ()


def test_card_loader_preserves_live_portfolio_metadata(
    tmp_path: Path,
) -> None:
    result = CardLoader().load(write_live_cards_json(tmp_path))
    position = result.positions[0]

    assert result.portfolio_name == "Live Cards"
    assert result.base_currency == "TWD"
    assert position.account == "Vault"
    assert position.asset_class == "Sports Card"
    assert position.status == "Owned"
    assert position.base_currency == "TWD"
    assert position.cost == Decimal("8500")
    assert position.purchase_platform == "Card Show"
    assert position.collection_type == "Investment"
    assert position.valuation_source == "eBay Sold"
    assert position.asset.grade_company == "PSA"
    assert position.inventory_id == "INV-CARD-JORDAN"
    assert position.cert_number == "87654321"
    assert position.owned_quantity == Decimal("1")
    assert position.available_quantity == Decimal("1")
    assert position.listed_quantity == Decimal("0")
    assert position.sold_quantity == Decimal("0")
    assert position.location == "Vault"
    assert position.cabinet == "A"
    assert position.box == "Box 1"
    assert position.row == "Row 1"
    assert position.slot == "Slot 1"
    assert position.last_inventory_update == "2026-01-16"


def test_card_import_output_includes_live_metadata(tmp_path: Path) -> None:
    result = CardLoader().load(write_live_cards_json(tmp_path))
    payload = card_import_output(result)

    assert payload["portfolio_name"] == "Live Cards"
    assert payload["base_currency"] == "TWD"
    assert payload["valuation_source_priority"] == list(
        VALUATION_SOURCE_PRIORITY
    )
    assert payload["cards"][0]["account"] == "Vault"
    assert payload["cards"][0]["cost"] == "8500.00"
    assert payload["cards"][0]["valuation_source"] == "eBay Sold"
    assert payload["cards"][0]["inventory_id"] == "INV-CARD-JORDAN"
    assert payload["cards"][0]["cert_number"] == "87654321"
    assert payload["cards"][0]["owned_quantity"] == "1.00"
    assert payload["cards"][0]["available_quantity"] == "1.00"
    assert payload["cards"][0]["location"] == "Vault"


def test_card_loader_invalid_json(tmp_path: Path) -> None:
    json_path = tmp_path / "cards.json"
    json_path.write_text("{invalid", encoding="utf-8")

    try:
        CardLoader().load(json_path)
    except CardLoaderError as exc:
        assert "Invalid cards JSON" in str(exc)
    else:
        raise AssertionError("Invalid JSON should be rejected.")


def test_card_loader_missing_fields(tmp_path: Path) -> None:
    payload = cards_json_payload()
    del payload["cards"][0]["player"]
    json_path = write_cards_json(tmp_path, payload)

    try:
        CardLoader().load(json_path)
    except CardLoaderError as exc:
        assert "Missing required field" in str(exc)
        assert "player" in str(exc)
    else:
        raise AssertionError("Missing fields should be rejected.")


def test_card_loader_invalid_grade(tmp_path: Path) -> None:
    payload = cards_json_payload()
    payload["cards"][0]["grade"] = "Gem"
    json_path = write_cards_json(tmp_path, payload)

    try:
        CardLoader().load(json_path)
    except CardLoaderError as exc:
        assert "Invalid grade" in str(exc)
    else:
        raise AssertionError("Invalid grade should be rejected.")


def test_card_loader_invalid_quantity(tmp_path: Path) -> None:
    payload = cards_json_payload()
    payload["cards"][0]["quantity"] = "0"
    json_path = write_cards_json(tmp_path, payload)

    try:
        CardLoader().load(json_path)
    except CardLoaderError as exc:
        assert "Invalid quantity" in str(exc)
    else:
        raise AssertionError("Invalid quantity should be rejected.")


def test_card_loader_rejects_invalid_status(tmp_path: Path) -> None:
    payload = live_cards_json_payload()
    payload["cards"][0]["status"] = "Unknown"
    json_path = write_live_cards_json(tmp_path, payload)

    try:
        CardLoader().load(json_path)
    except CardLoaderError as exc:
        assert "Unsupported card status" in str(exc)
    else:
        raise AssertionError("Invalid status should be rejected.")


def test_card_loader_rejects_invalid_collection_type(tmp_path: Path) -> None:
    payload = live_cards_json_payload()
    payload["cards"][0]["collection_type"] = "Speculation"
    json_path = write_live_cards_json(tmp_path, payload)

    try:
        CardLoader().load(json_path)
    except CardLoaderError as exc:
        assert "Unsupported collection_type" in str(exc)
    else:
        raise AssertionError("Invalid collection_type should be rejected.")


def test_card_loader_rejects_invalid_valuation_source(tmp_path: Path) -> None:
    payload = live_cards_json_payload()
    payload["cards"][0]["valuation_source"] = "Unknown"
    json_path = write_live_cards_json(tmp_path, payload)

    try:
        CardLoader().load(json_path)
    except CardLoaderError as exc:
        assert "Unsupported valuation_source" in str(exc)
    else:
        raise AssertionError("Invalid valuation_source should be rejected.")


def test_cli_cards_demo_works(tmp_path: Path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))
    monkeypatch.chdir(Path(__file__).resolve().parents[1])

    assert main(["cards", "demo"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert len(payload["cards"]) == 3
    assert payload["cards"][0]["player"] == "Michael Jordan"
    assert payload["cards"][0]["card"] == "1986 Fleer Base #57"
    assert payload["cards"][0]["grade"] == "PSA 9"
    assert payload["cards"][0]["quantity"] == "1.00"
    assert payload["cards"][0]["purchase_price"] == "8500.00"


def test_cli_cards_import_works(tmp_path: Path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))
    json_path = write_live_cards_json(tmp_path)

    assert main(["cards", "import", str(json_path)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["portfolio_name"] == "Live Cards"
    assert payload["cards"][0]["player"] == "Michael Jordan"
    assert payload["cards"][0]["grade_company"] == "PSA"


def test_psa_csv_import_creates_live_portfolio(tmp_path: Path) -> None:
    csv_path = write_psa_csv(tmp_path)
    output_path = tmp_path / "sports_cards.json"

    result = PsaCsvImporter().import_csv(csv_path, output_path)
    loaded = CardLoader().load(output_path)
    position = loaded.positions[0]

    assert result.imported_count == 1
    assert result.skipped_duplicates == 0
    assert result.total_cards == 1
    assert loaded.portfolio_name == "Onecool Sports Cards"
    assert loaded.base_currency == "TWD"
    assert position.asset.asset_id == "PSA-12345678"
    assert position.asset.player == "Shohei Ohtani"
    assert position.asset.serial_number == "12345678"
    assert position.status == "Owned"
    assert position.collection_type == "Investment"
    assert position.valuation_source == "eBay Sold"
    assert position.cost == Decimal("125.50")
    assert position.purchase_platform == "PSA Collection"
    assert position.inventory_id == "INV-PSA-12345678"
    assert position.cert_number == "12345678"
    assert position.owned_quantity == Decimal("1")
    assert position.available_quantity == Decimal("1")
    assert position.listed_quantity == Decimal("0")
    assert position.sold_quantity == Decimal("0")
    assert position.last_inventory_update == "2026-01-15"


def test_psa_csv_import_does_not_overwrite_existing_cards(
    tmp_path: Path,
) -> None:
    output_path = write_live_cards_json(tmp_path)
    csv_path = write_psa_csv(tmp_path)

    result = PsaCsvImporter().import_csv(csv_path, output_path)
    loaded = CardLoader().load(output_path)

    assert result.imported_count == 1
    assert result.total_cards == 2
    assert loaded.positions[0].asset.player == "Michael Jordan"
    assert loaded.positions[1].asset.player == "Shohei Ohtani"


def test_psa_csv_import_skips_duplicate_cert_number(tmp_path: Path) -> None:
    csv_path = write_psa_csv(
        tmp_path,
        rows=[
            psa_csv_row(cert_number="12345678"),
            psa_csv_row(cert_number="12345678"),
        ],
    )
    output_path = tmp_path / "sports_cards.json"

    result = PsaCsvImporter().import_csv(csv_path, output_path)
    loaded = CardLoader().load(output_path)

    assert result.imported_count == 1
    assert result.skipped_duplicates == 1
    assert len(loaded.positions) == 1


def test_psa_csv_import_rejects_missing_field(tmp_path: Path) -> None:
    csv_path = tmp_path / "psa.csv"
    csv_path.write_text(
        "Item,Subject\nSample Card,Shohei Ohtani\n",
        encoding="utf-8",
    )

    try:
        PsaCsvImporter().import_csv(csv_path, tmp_path / "sports_cards.json")
    except PsaCsvImportError as exc:
        assert "Missing PSA CSV field" in str(exc)
        assert "Cert Number" in str(exc)
    else:
        raise AssertionError("Missing PSA CSV fields should be rejected.")


def test_cli_cards_import_csv_works(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))
    monkeypatch.chdir(tmp_path)
    csv_path = write_psa_csv(tmp_path)

    assert main(["cards", "import-csv", str(csv_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    loaded = CardLoader().load(tmp_path / "data/portfolio/sports_cards.json")

    assert payload["status"] == "success"
    assert payload["imported_count"] == 1
    assert payload["output_path"] == "data/portfolio/sports_cards.json"
    assert loaded.positions[0].asset.player == "Shohei Ohtani"


def sample_card_asset() -> CardAsset:
    return CardAsset(
        asset_id="CARD-JORDAN-1986-FLEER-57-PSA9",
        player="Michael Jordan",
        sport="Basketball",
        year="1986",
        brand="Fleer",
        set="Base",
        card_number="57",
        grader="PSA",
        grade="9",
        parallel="",
        serial_number="",
        currency="USD",
    )


def cards_json_payload() -> dict[str, object]:
    return {
        "cards": [
            {
                "asset_id": "CARD-JORDAN-1986-FLEER-57-PSA9",
                "player": "Michael Jordan",
                "sport": "Basketball",
                "year": "1986",
                "brand": "Fleer",
                "set": "Base",
                "card_number": "57",
                "grader": "PSA",
                "grade": "9",
                "parallel": "",
                "serial_number": "",
                "currency": "USD",
                "quantity": "1",
                "purchase_price": "8500",
                "purchase_date": "2026-01-15",
                "notes": "Sample card for demo only.",
            },
            {
                "asset_id": "CARD-OHTANI-2018-TOPPS-700-PSA10",
                "player": "Shohei Ohtani",
                "sport": "Baseball",
                "year": "2018",
                "brand": "Topps",
                "set": "Update",
                "card_number": "700",
                "grader": "PSA",
                "grade": "10",
                "parallel": "Rookie Debut",
                "serial_number": "",
                "currency": "USD",
                "quantity": "2",
                "purchase_price": "300",
                "purchase_date": "2026-02-10",
                "notes": "Sample card for demo only.",
            },
            {
                "asset_id": "CARD-MESSI-2004-MEGA-71-SGC9",
                "player": "Lionel Messi",
                "sport": "Soccer",
                "year": "2004",
                "brand": "Panini",
                "set": "Mega Cracks",
                "card_number": "71",
                "grader": "SGC",
                "grade": "9",
                "parallel": "",
                "serial_number": "",
                "currency": "USD",
                "quantity": "1",
                "purchase_price": "1200",
                "purchase_date": "2026-03-05",
                "notes": "Sample card for demo only.",
            },
        ],
    }


def live_cards_json_payload() -> dict[str, object]:
    return {
        "portfolio_name": "Live Cards",
        "base_currency": "TWD",
        "cards": [
            {
                "account": "Vault",
                "asset_class": "Sports Card",
                "status": "Owned",
                "currency": "USD",
                "base_currency": "TWD",
                "cost": "8500",
                "inventory_id": "INV-CARD-JORDAN",
                "cert_number": "87654321",
                "owned_quantity": "1",
                "available_quantity": "1",
                "listed_quantity": "0",
                "sold_quantity": "0",
                "location": "Vault",
                "cabinet": "A",
                "box": "Box 1",
                "row": "Row 1",
                "slot": "Slot 1",
                "last_inventory_update": "2026-01-16",
                "asset_id": "CARD-JORDAN-1986-FLEER-57-PSA9",
                "player": "Michael Jordan",
                "year": "1986",
                "sport": "Basketball",
                "brand": "Fleer",
                "set": "Base",
                "card_number": "57",
                "parallel": "",
                "serial_number": "",
                "grade_company": "PSA",
                "grade": "9",
                "purchase_date": "2026-01-15",
                "purchase_platform": "Card Show",
                "collection_type": "Investment",
                "valuation_source": "eBay Sold",
                "notes": "Sample live card.",
            }
        ],
    }


def write_cards_json(
    tmp_path: Path,
    payload: dict[str, object] | None = None,
) -> Path:
    json_path = tmp_path / "cards.json"
    json_path.write_text(
        json.dumps(payload or cards_json_payload()),
        encoding="utf-8",
    )
    return json_path


def write_live_cards_json(
    tmp_path: Path,
    payload: dict[str, object] | None = None,
) -> Path:
    json_path = tmp_path / "sports_cards.json"
    json_path.write_text(
        json.dumps(payload or live_cards_json_payload()),
        encoding="utf-8",
    )
    return json_path


def card_import_output(result):
    from onecool_os.assets.sports_cards.loader import card_import_to_dict

    return card_import_to_dict(result)


def write_psa_csv(
    tmp_path: Path,
    rows: list[dict[str, str]] | None = None,
) -> Path:
    csv_path = tmp_path / "psa.csv"
    fieldnames = [
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
    ]
    csv_rows = rows or [psa_csv_row()]
    lines = [",".join(fieldnames)]
    lines.extend(
        ",".join(row[field] for field in fieldnames)
        for row in csv_rows
    )
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path


def psa_csv_row(cert_number: str = "12345678") -> dict[str, str]:
    return {
        "Item": "2018 Topps Chrome Shohei Ohtani #150",
        "Subject": "Shohei Ohtani",
        "Year": "2018",
        "Set": "Topps Chrome",
        "Card Number": "150",
        "Grade Issuer": "PSA",
        "Grade": "10",
        "Cert Number": cert_number,
        "My Cost": "125.50",
        "Date Acquired": "2026-01-15",
        "Source": "PSA Collection",
        "My Notes": "CSV import sample",
    }
