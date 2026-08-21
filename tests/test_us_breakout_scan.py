from datetime import date, timedelta

import pandas as pd
import pytest

from onecool_os.market.etf_cta import DailyBar
from onecool_os.market.us_breakout_scan import (
    FundamentalMetrics,
    US_BREAKOUT_UNIVERSE,
    US_SECURITY_MASTER,
    build_breakout_scan_payload,
    fetch_yahoo_breakout_inputs,
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
    universe = tuple(f"STK{index}" for index in range(7))
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
    histories = {"GOOD": _history(), "STALE": _history()[:-1]}
    fundamentals = {
        "GOOD": _fundamental(as_of),
        "STALE": _fundamental(as_of),
    }

    payload = build_breakout_scan_payload(
        histories,
        fundamentals,
        spy_history=spy,
        expected_as_of=as_of,
        universe=("GOOD", "STALE"),
    )

    assert [item["symbol"] for item in payload["top5"]] == ["GOOD"]
    stale = next(item for item in payload["exclusions"] if item["symbol"] == "STALE")
    assert stale["technical_confidence"] < 90
    assert "cutoff mismatch" in stale["reason"]


def test_technical_confidence_requires_liquidity() -> None:
    bars = _history()
    illiquid = [DailyBar(**{**bar.__dict__, "volume": 100}) for bar in bars]

    score, reasons = technical_confidence(illiquid, bars[-1].trading_date)

    assert score == 85
    assert "liquidity" in "; ".join(reasons)


def test_yahoo_input_loader_uses_batch_prices_and_shortlists_fundamentals() -> None:
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

    class FakeTicker:
        info = {
            "earningsQuarterlyGrowth": 0.5,
            "revenueGrowth": 0.3,
            "earningsGrowth": 0.4,
            "heldPercentInstitutions": 0.7,
        }

    class FakeYahoo:
        @staticmethod
        def download(*args, **kwargs):
            assert set(args[0]) == {"AAA", "BBB"}
            assert kwargs["auto_adjust"] is True
            return frame

        @staticmethod
        def Ticker(symbol):
            return FakeTicker()

    histories, fundamentals = fetch_yahoo_breakout_inputs(
        FakeYahoo,
        expected_as_of=spy[-1].trading_date.isoformat(),
        spy_history=spy,
        universe=("AAA", "BBB"),
        fundamental_shortlist_size=1,
    )

    assert set(histories) == {"AAA", "BBB"}
    assert all(len(history) == len(spy) for history in histories.values())
    assert len(fundamentals) == 1
    assert "AAA" in fundamentals


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
    assert set(US_BREAKOUT_UNIVERSE) == set(US_SECURITY_MASTER)
    assert US_SECURITY_MASTER["TSM"].security_type == "ADR"
