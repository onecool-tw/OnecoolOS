import json
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

from onecool_os.__main__ import main
from onecool_os.core.config import (
    ApplicationSettings,
    DatabaseSettings,
    LoggingSettings,
    PathSettings,
    RuntimeSettings,
    SystemConfig,
)
from onecool_os.market.engine import MarketEngine
from onecool_os.market.providers import (
    MarketProvider,
    MarketProviderError,
    MockProvider,
    YahooFinanceProvider,
)
from onecool_os.market.registry import ProviderRegistry, ProviderRegistryError


def build_config(tmp_path: Path) -> SystemConfig:
    return SystemConfig(
        app=ApplicationSettings(
            name="Onecool OS",
            version="0.3.0",
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
  version: 0.3.0
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
market:
  default_provider: yahoo
  providers:
    yahoo:
      enabled: true
    mock:
      enabled: true
""".strip(),
        encoding="utf-8",
    )


def test_market_engine_initializes(tmp_path: Path) -> None:
    engine = MarketEngine(build_config(tmp_path)).initialize()

    status = engine.status()

    assert engine.started is True
    assert status.engine_status == "ready"
    assert status.registered_providers == ("mock",)


def test_provider_registration(tmp_path: Path) -> None:
    registry = ProviderRegistry()
    provider = MockProvider()

    registry.register_provider(provider)

    assert registry.get_provider("mock") is provider
    assert registry.list_providers() == (provider,)


def test_duplicate_provider_rejection() -> None:
    registry = ProviderRegistry()
    registry.register_provider(MockProvider())

    with pytest.raises(ProviderRegistryError):
        registry.register_provider(MockProvider())


def test_mock_provider_fetch() -> None:
    provider = MockProvider()
    provider.connect()

    data = provider.fetch("aapl")

    assert data["provider_id"] == "mock"
    assert data["symbol"] == "AAPL"
    assert data["price"] == 100.0
    assert data["source"] == "mock"


def test_provider_health_check() -> None:
    provider = MockProvider()
    provider.connect()

    health = provider.health_check()

    assert health["provider_id"] == "mock"
    assert health["status"] == "ok"


def test_cli_market_status(tmp_path: Path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))

    assert main(["market", "status"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["engine_status"] == "ready"
    assert payload["registered_providers"] == ["mock", "yahoo"]
    assert payload["provider_health"]["mock"]["status"] == "ok"


def test_yahoo_finance_provider_implements_market_provider() -> None:
    provider = YahooFinanceProvider()

    assert isinstance(provider, MarketProvider)
    assert provider.provider_id == "yahoo"


def test_yahoo_provider_can_be_registered() -> None:
    registry = ProviderRegistry()
    provider = YahooFinanceProvider()

    registry.register_provider(provider)

    assert registry.get_provider("yahoo") is provider


def test_yahoo_fetch_returns_normalized_schema(monkeypatch) -> None:
    monkeypatch.setitem(
        sys.modules,
        "yfinance",
        SimpleNamespace(Ticker=FakeTicker),
    )
    provider = YahooFinanceProvider()

    data = provider.fetch("SPY")

    assert data["symbol"] == "SPY"
    assert data["provider"] == "yahoo"
    assert data["last_price"] == 456.78
    assert data["currency"] == "USD"
    assert data["timestamp"]
    assert data["raw"]["last_price"] == 456.78


def test_cli_market_fetch_works(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setitem(
        sys.modules,
        "yfinance",
        SimpleNamespace(Ticker=FakeTicker),
    )
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))

    assert main(["market", "fetch", "SPY", "--provider", "yahoo"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["symbol"] == "SPY"
    assert payload["provider"] == "yahoo"
    assert payload["last_price"] == 456.78


def test_yahoo_provider_failure_is_handled_safely(monkeypatch) -> None:
    monkeypatch.setitem(
        sys.modules,
        "yfinance",
        SimpleNamespace(Ticker=FailingTicker),
    )
    provider = YahooFinanceProvider()

    with pytest.raises(MarketProviderError):
        provider.fetch("SPY")


class FakeTicker:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.fast_info = {
            "last_price": 456.78,
            "currency": "USD",
        }


class FailingTicker:
    def __init__(self, symbol: str) -> None:
        raise RuntimeError(f"fetch failed for {symbol}")
