from datetime import date, timedelta

import pytest

from onecool_os.market.etf_cta import (
    AlphaVantageClient,
    DailyBar,
    ETFCTAError,
    calculate_cta,
    merge_and_adjust,
    parse_alpha_vantage,
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
