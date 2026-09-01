import json
from dataclasses import replace
from datetime import date, timedelta
from math import nan
from pathlib import Path

import pytest

from onecool_os.market.etf_cta import DailyBar, merge_and_adjust
from onecool_os.market.us_breakout_scan import FundamentalMetrics
from scripts import update_market_dashboard


class FakeClient:
    calls: list[tuple[str, str]] = []

    def __init__(self, api_key: str) -> None:
        assert api_key == "secret"

    def fetch_daily(self, symbol: str, *, outputsize: str = "compact"):
        self.calls.append((f"daily:{outputsize}", symbol))
        start = date(2025, 10, 1)
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
        start = date(2025, 10, 1)
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

    def fetch_raw_daily(self, symbol: str, *, period: str = "10d"):
        return self.fetch_daily(symbol)

    def fetch_adjusted_daily(self, symbol: str):
        self.adjusted_calls.append(symbol)
        return self.fetch_daily(symbol)


class LiquidFakeBootstrapper(FakeBootstrapper):
    def fetch_daily(self, symbol: str):
        return [
            replace(bar, volume=1_000_000)
            for bar in super().fetch_daily(symbol)
        ]


def test_update_uses_raw_yahoo_primary_for_all_dashboard_symbols(
    tmp_path: Path, monkeypatch
) -> None:
    FakeClient.calls = []
    FakeBootstrapper.calls = []
    FakeBootstrapper.adjusted_calls = []
    monkeypatch.setattr(update_market_dashboard, "AlphaVantageClient", FakeClient)

    payload = update_market_dashboard.update(
        tmp_path, "secret", bootstrapper=FakeBootstrapper()
    )

    assert FakeClient.calls == []
    assert FakeBootstrapper.calls == [
        config.provider_symbol for config in update_market_dashboard.MARKET_SYMBOLS
    ] + ["SPCX"]
    assert FakeBootstrapper.adjusted_calls == []
    assert len(payload["results"]) == len(update_market_dashboard.MARKET_SYMBOLS)
    assert payload["provider_by_symbol"]["SPY"] == "yahoo_finance_raw"
    assert payload["provider_by_symbol"]["VIX"] == "yahoo_finance_raw"
    assert payload["cta_engine"] == "onecool_os.market.etf_cta.calculate_cta"
    latest = tmp_path / "data" / "market" / "dashboard" / "dashboard_latest.json"
    assert latest.exists()
    assert len(list((latest.parent / "history").glob("*.csv"))) == len(
        update_market_dashboard.MARKET_SYMBOLS
    ) + 1
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

    assert len(payload["results"]) == len(update_market_dashboard.MARKET_SYMBOLS)
    assert FakeBootstrapper.calls == [
        config.provider_symbol for config in update_market_dashboard.MARKET_SYMBOLS
    ] + ["SPCX"]
    assert FakeBootstrapper.adjusted_calls == []
    assert set(payload["provider_by_symbol"].values()) == {"yahoo_finance_raw"}


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
        def fetch_raw_daily(self, symbol: str, *, period: str = "10d"):
            raise RuntimeError(f"backup failed for {symbol}")

    monkeypatch.setattr(
        update_market_dashboard, "AlphaVantageClient", FailingClient
    )

    with pytest.raises(RuntimeError, match="raw-history rebuild"):
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
        config.provider_symbol for config in update_market_dashboard.MARKET_SYMBOLS
    ] + ["SPCX"]
    assert FakeBootstrapper.adjusted_calls == []
    assert FakeClient.calls == []


def test_immature_innovation_option_is_displayed_without_fake_cta() -> None:
    start = date(2026, 6, 12)
    history = merge_and_adjust(
        [],
        [
            DailyBar(
                trading_date=start + timedelta(days=index),
                open=100.0 + index,
                high=101.0 + index,
                low=99.0 + index,
                close=100.0 + index,
                volume=100,
            )
            for index in range(60)
        ],
    )

    state = update_market_dashboard._innovation_option_state(
        update_market_dashboard.INNOVATION_OPTION_CONFIGS["SPCX"], history
    )

    assert state["symbol"] == "SPCX"
    assert state["data_status"] == "ACCUMULATING"
    assert state["weekly_entry_status"] == "UNKNOWN"
    assert state["daily_risk_status"] == "UNKNOWN"
    assert state["display_action"] == "資料累積中；不得建立CTA訊號"
    assert "weekly_ma30" not in state


