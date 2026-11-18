"""Update Taiwan market CTA histories and the shared daily snapshot."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from decimal import Decimal
from urllib.request import urlopen

from onecool_os.market.taiwan_calendar import latest_twse_session

from onecool_os.market.session_cutoff import completed_daily_bars, latest_completed_market_session

from onecool_os.market.etf_cta import (
    CTAResult,
    DailyBar,
    ETFCTAError,
    calculate_cta,
    merge_and_adjust,
    read_history,
    write_history,
)


TAIWAN_CTA_SYMBOLS = {
    "0050": "0050.TW",
    "2330": "2330.TW",
}


def fetch_yahoo_daily(symbol: str, *, period: str = "10d", start=None, end=None) -> list[DailyBar]:
    """Fetch raw Yahoo daily bars for a Taiwan-listed symbol."""

    import yfinance as yf

    window = {"period": period} if start is None else {"start": start, "end": end}
    frame = yf.Ticker(symbol).history(auto_adjust=False, actions=True, **window)
    if frame.empty:
        raise ETFCTAError(f"Yahoo returned no history for {symbol}.")
    bars = []
    for timestamp, row in frame.iterrows():
        bars.append(
            DailyBar(
                trading_date=timestamp.date(),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=int(row["Volume"]),
                dividend=float(row.get("Dividends", 0.0)),
                split_factor=float(row.get("Stock Splits", 0.0)) or 1.0,
                source=(
                    "yahoo_bootstrap" if period == "5y" else "yahoo_daily"
                ),
            )
        )
    return bars


def fetch_twse_missing_session(symbol, expected, previous):
    """Append one official bar only when the exchange reference reconciles."""
    if previous.trading_date != latest_twse_session(expected - timedelta(days=1)):
        raise ETFCTAError(f"{symbol}: TWSE fallback requires an adjacent cached session")
    url = (
        "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
        f"?response=json&date={expected:%Y%m%d}&stockNo={symbol}"
    )
    with urlopen(url, timeout=30) as response:
        payload = json.load(response)
    day = f"{expected.year - 1911}/{expected:%m/%d}"
    fields = payload.get("fields", [])
    rows = [dict(zip(fields, row, strict=True)) for row in payload.get("data", [])
            if row and row[0] == day]
    if payload.get("stat") != "OK" or len(rows) != 1:
        raise ETFCTAError(f"{symbol}: TWSE bar unavailable for {expected}")
    row = rows[0]
    try:
        close = Decimal(row["收盤價"].replace(",", ""))
        change = Decimal(row["漲跌價差"].replace(",", ""))
        if abs(close - change - Decimal(str(previous.close))) > Decimal("0.001"):
            raise ValueError("reference price differs from previous close")
        return DailyBar(
            trading_date=expected, open=float(row["開盤價"].replace(",", "")),
            high=float(row["最高價"].replace(",", "")),
            low=float(row["最低價"].replace(",", "")), close=float(close),
            volume=int(row["成交股數"].replace(",", "")), source="twse_stock_day",
        )
    except (ArithmeticError, KeyError, ValueError) as exc:
        raise ETFCTAError(f"{symbol}: TWSE fallback could not verify {expected}: {exc}") from exc


def update(
    data_dir: Path,
    *,
    allow_bootstrap: bool = False,
    fetcher: Callable[..., list[DailyBar]] = fetch_yahoo_daily,
    reference_time: datetime | None = None,
) -> dict:
    """Update both Taiwan symbols with one shared CTA implementation."""

    results: list[dict] = []
    histories = {}
    now = reference_time or datetime.now(UTC)
    expected = latest_completed_market_session("TW", now)
    for symbol, provider_symbol in TAIWAN_CTA_SYMBOLS.items():
        path = data_dir / "history" / f"{symbol}.csv"
        existing = read_history(path)
        if not existing:
            if not allow_bootstrap:
                raise ETFCTAError(
                    f"{symbol} history is missing; rerun with --allow-bootstrap."
                )
            existing = fetcher(provider_symbol, period="5y")
        incoming = fetcher(provider_symbol, period="10d")
        history = merge_and_adjust(
            completed_daily_bars(existing, "TW", now),
            completed_daily_bars(incoming, "TW", now),
        )
        if history[-1].trading_date < expected and fetcher is fetch_yahoo_daily:
            dated = fetcher(
                provider_symbol, start=expected - timedelta(days=14),
                end=expected + timedelta(days=1),
            )
            history = merge_and_adjust(history, completed_daily_bars(dated, "TW", now))
        if history[-1].trading_date < expected and fetcher is fetch_yahoo_daily:
            official = fetch_twse_missing_session(symbol, expected, history[-1])
            history = merge_and_adjust(history, [official])
        if history[-1].trading_date != expected:
            raise ETFCTAError(
                f"{symbol}: expected completed TWSE session {expected}, "
                f"received {history[-1].trading_date}"
            )
        result: CTAResult = calculate_cta(symbol, history)
        histories[path] = history
        item = asdict(result)
        item["provider_symbol"] = provider_symbol
        results.append(item)

    as_of = expected.isoformat()
    for path, history in histories.items():
        write_history(path, history)
    payload = {
        "schema_version": "1.0",
        "metric": "Onecool Taiwan CTA",
        "source": "Yahoo Finance daily history with verified TWSE session fallback",
        "engine": "shared_onecool_cta_engine",
        "data_cutoff": as_of,
        "price_basis": "locally_adjusted_close",
        "method": {
            "daily": ["adjusted_close", "SMA50", "SMA200"],
            "weekly": ["last_trading_day_adjusted_close", "SMA30", "SMA50"],
            "rules": "Onecool CTA v2 weekly crossover priority",
        },
        "results": results,
    }
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "cta_latest.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir", type=Path, default=Path("data/market/taiwan_cta")
    )
    parser.add_argument("--allow-bootstrap", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            update(args.data_dir, allow_bootstrap=args.allow_bootstrap),
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
