from datetime import date, timedelta

from onecool_os.market.etf_cta import DailyBar, ETFCTAError, write_history
from scripts import update_etf_cta


def bars(days: int = 400) -> list[DailyBar]:
    start = date(2025, 1, 1)
    return [
        DailyBar(
            trading_date=start + timedelta(days=index),
            open=100 + index,
            high=100 + index,
            low=100 + index,
            close=100 + index,
            volume=100,
            adjusted_close=100 + index,
            source="test",
        )
        for index in range(days)
    ]


def test_equity_daily_prices_do_not_use_alpha_vantage(
    tmp_path, monkeypatch
) -> None:
    yahoo_calls = []

    monkeypatch.setattr(
        update_etf_cta,
        "fetch_yahoo_daily",
        lambda symbol, **_: yahoo_calls.append(symbol) or bars(),
    )
    monkeypatch.setattr(
        update_etf_cta.AlphaVantageClient,
        "fetch_daily",
        lambda *_: (_ for _ in ()).throw(
            AssertionError("Alpha Vantage daily endpoint must not be called")
        ),
    )
    monkeypatch.setattr(
        update_etf_cta.AlphaVantageClient,
        "fetch_wti_daily",
        lambda *_: bars(),
    )

    payload = update_etf_cta.update(tmp_path, "key", allow_bootstrap=True)

    assert set(yahoo_calls) == set(update_etf_cta.EQUITY_MARKET_SYMBOLS)
    price_statuses = [
        item
        for item in payload["data_status"]
        if item["dataset"] == "daily_price" and item["symbol"] != "WTI"
    ]
    assert all(item["status"] == "CURRENT" for item in price_statuses)
    assert all(item["source"] == "yahoo" for item in price_statuses)


def test_rate_limit_keeps_existing_wti_and_marks_stale(
    tmp_path, monkeypatch
) -> None:
    existing = bars()
    history_dir = tmp_path / "history"
    write_history(history_dir / "WTI.csv", existing)

    monkeypatch.setattr(
        update_etf_cta, "fetch_yahoo_daily", lambda _symbol, **_: bars()
    )
    monkeypatch.setattr(
        update_etf_cta.AlphaVantageClient,
        "fetch_wti_daily",
        lambda *_: (_ for _ in ()).throw(
            ETFCTAError("standard API rate limit is 25 requests per day")
        ),
    )

    payload = update_etf_cta.update(tmp_path, "key", allow_bootstrap=True)

    wti_status = next(
        item
        for item in payload["data_status"]
        if item["symbol"] == "WTI" and item["dataset"] == "daily_price"
    )
    assert wti_status["status"] == "STALE"
    assert wti_status["reason"] == "alpha_vantage_daily_quota"


def test_rate_limit_keeps_existing_actions_and_marks_stale(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        update_etf_cta, "fetch_yahoo_daily", lambda _symbol, **_: bars()
    )
    monkeypatch.setattr(
        update_etf_cta.AlphaVantageClient,
        "fetch_actions",
        lambda *_: (_ for _ in ()).throw(
            ETFCTAError("standard API rate limit is 25 requests per day")
        ),
    )
    monkeypatch.setattr(
        update_etf_cta.AlphaVantageClient,
        "fetch_wti_daily",
        lambda *_: bars(),
    )

    payload = update_etf_cta.update(
        tmp_path,
        "key",
        allow_bootstrap=True,
        refresh_action_symbols={"AIQ"},
    )

    assert {
        "symbol": "AIQ",
        "dataset": "corporate_actions",
        "status": "STALE",
        "reason": "alpha_vantage_daily_quota",
    } in payload["data_status"]
