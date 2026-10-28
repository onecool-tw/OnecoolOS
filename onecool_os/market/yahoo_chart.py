"""Bounded same-provider daily chart fallback; no imputation or live quotes."""
from datetime import datetime, date
from zoneinfo import ZoneInfo
from urllib.parse import quote
from urllib.request import Request, urlopen
from math import isfinite
import json
from onecool_os.market.etf_cta import DailyBar


def parse_adjusted_chart(payload, expected_as_of):
    cutoff = date.fromisoformat(expected_as_of)
    result = payload["chart"]["result"][0]
    if result["meta"].get("exchangeTimezoneName") != "America/New_York":
        raise ValueError("US_CHART_EXCHANGE_TIMEZONE_MISMATCH")
    stamps = result["timestamp"]
    q = result["indicators"]["quote"][0]
    adjusted = result["indicators"]["adjclose"][0]["adjclose"]
    if any(len(q[k]) != len(stamps) for k in ("open", "high", "low", "close", "volume")) or len(adjusted) != len(stamps):
        raise ValueError("CHART_ARRAY_LENGTH_MISMATCH")
    bars = []
    for i, timestamp in enumerate(stamps):
        day = datetime.fromtimestamp(timestamp, ZoneInfo("America/New_York")).date()
        if day > cutoff:
            continue
        values = [q[k][i] for k in ("open", "high", "low", "close")]+[adjusted[i]]
        volume = q["volume"][i]
        if any(v is None or not isfinite(float(v)) or v <= 0 for v in values) or volume is None or volume < 0 or int(volume) != volume:
            raise ValueError("CHART_OHLCV_INCOMPLETE")
        factor = adjusted[i]/q["close"][i]
        bars.append(DailyBar(trading_date=day, open=q["open"][i]*factor,
                            high=q["high"][i]*factor, low=q["low"][i]*factor,
                            close=adjusted[i], volume=int(volume), adjusted_close=adjusted[i],
                            source="yahoo_finance_adjusted_chart"))
    if len({b.trading_date for b in bars}) != len(bars) or bars != sorted(bars, key=lambda b: b.trading_date):
        raise ValueError("CHART_DUPLICATE_OR_UNSORTED_DATES")
    return bars


def fetch_adjusted_chart(symbol, expected_as_of):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe='')}?range=2y&interval=1d&events=div%2Csplits"
    request = Request(url, headers={"User-Agent": "OnecoolOS research"})
    with urlopen(request, timeout=12) as response:
        payload = json.load(response)
    if payload["chart"]["result"][0]["meta"]["symbol"] != symbol:
        raise ValueError("CHART_SECURITY_MAPPING_MISMATCH")
    return parse_adjusted_chart(payload, expected_as_of)
