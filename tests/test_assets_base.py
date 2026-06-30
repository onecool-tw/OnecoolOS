import json
from decimal import Decimal
from pathlib import Path

from onecool_os.__main__ import main
from onecool_os.assets.base import BaseAsset, BasePosition
from onecool_os.assets.cash.loader import CashLoader
from onecool_os.assets.cash.models import CashAsset
from onecool_os.assets.funds.loader import FundLoader
from onecool_os.assets.funds.models import FundAsset
from onecool_os.assets.real_estate.loader import RealEstateLoader
from onecool_os.assets.real_estate.models import RealEstateAsset
from onecool_os.assets.sports_cards.loader import CardLoader
from onecool_os.assets.sports_cards.models import CardAsset


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


def test_base_asset_creation() -> None:
    asset = BaseAsset(
        asset_id="asset-1",
        asset_type="OTHER",
        name="Generic Asset",
        currency="USD",
    )

    assert asset.asset_id == "asset-1"
    assert asset.asset_type == "OTHER"
    assert asset.name == "Generic Asset"
    assert asset.currency == "USD"
    assert asset.created_at is None
    assert asset.updated_at is None


def test_base_position_creation() -> None:
    asset = BaseAsset(
        asset_id="asset-1",
        asset_type="OTHER",
        name="Generic Asset",
        currency="USD",
    )
    position = BasePosition(asset=asset, notes="Base note.")

    assert position.asset is asset
    assert position.notes == "Base note."
    assert position.metadata()["asset_type"] == "OTHER"


def test_fund_asset_is_compatible_with_base_asset() -> None:
    asset = FundAsset(
        asset_id="FUND-US-GROWTH",
        symbol="USGROWTH",
        asset_type="MUTUAL_FUND",
        name="Sample US Growth Fund",
        currency="USD",
    )

    assert isinstance(asset, BaseAsset)
    assert asset.asset_type == "MUTUAL_FUND"


def test_card_asset_is_compatible_with_base_asset() -> None:
    asset = CardAsset(
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

    assert isinstance(asset, BaseAsset)
    assert asset.asset_type == "SPORTS_CARD"
    assert asset.name == "Michael Jordan 1986 Fleer Base #57"


def test_real_estate_asset_is_compatible_with_base_asset() -> None:
    asset = RealEstateAsset(
        asset_id="REAL-ESTATE-DEMO-TAIPEI-001",
        asset_type="REAL_ESTATE",
        name="Sample Taipei Apartment",
        country="Taiwan",
        city="Taipei",
        district="Da'an",
        address_label="Demo address label only",
        property_type="Apartment",
        currency="TWD",
        area_ping=Decimal("32.5"),
        building_age_years=Decimal("12"),
        floor=8,
        total_floors=15,
        has_parking=True,
    )

    assert isinstance(asset, BaseAsset)
    assert asset.asset_type == "REAL_ESTATE"


def test_cash_asset_is_compatible_with_base_asset() -> None:
    asset = CashAsset(
        asset_id="CASH-TWD-DEMO",
        asset_type="CASH",
        name="Demo TWD Cash",
        currency="TWD",
        account_type="checking",
    )

    assert isinstance(asset, BaseAsset)
    assert asset.asset_type == "CASH"


def test_existing_asset_loaders_still_work() -> None:
    root = Path(__file__).resolve().parents[1]

    assert len(FundLoader().load(root / "examples/funds_demo.json").positions) == 2
    assert len(CardLoader().load(root / "examples/cards_demo.json").positions) == 3
    assert len(
        RealEstateLoader().load(root / "examples/real_estate_demo.json").positions
    ) == 2
    assert len(CashLoader().load(root / "examples/cash_demo.json").positions) == 2


def test_existing_asset_cli_commands_still_work(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))
    monkeypatch.chdir(Path(__file__).resolve().parents[1])

    assert main(["cash", "demo"]) == 0
    assert json.loads(capsys.readouterr().out)["cash_accounts"]

    assert main(["cards", "demo"]) == 0
    assert json.loads(capsys.readouterr().out)["cards"]

    assert main(["real-estate", "demo"]) == 0
    assert json.loads(capsys.readouterr().out)["properties"]

    assert main(["funds", "import", "examples/funds_demo.json"]) == 0
    assert json.loads(capsys.readouterr().out)["funds"]
