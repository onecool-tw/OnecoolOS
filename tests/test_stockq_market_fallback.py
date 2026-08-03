from datetime import date, timedelta

from onecool_os.market.etf_cta import DailyBar
from scripts import update_stockq_rotation


def _bars() -> list[DailyBar]:
    return [
        DailyBar(
            trading_date=date(2025, 1, 1) + timedelta(days=index),
            open=100,
            high=100,
            low=100,
            close=100,
            volume=0,
            adjusted_close=100,
        )
        for index in range(300)
    ]


def test_wig_uses_stooq_when_yahoo_market_series_fails(monkeypatch) -> None:
    class Bootstrapper:
        def fetch_adjusted_daily(self, _symbol):
            raise RuntimeError("Yahoo unavailable")

    monkeypatch.setattr(update_stockq_rotation, "_fetch_stooq_daily", lambda _: _bars())

    bars, method = update_stockq_rotation._fetch_local_market(
        "^WIG", Bootstrapper()
    )

    assert method == "STOOQ_FALLBACK"
    assert len(bars) == 300


def test_unmapped_market_does_not_silently_change_benchmark() -> None:
    class Bootstrapper:
        def fetch_adjusted_daily(self, _symbol):
            raise RuntimeError("Yahoo unavailable")

    try:
        update_stockq_rotation._fetch_local_market("^GSPC", Bootstrapper())
    except RuntimeError as exc:
        assert str(exc) == "Yahoo unavailable"
    else:
        raise AssertionError("Unmapped market must remain a provider failure")