def test_non_finite_yahoo_row_is_dropped_without_aborting_dashboard(
    tmp_path: Path, monkeypatch
) -> None:
    class BootstrapperWithOneBadRow(FakeBootstrapper):
        def fetch_raw_daily(self, symbol: str, *, period: str = "10d"):
            bars = super().fetch_raw_daily(symbol, period=period)
            if symbol == "0050.TW":
                bars[-5] = replace(
                    bars[-5],
                    open=nan,
                    high=nan,
                    low=nan,
                    close=nan,
                )
            return bars

    monkeypatch.setattr(update_market_dashboard, "AlphaVantageClient", FakeClient)
    payload = update_market_dashboard.update(
        tmp_path, "secret", bootstrapper=BootstrapperWithOneBadRow()
    )

    record = next(item for item in payload["results"] if item["symbol"] == "0050")
    assert record["current_price"] == 500.0
    assert record["sma50"] == record["sma50"]
    latest = tmp_path / "data" / "market" / "dashboard" / "dashboard_latest.json"
    parsed = json.loads(latest.read_text(encoding="utf-8"))
    assert parsed["data_status"] == "READY"


@pytest.mark.parametrize(
    ("yahoo_dividend", "alpha_dividend"),
    [
        (1.428, 1.428117),
        (1.966, 1.965548),
    ],
)
def test_corporate_action_validation_accepts_provider_rounding(
    yahoo_dividend: float, alpha_dividend: float
) -> None:
    trading_date = date(2024, 12, 20)
    bars = [
        DailyBar(
            trading_date=trading_date,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=100,
            dividend=yahoo_dividend,
        )
    ]

    assert update_market_dashboard._corporate_action_mismatches(
        bars, {trading_date: (alpha_dividend, 1.0)}
    ) == []


def test_corporate_action_validation_tracks_qqq_minor_provider_difference() -> None:
    trading_date = date(2023, 9, 18)
    bars = [
        DailyBar(
            trading_date=trading_date,
            open=370.0,
            high=371.0,
            low=369.0,
            close=370.0,
            volume=100,
            dividend=0.536,
        )
    ]

    mismatches, minor_differences = (
        update_market_dashboard._corporate_action_discrepancies(
            bars, {trading_date: (0.53885, 1.0)}
        )
    )

    assert mismatches == []
    assert minor_differences == [
        "2023-09-18: dividend yahoo=0.536 alpha=0.53885 "
        "difference=0.002850"
    ]


def test_dashboard_publishes_minor_provider_difference_as_non_blocking(
    tmp_path: Path, monkeypatch
) -> None:
    action_date = date(2025, 10, 11)

    class MinorDifferenceClient(FakeClient):
        def fetch_actions(self, symbol: str):
            if symbol == "QQQ":
                return {action_date: (0.53885, 1.0)}
            return {}

    class QqqDividendBootstrapper(FakeBootstrapper):
        def fetch_raw_daily(self, symbol: str, *, period: str = "10d"):
            bars = super().fetch_raw_daily(symbol, period=period)
            if symbol == "QQQ":
                bars[10] = replace(bars[10], dividend=0.536)
            return bars

    monkeypatch.setattr(
        update_market_dashboard, "AlphaVantageClient", MinorDifferenceClient
    )

    payload = update_market_dashboard.update(
        tmp_path,
        "secret",
        bootstrapper=QqqDividendBootstrapper(),
        refresh_action_symbols={"QQQ"},
    )

    assert payload["data_status"] == "READY"
    assert payload["corporate_action_validation"] == [
        {
            "symbol": "QQQ",
            "status": "MATCHED_WITH_MINOR_PROVIDER_DIFFERENCE",
            "source_a": "yahoo_finance_raw",
            "source_b": "alpha_vantage",
            "as_of": "2027-02-12",
            "minor_differences": [
                "2025-10-11: dividend yahoo=0.536 alpha=0.53885 "
                "difference=0.002850"
            ],
            "minor_difference_policy": (
                "non_blocking_only_when_absolute_difference_lte_0.005_"
                "and_relative_difference_lte_1pct"
            ),
        }
    ]


