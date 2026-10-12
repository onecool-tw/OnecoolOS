"""One-time historical bootstrap providers for the Market Dashboard."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import json
import hashlib
from math import isfinite
from urllib.request import Request, urlopen
from typing import Any

from onecool_os.market.etf_cta import DailyBar, ETFCTAError


class YahooHistoryBootstrapper:
    """Build a missing GitHub history once; never used by cache consumers."""

    provider_id = "yahoo_finance_bootstrap"

    def __init__(self, yfinance_module: Any | None = None) -> None:
        self._yfinance = yfinance_module
        self.btc_day_repairs: dict[str, dict] = {}

    def fetch_btc_completed_day(self, day: date) -> list[DailyBar]:
        """Repair one missing UTC day from the same Yahoo BTC-USD series."""
        start = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
        end = start + timedelta(days=1)
        url = ("https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD"
               f"?period1={int(start.timestamp())}&period2={int(end.timestamp())}&interval=1d")
        try:
            request = Request(url, headers={"User-Agent": "OnecoolOS/1.0 exact BTC day"})
            with urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return _parse_btc_completed_day(payload, day)
        except Exception:
            # Yahoo may leave a daily row null while all hourly bars exist.
            # Aggregate only a complete actual UTC day, without imputation.
            url = "https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?range=1mo&interval=60m"
            request = Request(url, headers={"User-Agent": "OnecoolOS/1.0 BTC hourly repair"})
            with urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
            bar, evidence = _parse_btc_hourly_day(payload, day)
            evidence["source_url"] = url
            evidence["fetched_at"] = datetime.now(UTC).isoformat()
            self.btc_day_repairs[day.isoformat()] = evidence
            return [bar]

    def fetch_daily(self, symbol: str) -> list[DailyBar]:
        """Fetch enough raw daily history for the shared CTA engine."""

        bars = self.fetch_raw_daily(symbol, period="5y")
        if len(bars) < 260:
            raise ETFCTAError(
                f"Yahoo Finance bootstrap for {symbol} returned only "
                f"{len(bars)} observations; at least 260 are required."
            )
        return bars

    def fetch_raw_daily(
        self, symbol: str, *, period: str = "10d"
    ) -> list[DailyBar]:
        """Fetch raw Yahoo OHLCV plus dividends and splits."""

        if self._yfinance is None:
            try:
                self._yfinance = __import__("yfinance")
            except Exception as exc:  # noqa: BLE001 - provider boundary.
                raise ETFCTAError(
                    "Yahoo Finance bootstrap provider is unavailable."
                ) from exc

        try:
            frame = self._yfinance.Ticker(symbol).history(
                period=period,
                interval="1d",
                auto_adjust=False,
                actions=True,
                timeout=12,
            )
        except Exception as exc:  # noqa: BLE001 - provider boundary.
            raise ETFCTAError(
                f"Yahoo Finance bootstrap failed for {symbol}: {exc}"
            ) from exc
        if frame is None or frame.empty:
            raise ETFCTAError(
                f"Yahoo Finance bootstrap returned no history for {symbol}."
            )

        bars = []
        for timestamp, row in frame.iterrows():
            trading_date = _as_date(timestamp)
            bars.append(
                DailyBar(
                    trading_date=trading_date,
                    open=_number(row, "Open"),
                    high=_number(row, "High"),
                    low=_number(row, "Low"),
                    close=_number(row, "Close"),
                    volume=int(_number(row, "Volume", 0.0)),
                    dividend=_number(row, "Dividends", 0.0),
                    split_factor=(
                        _number(row, "Stock Splits", 0.0) or 1.0
                    ),
                    source="yahoo_finance_raw",
                )
            )
        bars.sort(key=lambda bar: bar.trading_date)
        return bars

    def fetch_adjusted_daily(self, symbol: str) -> list[DailyBar]:
        """Fetch split/dividend-adjusted history for an unsupported AV symbol."""

        if self._yfinance is None:
            try:
                self._yfinance = __import__("yfinance")
            except Exception as exc:  # noqa: BLE001 - provider boundary.
                raise ETFCTAError(
                    "Yahoo Finance fallback provider is unavailable."
                ) from exc

        try:
            frame = self._yfinance.Ticker(symbol).history(
                period="5y",
                interval="1d",
                auto_adjust=True,
                actions=False,
            )
        except Exception as exc:  # noqa: BLE001 - provider boundary.
            raise ETFCTAError(
                f"Yahoo Finance fallback failed for {symbol}: {exc}"
            ) from exc
        if frame is None or frame.empty:
            raise ETFCTAError(
                f"Yahoo Finance fallback returned no history for {symbol}."
            )

        bars = [
            DailyBar(
                trading_date=_as_date(timestamp),
                open=_number(row, "Open"),
                high=_number(row, "High"),
                low=_number(row, "Low"),
                close=_number(row, "Close"),
                volume=int(_number(row, "Volume", 0.0)),
                source="yahoo_finance_adjusted_fallback",
            )
            for timestamp, row in frame.iterrows()
        ]
        bars.sort(key=lambda bar: bar.trading_date)
        if len(bars) < 260:
            raise ETFCTAError(
                f"Yahoo Finance fallback for {symbol} returned only "
                f"{len(bars)} observations; at least 260 are required."
            )
        return bars


def _parse_btc_hourly_day(payload: dict, day: date):
    if day >= datetime.now(UTC).date():
        raise ETFCTAError("BTC repair day must be completed in UTC.")
    results = payload.get("chart", {}).get("result") or []
    if len(results) != 1:
        raise ETFCTAError("BTC hourly response unavailable.")
    item = results[0]
    meta = item.get("meta", {})
    if meta.get("symbol") != "BTC-USD" or meta.get("currency") != "USD":
        raise ETFCTAError("BTC hourly series identity mismatch.")
    if meta.get("dataGranularity") not in (None, "1h", "60m"):
        raise ETFCTAError("BTC hourly granularity mismatch.")
    quote = item["indicators"]["quote"][0]
    samples = []
    for i, stamp in enumerate(item.get("timestamp", [])):
        if datetime.fromtimestamp(stamp, UTC).date() != day:
            continue
        o, h, lo, c = (float(quote[k][i]) for k in ("open", "high", "low", "close"))
        v = int(quote["volume"][i])
        if (not all(isfinite(x) and x > 0 for x in (o, h, lo, c)) or v < 0
                or lo > min(o, c) or h < max(o, c)):
            raise ETFCTAError("Invalid BTC hourly observation.")
        samples.append(dict(timestamp=stamp, open=o, high=h, low=lo, close=c, volume=v))
    start = int(datetime.combine(day, datetime.min.time(), tzinfo=UTC).timestamp())
    expected = [start + i * 3600 for i in range(24)]
    if [row["timestamp"] for row in samples] != expected:
        raise ETFCTAError("BTC UTC day needs exactly 24 unique consecutive hourly bars.")
    bar = DailyBar(trading_date=day, open=samples[0]["open"],
                   high=max(r["high"] for r in samples), low=min(r["low"] for r in samples),
                   close=samples[-1]["close"], volume=sum(r["volume"] for r in samples),
                   source="yahoo_finance_utc_hourly_aggregation")
    digest = hashlib.sha256(json.dumps(samples, sort_keys=True, allow_nan=False).encode()).hexdigest()
    return bar, {"symbol": "BTC-USD", "currency": "USD", "date": day.isoformat(),
                 "method": "UTC 00:00-24:00; first open, max high, min low, last close, sum provider hourly volume",
                 "observations": 24, "excluded": "all other UTC days; no missing-value filling",
                 "samples_sha256": digest, "samples": samples}


def _parse_btc_completed_day(payload: dict, day: date) -> list[DailyBar]:
    results = payload.get("chart", {}).get("result") or []
    if len(results) != 1:
        raise ETFCTAError("Exact BTC day response unavailable.")
    item = results[0]
    meta = item.get("meta", {})
    if meta.get("symbol") != "BTC-USD" or meta.get("currency") != "USD":
        raise ETFCTAError("Exact BTC series identity mismatch.")
    quote = item["indicators"]["quote"][0]
    bars = []
    for i, stamp in enumerate(item.get("timestamp", [])):
        if datetime.fromtimestamp(stamp, UTC).date() != day:
            continue
        o, h, lo, c = (float(quote[k][i]) for k in ("open", "high", "low", "close"))
        v = int(quote["volume"][i])
        if (not all(isfinite(x) and x > 0 for x in (o, h, lo, c)) or v < 0
                or lo > min(o, c) or h < max(o, c)):
            raise ETFCTAError("Invalid exact BTC daily observation.")
        bars.append(DailyBar(trading_date=day, open=o, high=h, low=lo,
                             close=c, volume=v, source="yahoo_finance_raw"))
    if len(bars) != 1:
        raise ETFCTAError("Exact BTC day missing or duplicated.")
    return bars


def _as_date(value: Any) -> date:
    converted = getattr(value, "date", None)
    if callable(converted):
        return converted()
    return date.fromisoformat(str(value)[:10])


def _number(row: Any, key: str, default: float | None = None) -> float:
    try:
        value = row[key]
        if value is None and default is not None:
            return default
        return float(value)
    except (KeyError, TypeError, ValueError) as exc:
        if default is not None:
            return default
        raise ETFCTAError(f"Yahoo Finance bootstrap field {key} is invalid.") from exc
