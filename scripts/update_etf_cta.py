"""Update Fund Watchlist ETF history and CTA snapshots."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from onecool_os.market.etf_cta import (
    ACTION_REFRESH_GROUPS,
    MARKET_SYMBOLS,
    AlphaVantageClient,
    DailyBar,
    ETFCTAError,
    calculate_cta,
    apply_corporate_actions,
    has_new_price_anomaly,
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


def update(
    data_dir: Path,
    api_key: str,
    allow_bootstrap: bool,
    refresh_actions: bool = False,
    refresh_action_symbols: set[str] | None = None,
) -> dict:
    """Update all symbols atomically enough for a reviewable Git commit."""

    client = AlphaVantageClient(api_key)
    results = []
    action_refreshes = []
    for symbol in MARKET_SYMBOLS:
        path = data_dir / "history" / f"{symbol}.csv"
        existing = read_history(path)
        if not existing:
            if not allow_bootstrap:
                raise ETFCTAError(
                    f"{symbol} history is missing; rerun with --allow-bootstrap."
                )
            existing = bootstrap_yahoo(symbol)
        incoming = client.fetch_daily(symbol)
        anomaly = has_new_price_anomaly(existing, incoming)
        should_refresh_actions = (
            refresh_actions
            or symbol in (refresh_action_symbols or set())
            or anomaly
        )
        combined = merge_and_adjust(existing, incoming)
        if should_refresh_actions:
            combined = apply_corporate_actions(
                combined,
                client.fetch_actions(symbol),
                authoritative=True,
            )
            action_refreshes.append(
                {"symbol": symbol, "reason": "anomaly" if anomaly else "weekly"}
            )
        history = merge_and_adjust([], combined)
        write_history(path, history)
        results.append(asdict(calculate_cta(symbol, history)))

    payload = {
        "schema_version": "1.1",
        "method": {
            "daily": ["adjusted_close", "SMA50", "SMA200"],
            "weekly": ["last_trading_day_adjusted_close", "SMA30", "SMA50"],
            "rules": "Onecool CTA v1 fixed rule",
            "cross_detection": {
                "daily": "SMA50 crosses SMA200",
                "weekly": "SMA30 crosses SMA50",
                "delta_rule": "cross_status is non-NONE only on the crossing period",
            },
        },
        "action_refreshes": action_refreshes,
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
    parser.add_argument(
        "--refresh-actions",
        action="store_true",
        help="Refresh full dividend/split history and recalculate all closes.",
    )
    parser.add_argument(
        "--refresh-actions-group",
        choices=tuple(ACTION_REFRESH_GROUPS),
        help="Refresh one API-safe subset of dividend/split histories.",
    )
    args = parser.parse_args()
    payload = update(
        args.data_dir,
        os.environ.get("ALPHA_VANTAGE_API_KEY", ""),
        args.allow_bootstrap,
        args.refresh_actions,
        set(ACTION_REFRESH_GROUPS.get(args.refresh_actions_group, ())),
    )
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
