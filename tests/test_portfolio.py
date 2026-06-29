import json
from decimal import Decimal
from pathlib import Path

from onecool_os.__main__ import main
from onecool_os.core.config import (
    ApplicationSettings,
    DatabaseSettings,
    LoggingSettings,
    PathSettings,
    RuntimeSettings,
    SystemConfig,
)
from onecool_os.portfolio.engine import PortfolioEngine
from onecool_os.portfolio.loader import PortfolioLoader, PortfolioLoaderError
from onecool_os.portfolio.models import Asset, Portfolio, PortfolioError, Position
from onecool_os.portfolio.registry import PortfolioRegistry


def build_config(tmp_path: Path) -> SystemConfig:
    return SystemConfig(
        app=ApplicationSettings(
            name="Onecool OS",
            version="0.4.0",
            timezone="Asia/Taipei",
            language="en",
        ),
        database=DatabaseSettings(path=tmp_path / "onecool.sqlite3"),
        paths=PathSettings(
            data_dir=tmp_path / "data",
            cache_dir=tmp_path / "cache",
            logs_dir=tmp_path / "logs",
            exports_dir=tmp_path / "exports",
        ),
        runtime=RuntimeSettings(debug=False, environment="test"),
        logging=LoggingSettings(level="INFO"),
    )


