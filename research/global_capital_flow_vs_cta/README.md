# Global Capital Flow vs CTA — research recovery (2026-11-10)

Status: **RESEARCH ONLY — validation blocked; no four-strategy results claimed.**

## Recovered verified assets

- Frozen shared CTA source: `onecool_os/market/etf_cta.py`, `calculate_cta`, `cross_priority_cta`.
- US market updater: `scripts/update_market_dashboard.py`.
- Taiwan CTA: `scripts/update_taiwan_cta.py`.
- Adj-close source histories: `data/market/dashboard/history/{QQQ,SOXX,0050}.csv`.
- Existing descriptive rates-versus-assets analysis: `onecool_os/market/rate_asset_backtest.py`.
- Macro regime `onecool_os/market/macro_regime.py` reuses CTA outputs: **not an independent flow factor**.

Price data begin 2021-08-02 (QQQ), 2021-11-10 (SOXX), and 2021-07-30 (0050). The short series cannot verify 2010-2026 performance.

## Why the four-strategy study remains blocked

A current/revised FRED extract is **not** sufficient for a look-ahead-free historical backtest. Required primary feed is a time-stamped historic vintage ledger with fields:
`factor,observation_date,available_at_utc,value,vintage_id`.

First-stage independent proxies:
- WALCL Fed assets (13-week change), release time must be historical and evidenced.
- BAMLH0A0HYM2 HY spread (20-observation change), historical first-availability required.

The above are Fed liquidity and credit risk **proxies**, *not* actual observed global capital flows. The FRED ICE HY spread has a recently shortened published history (about three years); older compliant source necessary for longer samples.

Never assume observation date = availability date. A conservative artificial lag is useful only for a sensitivity scenario, **not proof of point-in-time availability**.

## Precommitted exploratory comparison

Four strategy variants, **same common eligible sessions per asset**:
1. Buy/hold.
2. Original weekly-first CTA: preserve BUY/SELL/WATCH/HOLD and cross-age semantics.
3. Fed balance-sheet expansion **AND** no HY spread widening proxy (fixed research parameters).
4. CTA entry/exit policy gated by identical macro proxy.

Signals evaluated only after data are observable, execution at following session open; exchange calendars, time zones, fees, slippage, dividend/split adjustments and vendor revisions tested explicitly. 0050 may never see late US releases early. Require 252 common eligible sessions, and independent parity validation of CTA signals and completed weekly bars. Report CAGR, MDD, drawdown duration, Sharpe, turnover, exposure, lead/lag and out-of-sample evidence or refuse to print performance.

## Work completed in isolated sandbox

Research-only Python prototype and 5 passing local unit tests: latest-vintage visibility, reject pre-observation availability, reject missing vintage, reject insufficient factor history, reject common sample under 252 sessions. Prototype intentionally not committed to main. Independent production CTA signal-parity and market-data evidence are **not yet validated**. Any approximate CTA returns previously discussed are preliminary and not official validation.

## Safety boundaries

Do not merge this research note as authorization to alter trading signals. No changes to production CTA, Dashboard, workflows, caches, or schedules. Only open a draft PR against main; leave unmerged until PIT dataset, source licenses, comprehensive historical parity tests and out-of-sample results are verified.

References:
- https://fred.stlouisfed.org/series/WALCL
- https://fred.stlouisfed.org/series/BAMLH0A0HYM2
- https://alfred.stlouisfed.org/series?seid=BAMLH0A0HYM2
