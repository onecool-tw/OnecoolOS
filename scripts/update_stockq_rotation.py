"""Refresh the StockQ rotation radar cache used by the fund weekly report."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from onecool_os.market.stockq_rotation import (
    DatedValue,
    STOCKQ_MARKET_URL,
    build_rotation_radar,
    calculate_twd_returns,
    fetch_stockq_html,
    screen_markets,
)
from onecool_os.market.history_bootstrap import YahooHistoryBootstrapper


TWD_SERIES = {
    "泰國": ("^SET.BK", "THBTWD=X"),
    "新加坡": ("^STI", "SGDTWD=X"),
    "日本": ("^N225", "JPYTWD=X"),
    "韓國": ("^KS11", "KRWTWD=X"),
    "香港": ("^HSI", "HKDTWD=X"),
}


def _twd_returns_for_pass_markets(
    market_html: str,
    as_of: str | None,
    bootstrapper: YahooHistoryBootstrapper,
) -> dict[str, dict]:
    results = {}
    cutoff = (
        datetime.fromisoformat(as_of).date()
        if as_of
        else datetime.now(timezone.utc).date()
    )
    for market in screen_markets(market_html):
        if market.stage1 != "PASS" or market.market not in TWD_SERIES:
            continue
        market_symbol, fx_symbol = TWD_SERIES[market.market]
        try:
            local = bootstrapper.fetch_adjusted_daily(market_symbol)
            fx = bootstrapper.fetch_adjusted_daily(fx_symbol)
        except Exception as exc:  # Provider failure must not erase the radar.
            results[market.market] = {
                period: {
                    "start_date": None,
                    "end_date": None,
                    "local_return_pct": None,
                    "fx_return_pct": None,
                    "twd_return_pct": None,
                    "status": "UNKNOWN",
                    "reason": f"Same-date FX update failed: {type(exc).__name__}",
                }
                for period in ("1w", "1m")
            }
            continue
        results[market.market] = calculate_twd_returns(
            [
                DatedValue(item.trading_date, item.adjusted_close or item.close)
                for item in local
            ],
            [
                DatedValue(item.trading_date, item.adjusted_close or item.close)
                for item in fx
            ],
            as_of=cutoff,
        )
    return results


def update(
    root: Path, *, bootstrapper: YahooHistoryBootstrapper | None = None
) -> dict:
    market_html = fetch_stockq_html(STOCKQ_MARKET_URL)
    match = re.search(
        r"<b>一日</b>.*?([0-9]{2}/[0-9]{2})",
        market_html,
        flags=re.DOTALL,
    )
    as_of = None
    if match:
        month, day = match.group(1).split("/")
        as_of = f"{datetime.now(timezone.utc).year}-{month}-{day}"
    twd_returns = _twd_returns_for_pass_markets(
        market_html, as_of, bootstrapper or YahooHistoryBootstrapper()
    )
    payload = build_rotation_radar(
        market_html,
        fetch_stockq_html,
        as_of=as_of,
        twd_returns=twd_returns,
    )
    destination = root / "data" / "market" / "stockq_rotation" / "rotation_latest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False))
    return payload


if __name__ == "__main__":
    update(Path("."))