def test_corporate_action_validation_rejects_small_absolute_large_relative_gap(
) -> None:
    trading_date = date(2024, 12, 20)
    bars = [
        DailyBar(
            trading_date=trading_date,
            open=10.0,
            high=10.1,
            low=9.9,
            close=10.0,
            volume=100,
            dividend=0.01,
        )
    ]

    mismatches, minor_differences = (
        update_market_dashboard._corporate_action_discrepancies(
            bars, {trading_date: (0.014, 1.0)}
        )
    )

    assert mismatches == [
        "2024-12-20: dividend yahoo=0.01 alpha=0.014 "
        "difference=0.004000"
    ]
    assert minor_differences == []


def test_corporate_action_validation_rejects_material_dividend_difference() -> None:
    trading_date = date(2024, 12, 20)
    bars = [
        DailyBar(
            trading_date=trading_date,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=100,
            dividend=1.428,
        )
    ]

    mismatches = update_market_dashboard._corporate_action_mismatches(
        bars, {trading_date: (1.438, 1.0)}
    )

    assert mismatches == [
        "2024-12-20: dividend yahoo=1.428 alpha=1.438 difference=0.010000"
    ]


def test_us_scan_is_published_with_same_dashboard_cutoff(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(update_market_dashboard, "AlphaVantageClient", FakeClient)
    bootstrapper = LiquidFakeBootstrapper()

    def loader(expected_as_of: str):
        history = merge_and_adjust([], bootstrapper.fetch_daily("RTX"))
        return {"RTX": history}, {
            "RTX": FundamentalMetrics(
                as_of=expected_as_of,
                quarterly_eps_growth=0.5,
                quarterly_revenue_growth=0.3,
                annual_eps_growth=0.4,
                institutional_holders_available=True,
            )
        }

    payload = update_market_dashboard.update(
        tmp_path,
        "secret",
        bootstrapper=bootstrapper,
        refresh_us_scan=True,
        breakout_input_loader=loader,
    )

    scan = payload["daily_top5_scan"]
    assert scan["publication_status"] == "CURRENT"
    assert scan["expected_as_of"] == payload["expected_as_of"]
    assert scan["top5"][0]["symbol"] == "RTX"
    latest = (
        tmp_path / "data" / "market" / "us_stock_intelligence"
        / "breakout_scan_latest.json"
    )
    assert json.loads(latest.read_text(encoding="utf-8"))["expected_as_of"] == (
        payload["expected_as_of"]
    )


def test_failed_us_scan_keeps_and_labels_last_valid_artifact(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(update_market_dashboard, "AlphaVantageClient", FakeClient)
    scan_dir = tmp_path / "data" / "market" / "us_stock_intelligence"
    scan_dir.mkdir(parents=True)
    scan_path = scan_dir / "breakout_scan_latest.json"
    previous = {
        "data_status": "READY",
        "publication_status": "CURRENT",
        "expected_as_of": "2026-08-07",
        "top5": [],
    }
    scan_path.write_text(json.dumps(previous), encoding="utf-8")

    def failing_loader(expected_as_of: str):
        raise RuntimeError(f"provider unavailable for {expected_as_of}")

    payload = update_market_dashboard.update(
        tmp_path,
        "secret",
        bootstrapper=LiquidFakeBootstrapper(),
        refresh_us_scan=True,
        breakout_input_loader=failing_loader,
    )

    scan = payload["daily_top5_scan"]
    assert scan["publication_status"] == "LAST_VALID"
    assert scan["expected_as_of"] == "2026-08-07"
    assert scan["attempted_as_of"] == payload["expected_as_of"]
    assert json.loads(scan_path.read_text(encoding="utf-8")) == previous
