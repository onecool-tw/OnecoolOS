# ETF CTA history

This directory is the reviewable GitHub history for the seven Fund Watchlist
CTA proxy ETFs: AIQ, SMIN, RING, IBB, PICK, RXI, and IXC. SMH and GLD are
confirmation signals only and are not used to calculate Onecool Excess Return.

The first successful workflow run seeds five years of raw OHLC, dividend, and
split observations through the project's existing `yfinance` dependency. Every
subsequent run uses Alpha Vantage free-tier endpoints. Daily runs request
`TIME_SERIES_DAILY` once per ETF (7 calls total). Friday UTC also requests
`DIVIDENDS` and `SPLITS` for every ETF (14 additional weekly calls), merges the
complete action history by date, and recalculates every adjusted close and CTA.
If a new raw close moves more than 35% in one session, that symbol receives an
immediate two-call action refresh as split protection.

CTA uses one cutoff date per symbol and one implementation:

- Daily adjusted close: SMA50 and SMA200.
- Weekly last-trading-day adjusted close: SMA30 and SMA50.
- `BUY`: price > daily 50 > daily 200 and price > weekly 30 > weekly 50.
- `SELL`: price < daily 50 < daily 200 and price < weekly 30 < weekly 50.
- `WATCH`: a long-term average is broken, or both slopes are bearish.
- `HOLD`: all remaining mixed but non-SELL states.

Provider failures are fatal. There is no silent runtime fallback.
