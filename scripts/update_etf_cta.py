"""Update Fund Watchlist ETF history and CTA snapshots."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from onecool_os.market.etf_cta import (
    WATCHLIST_SYMBOLS,
    AlphaVantageClient,
    DailyBar,
    ETFCTAError,
    calculate_cta,
    merge_and_adjust,
    read_history,
    write_history,
)


def bootstrap_yahoo(symbol: str) -> list[DailyBar]:
    """Create a one-time five-year raw seed using the existing dependency."""

    import yfinance as yf

    frame = yf.Ticker(symbol).history(
        period="5y", auto_adjust=False, actions=True
    )
    if frame.empty:
        raise ETFCTAError(f"Yahoo bootstrap returned no history for {symbol}.")
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
                source="yahoo_bootstrap",
            )
        )
    return bars


def update(data_dir: Path, api_key: str, allow_bootstrap: bool) -> dict:
    """Update all symbols atomically enough for a reviewable Git commit."""

    client = AlphaVantageClient(api_key)
    results = []
    for symbol in WATCHLIST_SYMBOLS:
        path = data_dir / "history" / f"{symbol}.csv"
        existing = read_history(path)
        if not existing:
            if not allow_bootstrap:
                raise ETFCTAError(
                    f"{symbol} history is missing; rerun with --allow-bootstrap."
                )
            existing = bootstrap_yahoo(symbol)
        incoming = client.fetch_symbol(symbol)
        history = merge_and_adjust(existing, incoming)
        write_history(path, history)
        results.append(asdict(calculate_cta(symbol, history)))

    payload = {
        "schema_version": "1.0",
        "method": {
            "daily": ["adjusted_close", "SMA50", "SMA200"],
            "weekly": ["last_trading_day_adjusted_close", "SMA30", "SMA50"],
            "rules": "Onecool CTA v1 fixed rule",
        },
        "results": results,
    }
    data_dir.mkdir(parents=True, exist_ok=True)
    output = data_dir / "cta_latest.json"
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir", type=Path, default=Path("data/market/etf_cta")
    )
    parser.add_argument("--allow-bootstrap", action="store_true")
    args = parser.parse_args()
    payload = update(
        args.data_dir,
        os.environ.get("ALPHA_VANTAGE_API_KEY", ""),
        args.allow_bootstrap,
    )
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
