from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

from onecool_os.market.etf_cta import DailyBar
from scripts.update_market_dashboard import (
    _completed_symbol_bars, _repair_btc_week_close,
)


BTC = SimpleNamespace(symbol="BTC", provider_symbol="BTC-USD", market="CONTEXT")
NOW = datetime(2026, 10, 12, 4, 0, tzinfo=UTC)


def bar(day):
    return DailyBar(trading_date=day, open=100, high=100, low=100,
                    close=100, volume=1, source="yahoo_finance_raw")


def test_crypto_filters_today_and_future_bars_but_keeps_completed_sunday():
    rows = [bar(date(2026, 10, d)) for d in (10, 11, 12, 13)]
    assert [b.trading_date for b in _completed_symbol_bars(BTC, rows, NOW)] == [
        date(2026, 10, 10), date(2026, 10, 11),
    ]


def test_missing_sunday_backfills_from_wider_window_without_today():
    class Provider:
        def fetch_raw_daily(self, symbol, *, period):
            assert (symbol, period) == ("BTC-USD", "1mo")
            return [bar(date(2026, 10, 11)), bar(date(2026, 10, 12))]

    rows = [bar(date(2026, 10, 4)), bar(date(2026, 10, 10))]
    result = _repair_btc_week_close(BTC, rows, Provider(), NOW)
    assert [b.trading_date for b in result] == [
        date(2026, 10, 4), date(2026, 10, 10), date(2026, 10, 11),
    ]


def test_failed_backfill_retains_verified_history_without_fabrication():
    class Provider:
        def fetch_raw_daily(self, *args, **kwargs):
            raise RuntimeError("rate limited")

    rows = [bar(date(2026, 10, 4)), bar(date(2026, 10, 10))]
    assert _repair_btc_week_close(BTC, rows, Provider(), NOW) == rows


def test_sunday_not_complete_until_monday_utc():
    rows = [bar(date(2026, 10, 11))]
    sunday = datetime(2026, 10, 11, 23, 59, tzinfo=UTC)
    assert _completed_symbol_bars(BTC, rows, sunday) == []


def test_present_sunday_does_not_hide_missing_latest_completed_day():
    calls = []

    class Provider:
        def fetch_raw_daily(self, symbol, *, period):
            return [bar(date(2026, 10, 11)), bar(date(2026, 10, 12))]

        def fetch_btc_completed_day(self, day):
            calls.append(day)
            return [bar(day)]

    rows = [bar(date(2026, 10, d)) for d in (11, 12)]
    now = datetime(2026, 10, 14, 3, 0, tzinfo=UTC)
    result = _repair_btc_week_close(BTC, rows, Provider(), now)
    assert calls == [date(2026, 10, 13)]
    assert result[-1].trading_date == date(2026, 10, 13)


def test_current_btc_history_needs_no_repair_request():
    class Provider:
        def fetch_raw_daily(self, *args, **kwargs):
            raise AssertionError("Unnecessary provider request")

    rows = [bar(date(2026, 10, d)) for d in (11, 12, 13)]
    assert _repair_btc_week_close(
        BTC, rows, Provider(), datetime(2026, 10, 14, tzinfo=UTC)
    ) == rows


def test_exact_latest_day_repair_rejects_wrong_date_and_keeps_cache_on_failure():
    class Provider:
        def fetch_raw_daily(self, *args, **kwargs):
            raise RuntimeError("Unavailable")

        def fetch_btc_completed_day(self, day):
            return [bar(date(2026, 10, 14))]

    rows = [bar(date(2026, 10, d)) for d in (11, 12)]
    assert _repair_btc_week_close(
        BTC, rows, Provider(), datetime(2026, 10, 14, tzinfo=UTC)
    ) == rows
