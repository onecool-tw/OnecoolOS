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
from onecool_os.portfolio.models import Asset, Portfolio, Position
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


def sample_position() -> Position:
    asset = Asset(
        asset_id="asset-1",
        asset_type="generic",
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
