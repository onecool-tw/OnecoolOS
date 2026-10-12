from datetime import UTC, date, datetime

import pytest

from onecool_os.market.etf_cta import ETFCTAError
from onecool_os.market.history_bootstrap import _parse_btc_hourly_day


DAY = date(2026, 10, 11)


def payload():
    start = int(datetime(2026, 10, 11, tzinfo=UTC).timestamp())
    return {"chart": {"result": [{
        "meta": {"symbol": "BTC-USD", "currency": "USD", "dataGranularity": "1h"},
        "timestamp": [start+i*3600 for i in range(24)],
        "indicators": {"quote": [{"open": [100+i for i in range(24)],
                                  "high": [102+i for i in range(24)],
                                  "low": [99+i for i in range(24)],
                                  "close": [101+i for i in range(24)], "volume": [10]*24}]},
    }]}}


def test_complete_real_hourly_day_produces_auditable_daily_bar():
    bar, evidence = _parse_btc_hourly_day(payload(), DAY)
    assert (bar.open, bar.high, bar.low, bar.close, bar.volume) == (100, 125, 99, 124, 240)
    assert evidence["observations"] == 24
    assert len(evidence["samples"]) == 24 and len(evidence["samples_sha256"]) == 64
    assert bar.source == "yahoo_finance_utc_hourly_aggregation"


@pytest.mark.parametrize("issue", ["missing", "duplicate", "shifted", "wrong_symbol", "wrong_interval", "null"])
def test_incomplete_or_wrong_hourly_evidence_is_rejected(issue):
    p = payload(); x=p["chart"]["result"][0]
    if issue == "missing": x["timestamp"].pop()
    if issue == "duplicate": x["timestamp"][-1]=x["timestamp"][-2]
    if issue == "shifted": x["timestamp"][0]+=60
    if issue == "wrong_symbol": x["meta"]["symbol"]="ETH-USD"
    if issue == "wrong_interval": x["meta"]["dataGranularity"]="1d"
    if issue == "null": x["indicators"]["quote"][0]["close"][0]=None
    with pytest.raises((ETFCTAError, TypeError)):
        _parse_btc_hourly_day(p, DAY)
