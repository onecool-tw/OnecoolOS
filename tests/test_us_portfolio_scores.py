from dataclasses import replace
from datetime import timedelta

import pytest

from onecool_os.market.us_breakout_scan import (
    FundamentalMetrics, PORTFOLIO_SYMBOLS, build_breakout_scan_payload,
)
from onecool_os.market.us_portfolio_scores import build_portfolio_score_payload
from tests.test_us_breakout_scan import _history, _fundamental


def inputs():
    histories = {s: _history() for s in (*PORTFOLIO_SYMBOLS, "SPY")}
    cutoff = histories["SPY"][-1].trading_date.isoformat()
    fundamentals = {s: _fundamental(cutoff) for s in PORTFOLIO_SYMBOLS}
    return histories, cutoff, fundamentals


def test_scan_and_portfolio_use_identical_scores_and_thresholds():
    histories, cutoff, fundamentals = inputs()
    portfolio = build_portfolio_score_payload(histories, expected_as_of=cutoff,
                                              fundamentals=fundamentals)
    scan = build_breakout_scan_payload(histories, fundamentals,
        spy_history=histories["SPY"], expected_as_of=cutoff, universe=PORTFOLIO_SYMBOLS)
    assert portfolio["data_status"] == "READY"
    assert portfolio["score_version"] == scan["score_version"]
    assert portfolio["price_basis"] == scan["price_basis"]
    assert portfolio["thresholds"] == scan["thresholds"] == {"canslim": 70, "minervini": 80}
    by_symbol = {r["symbol"]: r for r in scan["top5"]}
    for result in portfolio["results"]:
        for field in ("canslim_score", "minervini_score", "passes_dual_system",
                      "fundamentals_as_of", "validation_status"):
            assert result[field] == by_symbol[result["symbol"]][field]


@pytest.mark.parametrize("kind", ["missing", "stale", "future", "incomplete"])
def test_invalid_fundamentals_are_unknown_not_old_baselines(kind):
    histories, cutoff, fundamentals = inputs()
    f = fundamentals["XYZ"]
    if kind == "missing":
        del fundamentals["XYZ"]
    elif kind == "stale":
        fundamentals["XYZ"] = replace(f, as_of="2020-08-02")
    elif kind == "future":
        fundamentals["XYZ"] = replace(f, as_of="2099-01-01")
    else:
        fundamentals["XYZ"] = replace(f, annual_eps_growth=None)
    p = build_portfolio_score_payload(histories, expected_as_of=cutoff, fundamentals=fundamentals)
    xyz = next(r for r in p["results"] if r["symbol"] == "XYZ")
    assert p["data_status"] == "PARTIAL"
    assert xyz["canslim_score"] is None
    assert xyz["minervini_score"] is not None
    assert xyz["passes_dual_system"] is None
    assert xyz["validation_status"] == "Technical Data Validation Failed"


def test_bad_history_is_isolated_to_affected_holding():
    histories, cutoff, fundamentals = inputs()
    histories["BABA"] = histories["BABA"][:-1]
    p = build_portfolio_score_payload(histories, expected_as_of=cutoff, fundamentals=fundamentals)
    assert p["results"][0]["minervini_score"] is None
    assert p["results"][1]["validation_status"] == "PASSED"


def test_no_fundamental_inputs_never_returns_ready():
    histories, cutoff, _ = inputs()
    p = build_portfolio_score_payload(histories, expected_as_of=cutoff)
    assert len(p["results"]) == 5
    assert p["data_status"] == "PARTIAL"
    assert all(r["canslim_score"] is None for r in p["results"])
