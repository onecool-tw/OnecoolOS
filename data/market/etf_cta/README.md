# ETF CTA history

This directory is the reviewable GitHub history for the seven Fund Watchlist
CTA proxy ETFs: AIQ, SMIN, RING, IBB, PICK, RXI, and IXC. GLD and WTI are
auxiliary confirmation signals only and are not used to calculate Onecool
Excess Return. GLD confirms the gold-metal trend behind RING; WTI confirms the
oil-price trend behind IXC. They remain hidden in normal reports unless they
diverge, form a new crossover, or the formal fund/benchmark signal weakens.

The first successful workflow run seeds five years of raw OHLC, dividend, and
split observations through the project's existing `yfinance` dependency. Every
subsequent run uses Alpha Vantage free-tier endpoints. Daily runs request
`TIME_SERIES_DAILY` once per ETF plus one WTI daily-series request. Corporate
actions are split into two API-safe groups: five ETFs receive dividend and
split refreshes on Thursday UTC (10 extra calls), and three receive them on
Friday UTC (6 extra calls). The workflow merges complete action history by
date and recalculates every adjusted close and CTA.
If a new raw close moves more than 35% in one session, that symbol receives an
immediate two-call action refresh as split protection.

CTA uses one cutoff date per symbol and one shared implementation.  Crossovers
have priority over static alignment, and weekly signals have priority over
daily signals:

- Daily adjusted close: SMA50 and SMA200.
- Weekly last-trading-day adjusted close: SMA30 and SMA50.
- Weekly `GOLDEN` cross: `BUY`; weekly `DEATH` cross: `SELL`.
- A daily cross can confirm a weekly signal or soften it by one level, but it
  cannot reverse the weekly signal by itself.
- Crossover phase is `NEW`, `CONFIRMED`, `ACTIVE`, or `AGING`. Weekly phases
  use 0, 1-4, 5-52, and 53+ weekly periods; daily phases use 0, 1-5, 6-60,
  and 61+ daily observations.
- An aging weekly golden trend without renewed daily strength is `HOLD`.
- An active weekly death trend remains `SELL`; an opposing daily golden cross
  softens it to `WATCH` pending weekly confirmation.

`alignment` remains an explanatory field. `cross_status` is non-`NONE` only
on the actual crossing period, so a persistent alignment is never mislabeled
as a new crossover.

Provider failures are fatal. There is no silent runtime fallback.
