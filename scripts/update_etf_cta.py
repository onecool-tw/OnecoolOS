"""Update Fund Watchlist ETF history and CTA snapshots."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from onecool_os.market.etf_cta import (
    ACTION_REFRESH_GROUPS,
    COMMODITY_CONFIRMATION_SYMBOLS,
    EQUITY_MARKET_SYMBOLS,
    RETIRED_SYMBOLS,
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


def fetch_yahoo_daily(symbol: str, *, period: str = "10d") -> list[DailyBar]:
    """Fetch raw Yahoo daily bars without consuming Alpha Vantage quota."""

    import yfinance as yf

    frame = yf.Ticker(symbol).history(
        period=period, auto_adjust=False, actions=True
    )
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
                source=("yahoo_bootstrap" if period == "5y" else "yahoo_daily"),
            )
        )
    return bars


def bootstrap_yahoo(symbol: str) -> list[DailyBar]:
    """Create a one-time five-year raw seed using the existing dependency."""

    return fetch_yahoo_daily(symbol, period="5y")


def _is_alpha_vantage_rate_limit(error: ETFCTAError) -> bool:
    message = str(error).lower()
    return "rate limit" in message or "requests per day" in message


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
    data_status = []
    for symbol in RETIRED_SYMBOLS:
        (data_dir / "history" / f"{symbol}.csv").unlink(missing_ok=True)
    for symbol in EQUITY_MARKET_SYMBOLS:
        path = data_dir / "history" / f"{symbol}.csv"
        existing = read_history(path)
        if not existing:
            if not allow_bootstrap:
                raise ETFCTAError(
                    f"{symbol} history is missing; rerun with --allow-bootstrap."
                )
            existing = bootstrap_yahoo(symbol)
        incoming = fetch_yahoo_daily(symbol)
        anomaly = has_new_price_anomaly(existing, incoming)
        should_refresh_actions = (
            refresh_actions
            or symbol in (refresh_action_symbols or set())
            or anomaly
        )
        combined = merge_and_adjust(existing, incoming)
        if should_refresh_actions:
            try:
                combined = apply_corporate_actions(
                    combined,
                    client.fetch_actions(symbol),
                    authoritative=True,
                )
                action_refreshes.append(
                    {
                        "symbol": symbol,
                        "reason": "anomaly" if anomaly else "weekly",
                    }
                )
            except ETFCTAError as error:
                if not _is_alpha_vantage_rate_limit(error):
                    raise
                data_status.append(
                    {
                        "symbol": symbol,
                        "dataset": "corporate_actions",
                        "status": "STALE",
                        "reason": "alpha_vantage_daily_quota",
                    }
                )
        history = merge_and_adjust([], combined)
        write_history(path, history)
        results.append(asdict(calculate_cta(symbol, history)))
        data_status.append(
            {
                "symbol": symbol,
                "dataset": "daily_price",
                "status": "CURRENT",
                "source": "yahoo",
                "as_of": history[-1].trading_date.isoformat(),
            }
        )

    for symbol in COMMODITY_CONFIRMATION_SYMBOLS:
        if symbol != "WTI":
            raise ETFCTAError(f"Unsupported commodity confirmation: {symbol}.")
        path = data_dir / "history" / f"{symbol}.csv"
        existing = read_history(path)
        try:
            history = merge_and_adjust(existing, client.fetch_wti_daily())
            wti_status = "CURRENT"
            wti_reason = None
            wti_source = "alpha_vantage_wti_eia_fred"
        except ETFCTAError as error:
            try:
                incoming = fetch_yahoo_daily("CL=F")
                history = merge_and_adjust(existing, incoming)
                wti_status = "CURRENT"
                wti_reason = f"primary_failed:{type(error).__name__}"
                wti_source = "yahoo_cl_f_fallback"
            except Exception as fallback_error:
                if not existing:
                    raise ETFCTAError(
                        "WTI primary and CL=F fallback both failed."
                    ) from fallback_error
                history = existing
                wti_status = "STALE"
                wti_reason = "primary_and_fallback_failed"
                wti_source = "last_known_valid"
        write_history(path, history)
        results.append(asdict(calculate_cta(symbol, history)))
        status = {
            "symbol": symbol,
            "dataset": "daily_price",
            "status": wti_status,
            "source": wti_source,
            "as_of": history[-1].trading_date.isoformat(),
        }
        if wti_reason:
            status["reason"] = wti_reason
        data_status.append(status)

    payload = {
        "schema_version": "1.3",
        "method": {
            "daily": ["adjusted_close", "SMA50", "SMA200"],
            "weekly": ["last_trading_day_adjusted_close", "SMA30", "SMA50"],
            "rules": "Onecool CTA v2 weekly crossover priority",
            "cross_detection": {
                "daily": "SMA50 crosses SMA200",
                "weekly": "SMA30 crosses SMA50",
                "delta_rule": "cross_status is non-NONE only on the crossing period",
                "priority": "weekly crossover > daily crossover > alignment",
                "phase": "NEW, CONFIRMED, ACTIVE, AGING",
            },
        },
        "action_refreshes": action_refreshes,
        "data_status": data_status,
        "auxiliary_confirmation_policy": {
            "GLD": "gold spot proxy; context only for RING/fund divergence",
            "WTI": "oil spot series; context only for IXC/fund divergence",
            "visibility": (
                "hidden unless divergent, newly crossed, or formal signal weakens"
            ),
            "decision_use": "never independently triggers or reverses DCA action",
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
