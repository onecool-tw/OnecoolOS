from datetime import date, timedelta
from dataclasses import replace

import pandas as pd
import pytest

from onecool_os.market.etf_cta import DailyBar
from onecool_os.market.us_breakout_scan import (
    FundamentalMetrics,
    US_BREAKOUT_UNIVERSE,
    US_BREAKOUT_UNIVERSE_TARGET_SIZE,
    US_BREAKOUT_UNIVERSE_VERSION,
    US_SECURITY_MASTER,
    build_breakout_scan_payload,
    fetch_yahoo_breakout_inputs,
    _bars_from_download,
    technical_confidence,
)


def _history(*, strength: float = 0.25, days: int = 320, end_volume: int = 2_000_000):
    start = date(2025, 10, 1)
    bars = []
    for index in range(days):
        close = 100 + index * strength
        bars.append(DailyBar(
            trading_date=start + timedelta(days=index),
            open=close - 0.5,
            high=close + 1,
            low=close - 1,
            close=close,
            volume=end_volume if index == days - 1 else 1_000_000,
            adjusted_close=close,
            source="test_adjusted",
        ))
    return bars


def _fundamental(as_of: str) -> FundamentalMetrics:
    return FundamentalMetrics(
        as_of=as_of,
        quarterly_eps_growth=0.5,
        quarterly_revenue_growth=0.3,
        annual_eps_growth=0.4,
        institutional_holders_available=True,
    )


def test_breakout_scan_is_same_cutoff_ranked_and_limited_to_five() -> None:
    spy = _history(strength=0.1)
    as_of = spy[-1].trading_date.isoformat()
    universe = US_BREAKOUT_UNIVERSE[:7]
    histories = {
        symbol: _history(strength=0.2 + index * 0.03)
        for index, symbol in enumerate(universe)
    }
    fundamentals = {symbol: _fundamental(as_of) for symbol in universe}

    payload = build_breakout_scan_payload(
        histories,
        fundamentals,
        spy_history=spy,
        expected_as_of=as_of,
        universe=universe,
    )

    assert payload["data_status"] == "READY"
    assert payload["expected_as_of"] == as_of
    assert payload["universe_size"] == 7
    assert len(payload["top5"]) == 5
    assert all(item["price_as_of"] == as_of for item in payload["top5"])
    assert all(item["technical_confidence"] >= 90 for item in payload["top5"])
    assert all(item["status"] == "BREAKOUT" for item in payload["top5"])


def test_mixed_cutoff_is_excluded_instead_of_carried_forward() -> None:
    spy = _history()
    as_of = spy[-1].trading_date.isoformat()
    histories = {"NVDA": _history(), "XYZ": _history()[:-1]}
    fundamentals = {
        "NVDA": _fundamental(as_of),
        "XYZ": _fundamental(as_of),
    }

    payload = build_breakout_scan_payload(
        histories,
        fundamentals,
        spy_history=spy,
        expected_as_of=as_of,
        universe=("NVDA", "XYZ"),
    )

    assert [item["symbol"] for item in payload["top5"]] == ["NVDA"]
    stale = next(item for item in payload["exclusions"] if item["symbol"] == "XYZ")
    assert stale["technical_confidence"] < 90
    assert "cutoff mismatch" in stale["reason"]


def test_technical_confidence_requires_liquidity() -> None:
    bars = _history()
    illiquid = [DailyBar(**{**bar.__dict__, "volume": 100}) for bar in bars]

    score, reasons = technical_confidence(illiquid, bars[-1].trading_date)

    assert score == 85
    assert "liquidity" in "; ".join(reasons)


