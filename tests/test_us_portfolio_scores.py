from datetime import date, timedelta

import pytest

from onecool_os.market.etf_cta import DailyBar, merge_and_adjust
from onecool_os.market.us_portfolio_scores import (
    FUNDAMENTAL_SNAPSHOTS,
    build_portfolio_score_payload,
)


def _history(*, strength: float = 1.0, days: int = 320):
    start = date(2025, 10, 1)
    return merge_and_adjust(
        [],
        [
            DailyBar(
                trading_date=start + timedelta(days=index),
                open=100 + index * strength,
                high=101 + index * strength,
                low=99 + index * strength,
                close=100 + index * strength,
                volume=1000 + index,
            )
            for index in range(days)
        ],
    )


def test_scores_are_current_bounded_and_auditable() -> None:
    histories = {"SPY": _history(strength=0.5)}
    histories.update({symbol: _history() for symbol in FUNDAMENTAL_SNAPSHOTS})
    as_of = histories["SPY"][-1].trading_date.isoformat()

    payload = build_portfolio_score_payload(histories, expected_as_of=as_of)

    assert payload["data_status"] == "READY"
    assert payload["expected_as_of"] == as_of
    assert len(payload["results"]) == 5
    for result in payload["results"]:
        assert result["price_as_of"] == as_of
        assert result["validation_status"] == "PASSED"
        assert 0 <= result["canslim_score"] <= 100
        assert 0 <= result["minervini_score"] <= 100
        assert result["fundamentals_as_of"] <= as_of
        assert result["canslim_components"]
        assert result["minervini_components"]


def test_scores_reject_mixed_price_dates() -> None:
    histories = {"SPY": _history()}
    histories.update({symbol: _history() for symbol in FUNDAMENTAL_SNAPSHOTS})
    histories["BABA"] = histories["BABA"][:-1]
    as_of = histories["SPY"][-1].trading_date.isoformat()

    with pytest.raises(ValueError, match="BABA price date"):
        build_portfolio_score_payload(histories, expected_as_of=as_of)


def test_scores_reject_insufficient_history() -> None:
    histories = {"SPY": _history()}
    histories.update({symbol: _history() for symbol in FUNDAMENTAL_SNAPSHOTS})
    histories["RH"] = histories["RH"][-200:]
    as_of = histories["SPY"][-1].trading_date.isoformat()

    with pytest.raises(ValueError, match="RH needs at least 252"):
        build_portfolio_score_payload(histories, expected_as_of=as_of)
