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


def test_transient_exact_day_failure_retries_without_imputation(monkeypatch):
    monkeypatch.setattr("scripts.update_market_dashboard.sleep", lambda _: None)
    class Provider:
        calls = 0
        def fetch_raw_daily(self, *args, **kwargs):
            return []
        def fetch_btc_completed_day(self, day):
            self.calls += 1
            if self.calls < 3:
                raise RuntimeError("Temporary provider failure")
            return [bar(day)]
    provider = Provider()
    result = _repair_btc_week_close(BTC, [bar(date(2026, 10, 11))], provider,
                                    datetime(2026, 10, 14, 3, tzinfo=UTC))
    assert provider.calls == 3
    assert result[-1].trading_date == date(2026, 10, 13)


def test_exhausted_retry_preserves_cache_and_stale_heartbeat_fails(monkeypatch):
    import pytest
    from scripts.verify_btc_freshness import verify
    monkeypatch.setattr("scripts.update_market_dashboard.sleep", lambda _: None)
    class Provider:
        calls = 0
        def fetch_raw_daily(self, *args, **kwargs):
            return []
        def fetch_btc_completed_day(self, day):
            self.calls += 1
            return []
    provider = Provider()
    rows = [bar(date(2026, 10, 11))]
    now = datetime(2026, 10, 14, 3, tzinfo=UTC)
    assert _repair_btc_week_close(BTC, rows, provider, now) == rows
    assert provider.calls == 3
    with pytest.raises(RuntimeError, match="actual 2026-10-11"):
        verify({"results": [{"symbol": "BTC", "as_of": "2026-10-11", "cta": "SELL"}]}, now)


def test_btc_heartbeat_rejects_future_duplicate_unknown_and_allows_grace():
    import pytest
    from scripts.verify_btc_freshness import verify
    now = datetime(2026, 10, 16, 3, tzinfo=UTC)
    row = {"symbol": "BTC", "as_of": "2026-10-15", "cta": "SELL"}
    assert verify({"results": [row]}, now) == "2026-10-15"
    for rows in ([], [row, row], [dict(row, as_of="2026-10-16")], [dict(row, cta="UNKNOWN")]):
        with pytest.raises(RuntimeError):
            verify({"results": rows}, now)
    lag = dict(row, as_of="2026-10-14")
    assert verify({"results": [lag]}, now.replace(hour=0, minute=29)) == "2026-10-14"
    with pytest.raises(RuntimeError):
        verify({"results": [lag]}, now.replace(hour=0, minute=30))