@pytest.mark.parametrize("batch_missing", [False, True])
def test_yahoo_input_loader_uses_batch_prices_and_shortlists_fundamentals(batch_missing) -> None:
    spy = _history(strength=0.1)
    dates = pd.to_datetime([bar.trading_date for bar in spy])
    columns = pd.MultiIndex.from_product([
        ["AAA", "BBB"], ["Open", "High", "Low", "Close", "Volume"]
    ])
    rows = []
    for index in range(len(dates)):
        row = []
        for strength in (0.3, 0.2):
            close = 100 + index * strength
            row.extend((close - 0.5, close + 1, close - 1, close, 2_000_000))
        rows.append(row)
    frame = pd.DataFrame(rows, index=dates, columns=columns)
    quarter_timestamp = int(pd.Timestamp(spy[-1].trading_date, tz="UTC").timestamp())

    class FakeTicker:
        info = {
            "mostRecentQuarter": quarter_timestamp,
            "earningsQuarterlyGrowth": 0.5,
            "revenueGrowth": 0.3,
            "earningsGrowth": 0.4,
            "heldPercentInstitutions": 0.7,
        }

    class FakeYahoo:
        @staticmethod
        def download(*args, **kwargs):
            assert kwargs["auto_adjust"] is True
            if set(args[0]) == {"AAA", "BBB"}:
                return frame.drop(columns="BBB", level=0) if batch_missing else frame
            assert args[0] == ["BBB"] and kwargs["threads"] is False
            return frame[["BBB"]]

        @staticmethod
        def Ticker(symbol):
            return FakeTicker()

    cache, diagnostics = {}, {}
    histories, fundamentals = fetch_yahoo_breakout_inputs(
        FakeYahoo,
        expected_as_of=spy[-1].trading_date.isoformat(),
        spy_history=spy,
        universe=("AAA", "BBB"),
        fundamental_shortlist_size=1,
        fundamental_cache=cache, fetch_diagnostics=diagnostics,
    )

    assert set(histories) == {"AAA", "BBB"}
    assert all(len(history) == len(spy) for history in histories.values())
    assert len(fundamentals) == 1
    assert "AAA" in fundamentals
    assert diagnostics == {"AAA": "FETCHED", "BBB": "NOT_REQUESTED"}
    diagnostics = {}
    _, second = fetch_yahoo_breakout_inputs(
        FakeYahoo, expected_as_of=spy[-1].trading_date.isoformat(),
        spy_history=spy, universe=("AAA", "BBB"), fundamental_shortlist_size=1,
        fundamental_cache=cache, fetch_diagnostics=diagnostics,
    )
    assert set(second) == {"AAA", "BBB"}
    assert diagnostics == {"AAA": "CACHED_VALID", "BBB": "FETCHED"}
    _, full = fetch_yahoo_breakout_inputs(
        FakeYahoo, expected_as_of=spy[-1].trading_date.isoformat(),
        spy_history=spy, universe=("AAA", "BBB"),
    )
    assert set(full) == {"AAA", "BBB"}


def test_batch_union_leading_missing_rows_do_not_discard_valid_history() -> None:
    bars = _history(days=320)
    dates = pd.to_datetime([
        bars[0].trading_date - timedelta(days=1),
        *(bar.trading_date for bar in bars),
    ])
    rows = [[float("nan")] * 5] + [
        [bar.open, bar.high, bar.low, bar.close, bar.volume]
        for bar in bars
    ]
    columns = pd.MultiIndex.from_product([
        ["AAA"], ["Open", "High", "Low", "Close", "Volume"]
    ])
    frame = pd.DataFrame(rows, index=dates, columns=columns)

    recovered = _bars_from_download(frame, "AAA", bars[-1].trading_date)

    assert len(recovered) == len(bars)
    assert recovered[-1].trading_date == bars[-1].trading_date
    frame.loc[dates[100], ("AAA", "Close")] = float("nan")
    assert _bars_from_download(frame, "AAA", bars[-1].trading_date) == []