def write_settings(config_dir: Path, root_dir: Path) -> None:
    config_dir.mkdir(exist_ok=True)
    (config_dir / "settings.yaml").write_text(
        f"""
app:
  name: Onecool OS
  version: 0.4.0
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


def test_portfolio_creation() -> None:
    portfolio = Portfolio(portfolio_id="main", name="Main")

    assert portfolio.portfolio_id == "main"
    assert portfolio.name == "Main"
    assert portfolio.list_positions() == ()


def test_asset_type_validation() -> None:
    try:
        Asset(
            asset_id="bad",
            symbol="BAD",
            asset_type="invalid",
            name="Invalid",
            currency="USD",
        )
    except PortfolioError as exc:
        assert "Unsupported asset_type" in str(exc)
    else:
        raise AssertionError("Invalid asset_type should be rejected.")


def test_symbol_field_exists() -> None:
    asset = Asset(
        asset_id="spy",
        symbol="spy",
        asset_type="ETF",
        name="SPDR S&P 500 ETF Trust",
        currency="USD",
    )

    assert asset.symbol == "SPY"


def test_add_remove_position() -> None:
    portfolio = Portfolio(portfolio_id="main", name="Main")
    position = sample_position()

    portfolio.add_position(position)
    removed = portfolio.remove_position(position.asset.asset_id)

    assert removed == position
    assert portfolio.list_positions() == ()


def test_market_value_calculation() -> None:
    position = sample_position()

    assert position.market_value() == Decimal("1500")


def test_pnl_calculation() -> None:
    position = sample_position()

    assert position.unrealized_pnl() == Decimal("500")


def test_registry_functions() -> None:
    registry = PortfolioRegistry()

    portfolio = registry.create_portfolio("main", "Main")

    assert registry.get_portfolio("main") is portfolio
    assert registry.list_portfolios() == (portfolio,)


def test_cli_portfolio_status(tmp_path: Path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))

    assert main(["portfolio", "status"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["engine_status"] == "ready"
    assert payload["portfolio_count"] == 0
    assert payload["position_count"] == 0


def test_portfolio_demo_command_runs(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))

    assert main(["portfolio", "demo"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert len(payload["positions"]) == 3


def test_portfolio_demo_includes_portfolio_name(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))

    assert main(["portfolio", "demo"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["portfolio_name"] == "Demo Portfolio"


def test_portfolio_demo_includes_total_market_value(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))

    assert main(["portfolio", "demo"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["total_market_value"] == "8645.00"


def test_portfolio_demo_includes_unrealized_pnl(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))

    assert main(["portfolio", "demo"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["total_unrealized_pnl"] == "745.00"
    assert "unrealized_pnl" in payload["positions"][0]


def test_portfolio_demo_output_shows_normalized_model(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))

    assert main(["portfolio", "demo"]) == 0
    payload = json.loads(capsys.readouterr().out)

    positions = {position["symbol"]: position for position in payload["positions"]}
    assert positions["SPY"]["asset_type"] == "ETF"
    assert positions["QQQ"]["asset_type"] == "ETF"
    assert positions["GLD"]["asset_type"] == "ETF"


def test_portfolio_demo_does_not_require_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr("socket.create_connection", fail_network)

    assert main(["portfolio", "demo"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["portfolio_name"] == "Demo Portfolio"


def test_portfolio_demo_does_not_write_files(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))

    assert main(["portfolio", "demo"]) == 0
    capsys.readouterr()
    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    assert after == before


def test_portfolio_engine_status_counts_positions(tmp_path: Path) -> None:
    registry = PortfolioRegistry()
    portfolio = registry.create_portfolio("main", "Main")
    portfolio.add_position(sample_position())
    engine = PortfolioEngine(build_config(tmp_path), registry).initialize()

    status = engine.status()

    assert status.portfolio_count == 1
    assert status.position_count == 1


def test_portfolio_loader_valid_json(tmp_path: Path) -> None:
    json_path = write_portfolio_json(tmp_path)

    portfolio = PortfolioLoader().load(json_path)

    assert portfolio.name == "Loaded Portfolio"
    assert len(portfolio.list_positions()) == 3
    assert portfolio.total_cost() == Decimal("7900")
    assert portfolio.total_market_value() == Decimal("8645")


def test_portfolio_loader_invalid_json(tmp_path: Path) -> None:
    json_path = tmp_path / "portfolio.json"
    json_path.write_text("{invalid", encoding="utf-8")

    try:
        PortfolioLoader().load(json_path)
    except PortfolioLoaderError as exc:
        assert "Invalid portfolio JSON" in str(exc)
    else:
        raise AssertionError("Invalid JSON should be rejected.")


def test_portfolio_loader_missing_fields(tmp_path: Path) -> None:
    payload = portfolio_json_payload()
    del payload["positions"][0]["symbol"]
    json_path = write_portfolio_json(tmp_path, payload)

    try:
        PortfolioLoader().load(json_path)
    except PortfolioLoaderError as exc:
        assert "Missing required field" in str(exc)
        assert "symbol" in str(exc)
    else:
        raise AssertionError("Missing fields should be rejected.")


def test_portfolio_loader_invalid_asset_type(tmp_path: Path) -> None:
    payload = portfolio_json_payload()
    payload["positions"][0]["asset_type"] = "TICKER"
    json_path = write_portfolio_json(tmp_path, payload)

    try:
        PortfolioLoader().load(json_path)
    except PortfolioLoaderError as exc:
        assert "Unsupported asset_type" in str(exc)
    else:
        raise AssertionError("Invalid asset_type should be rejected.")


def test_portfolio_loader_invalid_quantity(tmp_path: Path) -> None:
    payload = portfolio_json_payload()
    payload["positions"][0]["quantity"] = "not-a-number"
    json_path = write_portfolio_json(tmp_path, payload)

    try:
        PortfolioLoader().load(json_path)
    except PortfolioLoaderError as exc:
        assert "Invalid quantity" in str(exc)
    else:
        raise AssertionError("Invalid quantity should be rejected.")


def test_portfolio_loader_totals_unchanged(tmp_path: Path) -> None:
    portfolio = PortfolioLoader().load(write_portfolio_json(tmp_path))

    total_unrealized_pnl = portfolio.total_market_value() - portfolio.total_cost()

    assert portfolio.total_cost() == Decimal("7900")
    assert portfolio.total_market_value() == Decimal("8645")
    assert total_unrealized_pnl == Decimal("745")


def test_cli_portfolio_import_outputs_summary(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))
    json_path = write_portfolio_json(tmp_path)

    assert main(["portfolio", "import", str(json_path)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["portfolio_summary"] == "Portfolio Summary"
    assert payload["portfolio_name"] == "Loaded Portfolio"
    assert payload["total_cost"] == "7900.00"
    assert payload["total_market_value"] == "8645.00"
    assert payload["total_unrealized_pnl"] == "745.00"


def sample_position() -> Position:
    asset = Asset(
        asset_id="asset-1",
        symbol="GENERIC",
        asset_type="OTHER",
        name="Generic Asset",
        currency="USD",
    )
    return Position(
        asset=asset,
        quantity=Decimal("10"),
        average_cost=Decimal("100"),
        current_price=Decimal("150"),
    )


def fail_network(*args: object, **kwargs: object) -> None:
    raise AssertionError("network should not be used")


def portfolio_json_payload() -> dict[str, object]:
    return {
        "portfolio_name": "Loaded Portfolio",
        "positions": [
            {
                "asset_id": "SPY",
                "symbol": "SPY",
                "asset_type": "ETF",
                "name": "SPDR S&P 500 ETF Trust",
                "currency": "USD",
                "quantity": "10",
                "average_cost": "420",
                "current_price": "455",
            },
            {
                "asset_id": "QQQ",
                "symbol": "QQQ",
                "asset_type": "ETF",
                "name": "Invesco QQQ Trust",
                "currency": "USD",
                "quantity": "8",
                "average_cost": "350",
                "current_price": "390",
            },
            {
                "asset_id": "GLD",
                "symbol": "GLD",
                "asset_type": "ETF",
                "name": "SPDR Gold Shares",
                "currency": "USD",
                "quantity": "5",
                "average_cost": "180",
                "current_price": "195",
            },
        ],
    }


def write_portfolio_json(
    tmp_path: Path,
    payload: dict[str, object] | None = None,
) -> Path:
    json_path = tmp_path / "portfolio.json"
    json_path.write_text(
        json.dumps(payload or portfolio_json_payload()),
        encoding="utf-8",
    )
    return json_path
