import json
from decimal import Decimal
from pathlib import Path

from onecool_os.__main__ import main
from onecool_os.assets.securities.creator import SecurityCreator
from onecool_os.assets.securities.loader import (
    SecurityLoader,
    SecurityLoaderError,
)
from onecool_os.assets.securities.models import (
    SecurityAsset,
    SecurityError,
    SecurityPosition,
)


def write_settings(config_dir: Path, root_dir: Path) -> None:
    config_dir.mkdir(exist_ok=True)
    (config_dir / "settings.yaml").write_text(
        f"""
app:
  name: Onecool OS
  version: 0.6.1
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


def test_security_asset_creation() -> None:
    asset = sample_security_asset()

    assert asset.asset_id == "SECURITY-US-SPY"
    assert asset.symbol == "SPY"
    assert asset.asset_type == "ETF"
    assert asset.market == "US"
    assert asset.currency == "USD"


def test_security_asset_rejects_invalid_values() -> None:
    try:
        SecurityAsset(
            asset_id="bad",
            symbol="BAD",
            asset_type="MUTUAL_FUND",
            name="Bad Security",
            currency="USD",
            market="US",
        )
    except SecurityError as exc:
        assert "Unsupported security asset_type" in str(exc)
    else:
        raise AssertionError("Invalid security asset_type should be rejected.")


def test_security_position_total_cost() -> None:
    position = SecurityPosition(
        asset=sample_security_asset(),
        quantity=Decimal("10"),
        average_cost=Decimal("500"),
    )

    assert position.total_cost() == Decimal("5000")


def test_security_loader_template_loading() -> None:
    result = SecurityLoader().load("data/portfolio/securities.example.json")

    assert result.portfolio_name == "My Securities Portfolio"
    assert len(result.positions) == 1
    assert result.positions[0].asset.asset_id == "SECURITY-EXAMPLE-001"


def test_security_loader_valid_json(tmp_path: Path) -> None:
    result = SecurityLoader().load(write_securities_json(tmp_path))

    assert result.portfolio_name == "Securities"
    assert len(result.positions) == 2
    assert result.positions[0].total_cost() == Decimal("5000")


def test_security_loader_invalid_json(tmp_path: Path) -> None:
    json_path = tmp_path / "securities.json"
    json_path.write_text("{invalid", encoding="utf-8")

    try:
        SecurityLoader().load(json_path)
    except SecurityLoaderError as exc:
        assert "Invalid securities JSON" in str(exc)
    else:
        raise AssertionError("Invalid JSON should be rejected.")


def test_security_loader_missing_fields(tmp_path: Path) -> None:
    payload = securities_json_payload()
    del payload["positions"][0]["symbol"]
    json_path = write_securities_json(tmp_path, payload)

    try:
        SecurityLoader().load(json_path)
    except SecurityLoaderError as exc:
        assert "Missing required field" in str(exc)
        assert "symbol" in str(exc)
    else:
        raise AssertionError("Missing fields should be rejected.")


def test_security_loader_invalid_market(tmp_path: Path) -> None:
    payload = securities_json_payload()
    payload["positions"][0]["market"] = "HK"
    json_path = write_securities_json(tmp_path, payload)

    try:
        SecurityLoader().load(json_path)
    except SecurityLoaderError as exc:
        assert "Unsupported security market" in str(exc)
    else:
        raise AssertionError("Invalid market should be rejected.")


def test_security_loader_invalid_quantity(tmp_path: Path) -> None:
    payload = securities_json_payload()
    payload["positions"][0]["quantity"] = "0"
    json_path = write_securities_json(tmp_path, payload)

    try:
        SecurityLoader().load(json_path)
    except SecurityLoaderError as exc:
        assert "Invalid quantity" in str(exc)
    else:
        raise AssertionError("Invalid quantity should be rejected.")


def test_security_loader_rejects_duplicate_asset_id(tmp_path: Path) -> None:
    payload = securities_json_payload()
    payload["positions"][1]["asset_id"] = "SECURITY-US-SPY"
    json_path = write_securities_json(tmp_path, payload)

    try:
        SecurityLoader().load(json_path)
    except SecurityLoaderError as exc:
        assert "Duplicate asset_id" in str(exc)
    else:
        raise AssertionError("Duplicate asset_id should be rejected.")


def test_security_creator_creates_new_file(tmp_path: Path) -> None:
    json_path = tmp_path / "data" / "portfolio" / "securities.json"
    creator = SecurityCreator(
        input_func=scripted_input(
            [
                "My Securities",
                "SPY",
                "SPDR S&P 500 ETF Trust",
                "US",
                "ETF",
                "USD",
                "10",
                "500",
                "NYSEARCA",
                "United States",
                "",
                "Index",
                "Core ETF",
                "N",
            ]
        )
    )

    result = creator.create(json_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert result.status == "success"
    assert result.position_count == 1
    assert payload["positions"][0]["asset_id"] == "SECURITY-US-SPY"
    assert payload["positions"][0]["market"] == "US"


def test_security_creator_appends_existing_file(tmp_path: Path) -> None:
    json_path = write_securities_json(tmp_path)
    creator = SecurityCreator(
        input_func=scripted_input(
            [
                "1",
                "2330",
                "Taiwan Semiconductor",
                "TW",
                "STOCK",
                "TWD",
                "3",
                "600",
                "TWSE",
                "Taiwan",
                "Technology",
                "",
                "",
                "N",
            ]
        )
    )

    result = creator.create(json_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert result.status == "success"
    assert len(payload["positions"]) == 3
    assert payload["positions"][2]["asset_id"] == "SECURITY-TW-2330"


def test_security_creator_replaces_existing_file(tmp_path: Path) -> None:
    json_path = write_securities_json(tmp_path)
    creator = SecurityCreator(
        input_func=scripted_input(
            [
                "2",
                "Replacement Securities",
                "QQQ",
                "Invesco QQQ Trust",
                "US",
                "ETF",
                "USD",
                "4",
                "450",
                "",
                "",
                "",
                "Nasdaq",
                "",
                "N",
            ]
        )
    )

    result = creator.create(json_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert result.status == "success"
    assert payload["portfolio_name"] == "Replacement Securities"
    assert len(payload["positions"]) == 1
    assert payload["positions"][0]["asset_id"] == "SECURITY-US-QQQ"


def test_security_creator_validates_input(tmp_path: Path) -> None:
    json_path = tmp_path / "securities.json"
    creator = SecurityCreator(
        input_func=scripted_input(
            [
                "Validated Securities",
                "",
                "VT",
                "",
                "Vanguard Total World Stock ETF",
                "HK",
                "US",
                "FUND",
                "ETF",
                "EUR",
                "USD",
                "0",
                "5",
                "-1",
                "100",
                "",
                "",
                "",
                "",
                "",
                "N",
            ]
        )
    )

    result = creator.create(json_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert result.status == "success"
    assert payload["positions"][0]["symbol"] == "VT"
    assert payload["positions"][0]["market"] == "US"
    assert payload["positions"][0]["asset_type"] == "ETF"
    assert payload["positions"][0]["currency"] == "USD"
    assert payload["positions"][0]["quantity"] == "5"
    assert payload["positions"][0]["average_cost"] == "100"


def test_security_creator_prevents_duplicate_asset_id(tmp_path: Path) -> None:
    json_path = write_securities_json(tmp_path)
    creator = SecurityCreator(
        input_func=scripted_input(
            [
                "1",
                "SPY",
                "Duplicate SPY",
                "US",
                "ETF",
                "QQQM",
                "Invesco NASDAQ 100 ETF",
                "US",
                "ETF",
                "USD",
                "2",
                "200",
                "",
                "",
                "",
                "",
                "",
                "N",
            ]
        )
    )

    result = creator.create(json_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert result.status == "success"
    assert len(payload["positions"]) == 3
    assert payload["positions"][2]["asset_id"] == "SECURITY-US-QQQM"


def test_security_creator_cancel_flow_keeps_file(tmp_path: Path) -> None:
    json_path = write_securities_json(tmp_path)
    before = json_path.read_text(encoding="utf-8")
    creator = SecurityCreator(input_func=scripted_input(["3"]))

    result = creator.create(json_path)

    assert result.status == "cancelled"
    assert json_path.read_text(encoding="utf-8") == before


def test_cli_securities_import_works(tmp_path: Path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))
    json_path = write_securities_json(tmp_path)

    assert main(["securities", "import", str(json_path)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["portfolio_name"] == "Securities"
    assert payload["securities"][0]["security"] == "SPDR S&P 500 ETF Trust"
    assert payload["securities"][0]["symbol"] == "SPY"
    assert payload["securities"][0]["total_cost"] == "5000.00"


def test_cli_securities_import_missing_file_is_friendly(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))
    json_path = tmp_path / "data" / "portfolio" / "securities.json"

    assert main(["securities", "import", str(json_path)]) == 1
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "failure"
    assert "securities.example.json" in payload["error_message"]


def test_cli_securities_create_writes_default_real_file(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "builtins.input",
        scripted_input(
            [
                "CLI Securities",
                "VOO",
                "Vanguard S&P 500 ETF",
                "US",
                "ETF",
                "USD",
                "1",
                "500",
                "",
                "",
                "",
                "",
                "",
                "N",
            ]
        ),
    )

    assert main(["securities", "create"]) == 0
    payload = json.loads(capsys.readouterr().out)
    json_path = tmp_path / "data" / "portfolio" / "securities.json"

    assert payload["status"] == "success"
    assert payload["position_count"] == 1
    assert json_path.exists()


def sample_security_asset() -> SecurityAsset:
    return SecurityAsset(
        asset_id="SECURITY-US-SPY",
        symbol="spy",
        asset_type="etf",
        name="SPDR S&P 500 ETF Trust",
        currency="usd",
        market="us",
        exchange="NYSEARCA",
        country="United States",
        sector="Index",
        theme="S&P 500",
    )


def securities_json_payload() -> dict[str, object]:
    return {
        "portfolio_name": "Securities",
        "positions": [
            {
                "asset_id": "SECURITY-US-SPY",
                "symbol": "SPY",
                "asset_type": "ETF",
                "name": "SPDR S&P 500 ETF Trust",
                "currency": "USD",
                "market": "US",
                "exchange": "NYSEARCA",
                "country": "United States",
                "sector": "Index",
                "theme": "S&P 500",
                "quantity": "10",
                "average_cost": "500",
                "purchase_date": "2026-01-01",
                "notes": "Sample holding.",
            },
            {
                "asset_id": "SECURITY-TW-0050",
                "symbol": "0050",
                "asset_type": "ETF",
                "name": "Yuanta Taiwan Top 50 ETF",
                "currency": "TWD",
                "market": "TW",
                "exchange": "TWSE",
                "country": "Taiwan",
                "sector": "Index",
                "theme": "Taiwan",
                "quantity": "20",
                "average_cost": "150",
            },
        ],
    }


def write_securities_json(
    tmp_path: Path,
    payload: dict[str, object] | None = None,
) -> Path:
    json_path = tmp_path / "securities.json"
    json_path.write_text(
        json.dumps(payload or securities_json_payload()),
        encoding="utf-8",
    )
    return json_path


def scripted_input(values: list[str]):
    iterator = iter(values)

    def _input(_prompt: str) -> str:
        return next(iterator)

    return _input
