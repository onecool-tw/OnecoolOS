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
    VALUATION_SOURCE_PRIORITY,
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
