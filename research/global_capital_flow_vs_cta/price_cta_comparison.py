"""Research-only comparison of rolling vs fully confirmed weekly CTA.

Run from repository root:
python -m research.global_capital_flow_vs_cta.price_cta_comparison

No macro flow factors are imputed here. Results are exploratory and are NOT
a point-in-time corporate-actions or exchange-calendar certified backtest.
"""
from __future__ import annotations

import json
from datetime import datetime
from math import isfinite
from pathlib import Path

from onecool_os.market.etf_cta import (
    InsufficientCTAHistory, calculate_cta, read_history,
)
from .cta_replay import replay_signal

SYMBOLS = ("QQQ", "SOXX", "0050")
HISTORY_ROOT = Path("data/market/dashboard/history")


def adjusted_open(bar):
    """Research approximation; historical adjustment vintage not proven."""
    if bar.close <= 0 or bar.open <= 0 or bar.adjusted_close is None:
        raise ValueError("Invalid price or adjustment")
    value = bar.open * bar.adjusted_close / bar.close
    if not isfinite(value) or value <= 0:
        raise ValueError("Invalid adjusted open proxy")
    return value


def _summary(nav, first, last):
    years = (last - first).days / 365.25
    if years <= 0:
        raise ValueError("Invalid strategy duration")
    peak = nav[0]
    worst = 0.0
    for value in nav:
        peak = max(peak, value)
        worst = min(worst, value / peak - 1)
    return {
        "total_pct": round((nav[-1] - 1) * 100, 3),
        "cagr_pct": round((nav[-1] ** (1 / years) - 1) * 100, 3),
        "max_dd_pct": round(worst * 100, 3),
    }


def run_symbol(symbol, bars, *, one_way_bps=0):
    """Frozen main CTA at each close, execute the decision at next open.

    Return over each following adjusted-open to adjusted-open interval uses
    ONLY the position entered at the immediately preceding open. WATCH/HOLD
    retain the existing stance; BUY enters, SELL exits; initially flat.
    No comparison is reported before BOTH arms have sufficient history.
    """
    if not isfinite(one_way_bps) or not 0 <= one_way_bps < 10000:
        raise ValueError("Invalid transaction cost")
    bars = sorted(bars, key=lambda x: x.trading_date)
    if len(set(b.trading_date for b in bars)) != len(bars):
        raise ValueError("Duplicate price dates")
    for bar in bars:
        adjusted_open(bar)
    decisions = []
    for i in range(len(bars) - 2):
        prefix = bars[: i + 1]
        try:
            rolling = calculate_cta(symbol, prefix).cta
            confirmed = replay_signal(symbol, prefix, bars[i].trading_date)["cta"]
        except InsufficientCTAHistory:
            continue
        decisions.append((i, rolling, confirmed))
    if not decisions:
        raise ValueError("No common eligible sessions")
    names = ("buy_hold", "rolling", "confirmed")
    nav = {x: [1.0] for x in names}
    stance = {"rolling": False, "confirmed": False}
    actions = {"rolling": [], "confirmed": []}
    exposure = {"rolling": 0, "confirmed": 0}
    mismatches = 0
    for i, rolling, confirmed in decisions:
        if rolling != confirmed:
            mismatches += 1
        grow = adjusted_open(bars[i + 2]) / adjusted_open(bars[i + 1])
        nav["buy_hold"].append(nav["buy_hold"][-1] * grow)
        for arm, action in (("rolling", rolling), ("confirmed", confirmed)):
            next_stance = (True if action == "BUY" else
                           False if action == "SELL" else stance[arm])
            changed = next_stance != stance[arm]
            if changed:
                actions[arm].append({
                    "signal_date": bars[i].trading_date.isoformat(),
                    "execution_date": bars[i + 1].trading_date.isoformat(),
                    "action": "BUY" if next_stance else "SELL",
                })
            stance[arm] = next_stance
            exposure[arm] += int(next_stance)
            nav[arm].append(nav[arm][-1] *
                            (1 - one_way_bps / 10000 if changed else 1) *
                            (grow if next_stance else 1))
    first_exec = bars[decisions[0][0] + 1].trading_date
    last_valued = bars[decisions[-1][0] + 2].trading_date
    return {
        "symbol": symbol,
        "status": "EXPLORATORY_PRICE_ONLY_NOT_PIT_CERTIFIED",
        "first_execution": first_exec.isoformat(),
        "last_valuation": last_valued.isoformat(),
        "sessions": len(decisions),
        "signal_label_differences": mismatches,
        "one_way_bps": one_way_bps,
        "strategies": {x: _summary(nav[x], first_exec, last_valued)
                       for x in names},
        "trade_events": actions,
        "exposure_pct": {x: round(exposure[x] / len(decisions) * 100, 2)
                         for x in exposure},
    }


def main():
    outputs = []
    for symbol in SYMBOLS:
        bars = read_history(HISTORY_ROOT / (symbol + ".csv"))
        for fee in (0, 10):
            outputs.append(run_symbol(symbol, bars, one_way_bps=fee))
    print(json.dumps({"research_only": True, "method": "next-open",
                      "outcomes": outputs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