def test_every_missing_batch_symbol_is_retried_without_synthesizing_bars() -> None:
    spy = _history(days=320)
    symbols = tuple(f"S{i:02d}" for i in range(20))
    dates = pd.to_datetime([bar.trading_date for bar in spy])
    columns = pd.MultiIndex.from_product([
        symbols, ["Open", "High", "Low", "Close", "Volume"]
    ])
    rows = [
        [item for symbol in symbols for item in (
            bar.open, bar.high, bar.low, bar.close, bar.volume,
        )]
        for bar in spy
    ]
    frame = pd.DataFrame(rows, index=dates, columns=columns)
    calls = []

    class FakeYahoo:
        @staticmethod
        def download(requested, **kwargs):
            calls.append(tuple(requested))
            if len(requested) > 1:
                return frame[[requested[0]]]
            if requested[0] == symbols[-1]:
                return pd.DataFrame()
            return frame[[requested[0]]]

        @staticmethod
        def Ticker(symbol):
            raise AssertionError("no fundamentals requested")

    histories, _ = fetch_yahoo_breakout_inputs(
        FakeYahoo,
        expected_as_of=spy[-1].trading_date.isoformat(),
        spy_history=spy,
        universe=symbols,
        fundamental_shortlist_size=0,
    )

    assert len([call for call in calls if len(call) == 1]) == 18
    assert all(len(histories[s]) == 320 for s in symbols[:-1])
    assert histories[symbols[-1]] == []


def test_calendar_mismatch_retries_ticker_and_keeps_gate_strict() -> None:
    spy = _history(days=320)
    dates = pd.to_datetime([bar.trading_date for bar in spy])
    frame = pd.DataFrame({
        "Open": [bar.open for bar in spy],
        "High": [bar.high for bar in spy],
        "Low": [bar.low for bar in spy],
        "Close": [bar.close for bar in spy],
        "Volume": [bar.volume for bar in spy],
    }, index=dates)
    calls = []

    class FakeYahoo:
        @staticmethod
        def download(requested, **kwargs):
            calls.append(tuple(requested))
            if len(calls) == 1:
                return frame.drop(index=dates[-10])
            return frame

        @staticmethod
        def Ticker(symbol):
            raise AssertionError("no fundamentals requested")

    histories, _ = fetch_yahoo_breakout_inputs(
        FakeYahoo,
        expected_as_of=spy[-1].trading_date.isoformat(),
        spy_history=spy,
        universe=("AAA",),
        fundamental_shortlist_size=0,
    )

    assert len(calls) == 2
    assert [bar.trading_date for bar in histories["AAA"][-252:]] == [
        bar.trading_date for bar in spy[-252:]
    ]


def test_ticker_history_fallback_recovers_only_calendar_complete_series() -> None:
    spy = _history(days=320)
    dates = pd.to_datetime([bar.trading_date for bar in spy])
    frame = pd.DataFrame({
        "Open": [bar.open for bar in spy],
        "High": [bar.high for bar in spy],
        "Low": [bar.low for bar in spy],
        "Close": [bar.close for bar in spy],
        "Volume": [bar.volume for bar in spy],
    }, index=dates)

    class FakeTicker:
        info = {}

        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, **kwargs):
            if self.symbol == "AAA":
                return frame
            return frame.drop(index=dates[-10])

    class FakeYahoo:
        Ticker = FakeTicker

        @staticmethod
        def download(requested, **kwargs):
            return pd.DataFrame()

    diagnostics = {}
    histories, _ = fetch_yahoo_breakout_inputs(
        FakeYahoo,
        expected_as_of=spy[-1].trading_date.isoformat(),
        spy_history=spy,
        universe=("AAA", "BBB"),
        fundamental_shortlist_size=0,
        price_diagnostics=diagnostics,
    )

    assert len(histories["AAA"]) == 320
    assert "AAA" not in diagnostics
    assert histories["BBB"] == []
    assert diagnostics["BBB"]["status"] == "TECHNICAL_DATA_VALIDATION_FAILED"
    assert diagnostics["BBB"]["observations"] == 319
    assert diagnostics["BBB"]["missing_spy_sessions"] == 1
    assert diagnostics["BBB"]["missing_spy_dates"] == [spy[-10].trading_date.isoformat()]


