import json
from decimal import Decimal
from pathlib import Path

from onecool_os.__main__ import main
from onecool_os.assets.real_estate.loader import (
    RealEstateLoader,
    RealEstateLoaderError,
)
from onecool_os.assets.real_estate.models import (
    RealEstateAsset,
    RealEstateError,
    RealEstatePosition,
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


def test_real_estate_asset_creation() -> None:
    real_estate = sample_real_estate_asset()
    asset = real_estate.to_asset()

    assert real_estate.asset_type == "REAL_ESTATE"
    assert real_estate.location_label() == "Taipei / Da'an"
    assert asset.asset_type == "REAL_ESTATE"
    assert asset.name == "Sample Taipei Apartment"


def test_real_estate_asset_rejects_invalid_area() -> None:
    try:
        RealEstateAsset(
            asset_id="bad",
            asset_type="REAL_ESTATE",
            name="Bad Property",
            country="Taiwan",
            city="Taipei",
            district="Da'an",
            address_label="Demo only",
            property_type="Apartment",
            currency="TWD",
            area_ping=Decimal("0"),
            building_age_years=Decimal("1"),
            floor=1,
            total_floors=5,
            has_parking=False,
        )
    except RealEstateError as exc:
        assert "Invalid area_ping" in str(exc)
    else:
        raise AssertionError("Invalid area should be rejected.")


def test_real_estate_position_creation() -> None:
    position = RealEstatePosition(
        asset=sample_real_estate_asset(),
        quantity=Decimal("1"),
        purchase_price=Decimal("28000000"),
        purchase_date="2026-01-10",
        current_estimated_value=Decimal("30500000"),
        notes="Demo only.",
    )

    assert position.quantity == Decimal("1")
    assert position.purchase_price == Decimal("28000000")
    assert position.unrealized_pnl() == Decimal("2500000")


def test_real_estate_loader_valid_json(tmp_path: Path) -> None:
    result = RealEstateLoader().load(write_real_estate_json(tmp_path))

    assert len(result.positions) == 2
    assert result.positions[0].asset.name == "Sample Taipei Apartment"
    assert result.positions[1].asset.city == "Taichung"


def test_real_estate_loader_invalid_json(tmp_path: Path) -> None:
    json_path = tmp_path / "real_estate.json"
    json_path.write_text("{invalid", encoding="utf-8")

    try:
        RealEstateLoader().load(json_path)
    except RealEstateLoaderError as exc:
        assert "Invalid real estate JSON" in str(exc)
    else:
        raise AssertionError("Invalid JSON should be rejected.")


def test_real_estate_loader_missing_fields(tmp_path: Path) -> None:
    payload = real_estate_json_payload()
    del payload["properties"][0]["city"]
    json_path = write_real_estate_json(tmp_path, payload)

    try:
        RealEstateLoader().load(json_path)
    except RealEstateLoaderError as exc:
        assert "Missing required field" in str(exc)
        assert "city" in str(exc)
    else:
        raise AssertionError("Missing fields should be rejected.")


def test_real_estate_loader_invalid_area(tmp_path: Path) -> None:
    payload = real_estate_json_payload()
    payload["properties"][0]["area_ping"] = "-1"
    json_path = write_real_estate_json(tmp_path, payload)

    try:
        RealEstateLoader().load(json_path)
    except RealEstateLoaderError as exc:
        assert "Invalid area_ping" in str(exc)
    else:
        raise AssertionError("Invalid area should be rejected.")


def test_real_estate_loader_invalid_price(tmp_path: Path) -> None:
    payload = real_estate_json_payload()
    payload["properties"][0]["purchase_price"] = "invalid"
    json_path = write_real_estate_json(tmp_path, payload)

    try:
        RealEstateLoader().load(json_path)
    except RealEstateLoaderError as exc:
        assert "Invalid purchase_price" in str(exc)
    else:
        raise AssertionError("Invalid price should be rejected.")


def test_cli_real_estate_demo_works(tmp_path: Path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))
    monkeypatch.chdir(Path(__file__).resolve().parents[1])

    assert main(["real-estate", "demo"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert len(payload["properties"]) == 2
    assert payload["properties"][0]["property_name"] == "Sample Taipei Apartment"
    assert payload["properties"][0]["city_district"] == "Taipei / Da'an"
    assert payload["properties"][0]["property_type"] == "Apartment"
    assert payload["properties"][0]["area"] == "32.50 ping"
    assert payload["properties"][0]["purchase_price"] == "28000000.00"
    assert payload["properties"][0]["current_estimated_value"] == "30500000.00"
    assert payload["properties"][0]["unrealized_pnl"] == "2500000.00"


def sample_real_estate_asset() -> RealEstateAsset:
    return RealEstateAsset(
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


def real_estate_json_payload() -> dict[str, object]:
    return {
        "properties": [
            {
                "asset_id": "REAL-ESTATE-DEMO-TAIPEI-001",
                "asset_type": "REAL_ESTATE",
                "name": "Sample Taipei Apartment",
                "country": "Taiwan",
                "city": "Taipei",
                "district": "Da'an",
                "address_label": "Demo address label only",
                "property_type": "Apartment",
                "currency": "TWD",
                "area_ping": "32.5",
                "building_age_years": "12",
                "floor": 8,
                "total_floors": 15,
                "has_parking": True,
                "quantity": "1",
                "purchase_price": "28000000",
                "purchase_date": "2026-01-10",
                "current_estimated_value": "30500000",
                "notes": "Sample property for demo only.",
            },
            {
                "asset_id": "REAL-ESTATE-DEMO-TAICHUNG-001",
                "asset_type": "REAL_ESTATE",
                "name": "Sample Taichung Studio",
                "country": "Taiwan",
                "city": "Taichung",
                "district": "Xitun",
                "address_label": "Demo district-level label only",
                "property_type": "Studio",
                "currency": "TWD",
                "area_ping": "18.2",
                "building_age_years": "6",
                "floor": 5,
                "total_floors": 12,
                "has_parking": False,
                "quantity": "1",
                "purchase_price": "9800000",
                "purchase_date": "2026-03-20",
                "current_estimated_value": "10200000",
                "notes": "Sample property for demo only.",
            },
        ],
    }


def write_real_estate_json(
    tmp_path: Path,
    payload: dict[str, object] | None = None,
) -> Path:
    json_path = tmp_path / "real_estate.json"
    json_path.write_text(
        json.dumps(payload or real_estate_json_payload()),
        encoding="utf-8",
    )
    return json_path
