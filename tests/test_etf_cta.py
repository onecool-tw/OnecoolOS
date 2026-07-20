from datetime import date, timedelta

import pytest

from onecool_os.market.etf_cta import (
    ACTION_REFRESH_GROUPS,
    CONFIRMATION_SYMBOLS,
    MARKET_SYMBOLS,
    WATCHLIST_SYMBOLS,
    AlphaVantageClient,
    DailyBar,
    ETFCTAError,
    calculate_cta,
    apply_corporate_actions,
    has_new_price_anomaly,
    merge_and_adjust,
    parse_alpha_vantage,
)


def test_market_symbols_separate_proxies_from_confirmations() -> None:
    assert WATCHLIST_SYMBOLS == (
        "AIQ", "SMIN", "RING", "IBB", "PICK", "RXI", "IXC"
    )
    assert CONFIRMATION_SYMBOLS == ("SMH", "GLD")
    assert MARKET_SYMBOLS == WATCHLIST_SYMBOLS + CONFIRMATION_SYMBOLS
    assert set(ACTION_REFRESH_GROUPS["group_a"]) | set(
        ACTION_REFRESH_GROUPS["group_b"]
    ) == set(MARKET_SYMBOLS)
    assert not set(ACTION_REFRESH_GROUPS["group_a"]) & set(
        ACTION_REFRESH_GROUPS["group_b"]
    )


def bar(day: date, close: float, **changes) -> DailyBar:
    values = {
        "trading_date": day,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": 100,
    }
    values.update(changes)
    return DailyBar(**values)


def test_parse_alpha_vantage_joins_actions() -> None:
    daily = {
        "Time Series (Daily)": {
            "2026-07-15": {
                "1. open": "99",
                "2. high": "101",
                "3. low": "98",
                "4. close": "100",
                "5. volume": "123",
            }
        }
    }
    dividends = {"data": [{"ex_dividend_date": "2026-07-15", "amount": "1"}]}
    splits = {"data": [{"effective_date": "2026-07-15", "split_factor": "2"}]}

    parsed = parse_alpha_vantage(daily, dividends, splits)

    assert parsed[0].dividend == 1.0
    assert parsed[0].split_factor == 2.0


def test_alpha_vantage_retries_rate_note() -> None:
    responses = iter(
        [
            b'{"Note":"slow down"}',
            b'{"Time Series (Daily)":{"2026-07-15":{"1. open":"1","2. high":"1","3. low":"1","4. close":"1","5. volume":"1"}}}',
        ]
    )
    sleeps = []
    client = AlphaVantageClient(
        "secret",
        request=lambda _: next(responses),
        sleeper=sleeps.append,
        request_spacing_seconds=0,
    )

    payload = client._query("TIME_SERIES_DAILY", "QQQ")

    assert "Time Series (Daily)" in payload
    assert sleeps == [60.0]


def test_daily_fetch_uses_one_request() -> None:
    urls = []
    response = b'{"Time Series (Daily)":{"2026-07-15":{"1. open":"1","2. high":"1","3. low":"1","4. close":"1","5. volume":"1"}}}'
    client = AlphaVantageClient(
        "secret",
        request=lambda url: urls.append(url) or response,
        sleeper=lambda _: None,
        request_spacing_seconds=0,
    )

    assert len(client.fetch_daily("QQQ")) == 1
    assert len(urls) == 1
    assert "function=TIME_SERIES_DAILY" in urls[0]


def test_daily_fetch_can_request_full_history_with_one_request() -> None:
    urls = []
    response = b'{"Time Series (Daily)":{"2026-07-15":{"1. open":"1","2. high":"1","3. low":"1","4. close":"1","5. volume":"1"}}}'
    client = AlphaVantageClient(
        "secret",
        request=lambda url: urls.append(url) or response,
        sleeper=lambda _: None,
        request_spacing_seconds=0,
    )

    client.fetch_daily("SPY", outputsize="full")

    assert len(urls) == 1
    assert "outputsize=full" in urls[0]


def test_action_refresh_backfills_existing_history() -> None:
    start = date(2026, 1, 1)
    existing = [bar(start, 100), bar(start + timedelta(days=1), 50)]
    refreshed = apply_corporate_actions(
        existing, {start + timedelta(days=1): (0.0, 2.0)}
    )
    history = merge_and_adjust([], refreshed)

    assert history[0].adjusted_close == pytest.approx(50)
    assert history[1].split_factor == 2.0


def test_authoritative_action_refresh_clears_stale_action() -> None:
    stale = [bar(date(2026, 1, 1), 100, dividend=1.0)]

    refreshed = apply_corporate_actions(stale, {}, authoritative=True)

    assert refreshed[0].dividend == 0.0
    assert refreshed[0].split_factor == 1.0


def test_large_new_close_move_triggers_anomaly() -> None:
    start = date(2026, 1, 1)
    existing = [bar(start, 100)]

    assert has_new_price_anomaly(
        existing, [bar(start + timedelta(days=1), 50)]
    )
    assert not has_new_price_anomaly(
        existing, [bar(start + timedelta(days=1), 90)]
    )


def test_merge_recalculates_split_and_dividend_adjustments() -> None:
    start = date(2026, 1, 1)
    history = merge_and_adjust(
        [],
        [
            bar(start, 100),
            bar(start + timedelta(days=1), 50, split_factor=2),
            bar(start + timedelta(days=2), 49, dividend=1),
        ],
    )

    assert history[-1].adjusted_close == pytest.approx(49)
    assert history[1].adjusted_close == pytest.approx(49)
    assert history[0].adjusted_close == pytest.approx(49)


def test_merge_does_not_double_adjust_provider_adjusted_split() -> None:
    start = date(2026, 1, 1)
    history = merge_and_adjust(
        [],
        [
            bar(start, 50),
            bar(start + timedelta(days=1), 51, split_factor=2),
            bar(start + timedelta(days=2), 52),
        ],
    )

    assert history[0].adjusted_close == pytest.approx(50)
    assert history[1].adjusted_close == pytest.approx(51)
    assert history[2].adjusted_close == pytest.approx(52)


def test_calculate_cta_buy() -> None:
    start = date(2020, 1, 1)
    history = [
        bar(
            start + timedelta(days=index),
            float(index + 1),
            adjusted_close=float(index + 1),
        )
        for index in range(400)
    ]

    result = calculate_cta("QQQ", history)

    assert result.cta == "BUY"
    assert result.daily_50ma > result.daily_200ma
    assert result.weekly_30ma > result.weekly_50ma


def test_calculate_cta_rejects_short_history() -> None:
    with pytest.raises(ETFCTAError, match="200 daily"):
        calculate_cta("QQQ", [bar(date(2026, 1, 1), 100)])
