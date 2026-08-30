from __future__ import annotations

import pandas as pd

from onecool_os.market.rate_asset_backtest import (
    backtest_asset,
    build_rate_states,
    classify_direction,
    infer_split_factor,
    month_end,
    yahoo_result_to_adjusted_close,
)


def _series(values: list[float], name: str) -> pd.Series:
    index = pd.date_range("2020-01-31", periods=len(values), freq="ME")
    return pd.Series(values, index=index, name=name)


def test_month_end_uses_last_observation() -> None:
    series = pd.Series(
        [1.0, 2.0, 3.0],
        index=pd.to_datetime(["2024-01-02", "2024-01-31", "2024-02-01"]),
    )
    result = month_end(series)
    assert list(result) == [2.0, 3.0]
    assert result.index[0] == pd.Timestamp("2024-01-31")


def test_direction_uses_three_month_25bp_threshold() -> None:
    series = _series([1.0, 1.1, 1.2, 1.3, 1.0, 0.9, 0.9], "DGS10")
    states = classify_direction(series)
    assert states.iloc[3] == "RISING"
    assert states.iloc[5] == "FALLING"
    assert states.iloc[6] == "FALLING"


def test_curve_keeps_level_and_direction_separate() -> None:
    rates = {
        "DFF": _series([1, 1, 1, 1, 1, 1], "DFF"),
        "DGS2": _series([2, 2, 2, 2, 2, 2], "DGS2"),
        "DGS10": _series([3, 3, 3, 3, 3, 3], "DGS10"),
        "DGS30": _series([4, 4, 4, 4, 4, 4], "DGS30"),
        "T10Y2Y": _series([0.2, 0.1, -0.1, -0.2, 0.1, 0.4], "T10Y2Y"),
    }
    states = build_rate_states(rates)
    assert states["T10Y2Y_LEVEL"].iloc[2] == "INVERTED"
    assert states["T10Y2Y_LEVEL"].iloc[5] == "POSITIVE"
    assert states["T10Y2Y_DIRECTION"].iloc[5] == "STEEPENING"


def test_backtest_forward_return_does_not_use_future_state() -> None:
    rates = {
        "DFF": _series([1, 1, 1, 1.3, 1.6, 1.9, 2.2, 2.5], "DFF"),
        "DGS2": _series([1, 1, 1, 1, 1, 1, 1, 1], "DGS2"),
        "DGS10": _series([2, 2, 2, 2, 2, 2, 2, 2], "DGS10"),
        "DGS30": _series([3, 3, 3, 3, 3, 3, 3, 3], "DGS30"),
        "T10Y2Y": _series([1, 1, 1, 1, 1, 1, 1, 1], "T10Y2Y"),
    }
    states = build_rate_states(rates)
    prices = _series([100, 100, 100, 100, 110, 121, 133.1, 146.41], "asset")
    result = backtest_asset(prices, rates, states)
    rising = next(
        row
        for row in result["state_results"]
        if row["rate_state_id"] == "DFF" and row["state"] == "RISING"
    )
    assert rising["forward"]["1"]["mean_return_pct"] == 10.0
    assert rising["forward"]["1"]["sample_months"] == 4
    assert rising["state_onsets"]["1"]["mean_return_pct"] == 10.0
    assert rising["state_onsets"]["1"]["sample_months"] == 1


def test_yahoo_parser_adjusts_split_instead_of_creating_false_loss() -> None:
    result = {
        "timestamp": [1703980800, 1704067200],
        "indicators": {"quote": [{"close": [100.0, 25.0]}]},
        "events": {
            "splits": {
                "1704067200": {
                    "date": 1704067200,
                    "numerator": 4.0,
                    "denominator": 1.0,
                }
            }
        },
    }
    prices = yahoo_result_to_adjusted_close(result, "TEST")
    assert list(prices) == [25.0, 25.0]


def test_split_inference_is_conservative_and_handles_reverse_splits() -> None:
    assert infer_split_factor(100.0, 25.1) == 4.0
    assert infer_split_factor(25.0, 99.0) == 0.25
    assert infer_split_factor(100.0, 62.0) == 1.0