def test_missing_session_is_recovered_only_from_real_adjusted_day_bar() -> None:
    spy = _history(days=320)
    dates = pd.to_datetime([bar.trading_date for bar in spy])
    frame = pd.DataFrame({
        "Open": [bar.open for bar in spy],
        "High": [bar.high for bar in spy],
        "Low": [bar.low for bar in spy],
        "Close": [bar.close for bar in spy],
        "Volume": [bar.volume for bar in spy],
    }, index=dates)
    missing_day = dates[-10]

    class FakeTicker:
        info = {}

        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, **kwargs):
            if "start" in kwargs:
                return frame.loc[[missing_day]] if self.symbol == "AAA" else pd.DataFrame()
            return frame.drop(index=missing_day)

    class FakeYahoo:
        Ticker = FakeTicker

        @staticmethod
        def download(requested, **kwargs):
            return pd.DataFrame()

    diagnostics = {}
    histories, _ = fetch_yahoo_breakout_inputs(
        FakeYahoo,
        expected_as_of=spy[-1].trading_date.isoformat(),
        spy_history=spy,
        universe=("AAA", "BBB"),
        fundamental_shortlist_size=0,
        price_diagnostics=diagnostics,
    )

    assert [bar.trading_date for bar in histories["AAA"][-252:]] == [
        bar.trading_date for bar in spy[-252:]
    ]
    assert histories["BBB"] == []
    assert diagnostics["BBB"]["missing_spy_dates"] == [missing_day.date().isoformat()]


def test_scan_refuses_to_publish_an_empty_validated_universe() -> None:
    spy = _history()
    as_of = spy[-1].trading_date.isoformat()

    with pytest.raises(ValueError, match="no candidate"):
        build_breakout_scan_payload(
            {"STALE": _history()[:-1]},
            {},
            spy_history=spy,
            expected_as_of=as_of,
            universe=("STALE",),
        )


def test_production_universe_has_an_explicit_security_mapping() -> None:
    assert set(US_BREAKOUT_UNIVERSE) <= set(US_SECURITY_MASTER)
    assert US_SECURITY_MASTER["TSM"].security_type == "ADR"


@pytest.mark.parametrize("bad", ["stale", "unmapped", "ohlc", "missing_close", "calendar"])
def test_validation_gate_excludes_bad_candidate(bad):
    history = _history()
    cutoff = history[-1].trading_date.isoformat()
    symbol = "DE" if bad != "unmapped" else "UNKNOWN_SYMBOL"
    candidate = list(history)
    fundamental = _fundamental(cutoff)
    if bad == "stale":
        fundamental = replace(fundamental, as_of="2020-08-02")
    elif bad == "ohlc":
        candidate[-1] = replace(candidate[-1], high=1)
    elif bad == "missing_close":
        candidate[-1] = replace(candidate[-1], adjusted_close=None)
    elif bad == "calendar":
        candidate.pop(-100)
    scan = build_breakout_scan_payload(
        {"NVDA": history, symbol: candidate},
        {"NVDA": _fundamental(cutoff), symbol: fundamental},
        spy_history=history, expected_as_of=cutoff, universe=("NVDA", symbol),
    )
    assert [r["symbol"] for r in scan["top5"]] == ["NVDA"]
    assert scan["exclusions"][0]["symbol"] == symbol


def test_production_universe_governance_is_explicit_and_stable() -> None:
    assert len(US_BREAKOUT_UNIVERSE) == US_BREAKOUT_UNIVERSE_TARGET_SIZE == 70
    assert US_BREAKOUT_UNIVERSE_VERSION == "2026Q3-v1"

    spy = _history(strength=0.1)
    as_of = spy[-1].trading_date.isoformat()
    histories = {
        symbol: _history(strength=0.2)
        for symbol in US_BREAKOUT_UNIVERSE[:2]
    }
    fundamentals = {
        symbol: _fundamental(as_of)
        for symbol in histories
    }
    payload = build_breakout_scan_payload(
        histories,
        fundamentals,
        spy_history=spy,
        expected_as_of=as_of,
        universe=tuple(histories),
    )
    governance = payload["universe_governance"]
    assert governance["version"] == US_BREAKOUT_UNIVERSE_VERSION
    assert governance["review_cadence"] == (
        "QUARTERLY_AFTER_LAST_FULL_US_SESSION"
    )
    assert governance["daily_membership_mutation"] is False
    assert governance["change_control"] == (
        "VERSION_BUMP_AND_AUDIT_RECORD_REQUIRED"
    )
