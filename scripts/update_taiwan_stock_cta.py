"""Update background CTA for every stock in the Taiwan candidate universe."""

from __future__ import annotations

import argparse
import json
import time
from math import isfinite
from pathlib import Path

from onecool_os.market.etf_cta import DailyBar, ETFCTAError
from onecool_os.market.taiwan_stock_cta import update_candidate_cta


def fetch_yahoo_batch(
    symbols: list[str], period: str, *, attempts: int = 3
) -> dict[str, list[DailyBar]]:
    """Fetch a bounded ticker batch and retain successful per-symbol results."""

    if not symbols:
        return {}
    import yfinance as yf

    collected: dict[str, list[DailyBar]] = {}
    pending = list(symbols)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            frame = yf.download(
                tickers=pending,
                period=period,
                auto_adjust=False,
                actions=True,
                group_by="ticker",
                threads=True,
                progress=False,
                timeout=30,
            )
            for symbol in list(pending):
                bars = _parse_symbol_frame(frame, symbol, len(pending), period)
                if bars:
                    collected[symbol] = bars
                    pending.remove(symbol)
        except Exception as exc:  # noqa: BLE001 - retry provider boundary.
            last_error = exc
        if not pending:
            return collected
        if attempt + 1 < attempts:
            time.sleep(2**attempt)
    if not collected and last_error:
        raise ETFCTAError(
            f"Yahoo batch failed for {len(symbols)} symbols: {last_error}"
        ) from last_error
    return collected


def _parse_symbol_frame(frame, symbol: str, request_size: int, period: str):
    if frame is None or frame.empty:
        return []
    columns = frame.columns
    if getattr(columns, "nlevels", 1) > 1:
        if symbol in columns.get_level_values(0):
            stock = frame[symbol]
        elif symbol in columns.get_level_values(1):
            stock = frame.xs(symbol, axis=1, level=1)
        else:
            return []
    elif request_size == 1:
        stock = frame
    else:
        return []

    bars = []
    for timestamp, row in stock.iterrows():
        values = [row.get(name) for name in ("Open", "High", "Low", "Close")]
        if any(value is None or not isfinite(float(value)) for value in values):
            continue
        dividend = _finite_or_zero(row.get("Dividends", 0.0))
        split = _finite_or_zero(row.get("Stock Splits", 0.0))
        volume = _finite_or_zero(row.get("Volume", 0.0))
        bars.append(DailyBar(
            trading_date=timestamp.date(),
            open=float(values[0]),
            high=float(values[1]),
            low=float(values[2]),
            close=float(values[3]),
            volume=int(volume),
            dividend=dividend,
            split_factor=split or 1.0,
            source="yahoo_bootstrap" if period == "5y" else "yahoo_daily",
        ))
    return bars


def _finite_or_zero(value) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return parsed if isfinite(parsed) else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--screen",
        type=Path,
        default=Path("data/market/taiwan_stock_intelligence/screen_latest.json"),
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/market/taiwan_stock_intelligence/cta"),
    )
    parser.add_argument("--batch-size", type=int, default=40)
    args = parser.parse_args()
    payload = update_candidate_cta(
        args.screen,
        args.data_dir,
        fetcher=fetch_yahoo_batch,
        batch_size=args.batch_size,
    )
    print(json.dumps({
        "requested_count": payload["requested_count"],
        "coverage": payload["coverage"],
        "screen_as_of": payload["screen_as_of"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
