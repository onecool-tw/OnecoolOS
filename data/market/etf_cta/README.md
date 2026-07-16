# ETF CTA history

This directory is the reviewable GitHub history for the seven Fund Watchlist
benchmark ETFs: QQQ, SMIN, GLD, IBB, PICK, VCR, and XLE.

The first successful workflow run seeds five years of raw OHLC, dividend, and
split observations through the project's existing `yfinance` dependency. Every
subsequent run uses only Alpha Vantage free-tier endpoints:
`TIME_SERIES_DAILY`, `DIVIDENDS`, and `SPLITS`. The updater merges by market
date and recalculates the complete adjusted-close history locally.

CTA uses one cutoff date per symbol and one implementation:

- Daily adjusted close: SMA50 and SMA200.
- Weekly last-trading-day adjusted close: SMA30 and SMA50.
- `BUY`: price > daily 50 > daily 200 and price > weekly 30 > weekly 50.
- `SELL`: price < daily 50 < daily 200 and price < weekly 30 < weekly 50.
- `WATCH`: a long-term average is broken, or both slopes are bearish.
- `HOLD`: all remaining mixed but non-SELL states.

Provider failures are fatal. There is no silent runtime fallback.
