from datetime import date, timedelta
from pathlib import Path

import pytest

from onecool_os.market.etf_cta import DailyBar, merge_and_adjust
from scripts import update_market_dashboard


class FakeClient:
    calls: list[tuple[str, str]] = []

    def __init__(self, api_key: str) -> None:
        assert api_key == "secret"

    def fetch_daily(self, symbol: str, *, outputsize: str = "compact"):
        self.calls.append((f"daily:{outputsize}", symbol))
        start = date(2020, 1, 1)
        return [
            DailyBar(
                trading_date=start + timedelta(days=index),
                open=float(index + 1),
                high=float(index + 1),
                low=float(index + 1),
                close=float(index + 1),
                volume=100,
            )
            for index in range(500)
        ]

    def fetch_actions(self, symbol: str):
        self.calls.extend((("dividends", symbol), ("splits", symbol)))
        return {}


class FakeBootstrapper:
    calls: list[str] = []
    adjusted_calls: list[str] = []

    def fetch_daily(self, symbol: str):
        self.calls.append(symbol)
        start = date(2020, 1, 1)
        return [
            DailyBar(
                trading_date=start + timedelta(days=index),
                open=float(index + 1),
                high=float(index + 1),
                low=float(index + 1),
                close=float(index + 1),
                volume=100,
                source="yahoo_finance_bootstrap",
            )
            for index in range(500)
        ]

    def fetch_adjusted_daily(self, symbol: str):
        self.adjusted_calls.append(symbol)
        return self.fetch_daily(symbol)


def test_update_uses_av_for_us_and_yahoo_fallback_for_taiwan(
    tmp_path: Path, monkeypatch
) -> None:
    FakeClient.calls = []
    FakeBootstrapper.calls = []
    FakeBootstrapper.adjusted_calls = []
    monkeypatch.setattr(update_market_dashboard, "AlphaVantageClient", FakeClient)

    payload = update_market_dashboard.update(
        tmp_path, "secret", bootstrapper=FakeBootstrapper()
    )

    assert len(FakeClient.calls) == 15
    assert len(FakeBootstrapper.calls) == 11
    assert FakeBootstrapper.adjusted_calls == [
        "^RUT", "0050.TW", "2330.TW", "^VIX", "DX-Y.NYB", "^TYX"
    ]
    assert all(call[0] != "daily:full" for call in FakeClient.calls)
    assert len(payload["results"]) == 11
    assert payload["provider_by_symbol"]["SPY"] == "alpha_vantage"
    assert payload["provider_by_symbol"]["VIX"] == "yahoo_finance"
    assert payload["cta_engine"] == "onecool_os.market.etf_cta.calculate_cta"
    latest = tmp_path / "data" / "market" / "dashboard" / "dashboard_latest.json"
    assert latest.exists()
    assert len(list((latest.parent / "history").glob("*.csv"))) == 11
    assert len(list((latest.parent / "snapshots").glob("*.json"))) == 1


def test_missing_api_key_uses_yahoo_for_all_symbols(
    tmp_path: Path, monkeypatch
) -> None:
    class ClientMustNotBeCreated:
        def __init__(self, api_key: str) -> None:
            raise AssertionError("Alpha Vantage must not be created without a key")

    monkeypatch.setattr(
        update_market_dashboard, "AlphaVantageClient", ClientMustNotBeCreated
    )
    bootstrapper = FakeBootstrapper()
    FakeBootstrapper.calls = []
    FakeBootstrapper.adjusted_calls = []

    payload = update_market_dashboard.update(
        tmp_path, "", bootstrapper=bootstrapper
    )

    assert len(payload["results"]) == 11
    assert FakeBootstrapper.adjusted_calls == [
        config.provider_symbol for config in update_market_dashboard.MARKET_SYMBOLS
    ]
    assert set(payload["provider_by_symbol"].values()) == {
        "yahoo_finance",
        "yahoo_finance_fallback",
    }


def test_both_providers_failing_keeps_last_successful_cache(
    tmp_path: Path, monkeypatch
) -> None:
    dashboard = tmp_path / "data" / "market" / "dashboard"
    dashboard.mkdir(parents=True)
    latest = dashboard / "dashboard_latest.json"
    latest.write_text('{"status":"last-success"}\n', encoding="utf-8")

    class FailingClient(FakeClient):
        def fetch_actions(self, symbol: str):
            raise RuntimeError(f"provider failed for {symbol}")

    class FailingBootstrapper(FakeBootstrapper):
        def fetch_adjusted_daily(self, symbol: str):
            raise RuntimeError(f"backup failed for {symbol}")

    monkeypatch.setattr(
        update_market_dashboard, "AlphaVantageClient", FailingClient
    )

    with pytest.raises(RuntimeError, match="backup failed"):
        update_market_dashboard.update(
            tmp_path, "secret", bootstrapper=FailingBootstrapper()
        )

    assert latest.read_text(encoding="utf-8") == '{"status":"last-success"}\n'
    assert not (dashboard / "history").exists()


def test_existing_histories_skip_yahoo_bootstrap(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(update_market_dashboard, "AlphaVantageClient", FakeClient)
    bootstrapper = FakeBootstrapper()
    history_dir = tmp_path / "data" / "market" / "dashboard" / "history"
    history_dir.mkdir(parents=True)
    for config in update_market_dashboard.MARKET_SYMBOLS:
        update_market_dashboard.write_history(
            history_dir / f"{config.symbol}.csv",
            merge_and_adjust(
                [],
                bootstrapper.fetch_daily(config.provider_symbol),
            ),
        )
    FakeBootstrapper.calls = []
    FakeBootstrapper.adjusted_calls = []
    FakeClient.calls = []

    update_market_dashboard.update(
        tmp_path, "secret", bootstrapper=bootstrapper
    )

    assert FakeBootstrapper.calls == [
        "^RUT", "0050.TW", "2330.TW", "^VIX", "DX-Y.NYB", "^TYX"
    ]
    assert FakeBootstrapper.adjusted_calls == [
        "^RUT", "0050.TW", "2330.TW", "^VIX", "DX-Y.NYB", "^TYX"
    ]
    assert len(FakeClient.calls) == 15
