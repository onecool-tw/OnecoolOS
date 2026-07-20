# Fund NAV and Onecool Relative Alpha

This directory contains only public share-class NAV history for the seven Fund
Watchlist funds. It never stores units, cost, market value, profit/loss, cash
flows, account information, or portfolio allocation.

Fund NAVs are read weekly from the public `NavHIS` endpoint used by Anue Fund's
own detail pages. The source is identified as `anuefund_public`; it is a
platform source and is not represented as an official fund-company source.

`alpha_latest.json` defines Onecool Excess Return as:

`fund period NAV return - CTA proxy ETF period total return`

The latest payload includes 3-month, 6-month, and one-year measurements. The
existing flat one-year fields remain for backward compatibility; the additive
`period_returns` object is the source for multi-period reporting.

This is a raw return difference, not risk-adjusted alpha. Official Alpha is
reported only when the fund company publishes it for the applicable fund/share
class and is not calculated by this workflow.

Both legs must use identical start and end dates. For every horizon, the start
date is the latest common valuation date on or before the target anniversary
and must be within 10 calendar days. Missing or misaligned data returns
`unknown`, never a guessed value. Three completed monthly snapshots are
retained in the JSON result for the Onecool three-month decision rule.
