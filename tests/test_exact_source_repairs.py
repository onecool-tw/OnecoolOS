from datetime import UTC, date, datetime, timedelta

import pytest

from onecool_os.market.etf_cta import ETFCTAError
from onecool_os.market.history_bootstrap import _parse_btc_completed_day
from scripts.update_stockq_rotation import _parse_tencent_shanghai_b


def shanghai_payload():
    start = date(2025, 1, 1)
    return {"code": 0, "data": {"sh000003": {
        "qt": {"sh000003": ["1", "Ｂ股指数", "000003"]},
        "day": [[str(start + timedelta(days=i)), "100", "102", "103", "99", "1000"]
                for i in range(260)],
    }}}


def test_exact_shanghai_b_identity_and_ohlc_order():
    bars = _parse_tencent_shanghai_b(shanghai_payload())
    assert len(bars) == 260
    assert (bars[-1].open, bars[-1].close, bars[-1].high, bars[-1].low) == (100, 102, 103, 99)
    assert bars[-1].source == "tencent_exact_sh000003_index"


@pytest.mark.parametrize("problem", ["wrong_index", "duplicate", "nan", "short"])
def test_shanghai_invalid_response_is_not_published(problem):
    payload = shanghai_payload()
    item = payload["data"]["sh000003"]
    if problem == "wrong_index": item["qt"]["sh000003"][2] = "000001"
    if problem == "duplicate": item["day"][-1] = item["day"][-2]
    if problem == "nan": item["day"][0][2] = "nan"
    if problem == "short": item["day"].pop()
    with pytest.raises(ETFCTAError): _parse_tencent_shanghai_b(payload)


def btc_payload():
    stamp = int(datetime(2026, 10, 11, tzinfo=UTC).timestamp())
    return {"chart": {"result": [{
        "meta": {"symbol": "BTC-USD", "currency": "USD"},
        "timestamp": [stamp, stamp + 86400],
        "indicators": {"quote": [{"open": [100, 100], "high": [103, 103],
                                  "low": [99, 99], "close": [102, 102], "volume": [1000, 1000]}]},
    }]}}


def test_exact_btc_day_excludes_following_provisional_day():
    rows = _parse_btc_completed_day(btc_payload(), date(2026, 10, 11))
    assert len(rows) == 1
    assert rows[0].trading_date == date(2026, 10, 11)
    assert rows[0].source == "yahoo_finance_raw"


def test_exact_btc_rejects_other_symbol():
    payload = btc_payload()
    payload["chart"]["result"][0]["meta"]["symbol"] = "ETH-USD"
    with pytest.raises(ETFCTAError):
        _parse_btc_completed_day(payload, date(2026, 10, 11))
