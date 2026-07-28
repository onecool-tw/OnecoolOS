# Taiwan CTA history

This directory is the shared, reviewable CTA source for:

- `0050` — market-level Taiwan equity exposure.
- `2330` — TSMC stock-level action.

The daily workflow runs after the Taiwan close and obtains `0050.TW` and
`2330.TW` from Yahoo Finance. A missing history is bootstrapped once with five
years of data; later runs merge the newest daily observations into the
committed CSV history.

Both symbols use the existing `shared_onecool_cta_engine`:

- Daily adjusted close: SMA50 and SMA200.
- Weekly last-trading-day adjusted close: SMA30 and SMA50.
- Weekly crossover has priority; daily crossover confirms or softens it.

`cta_latest.json` is written only when both symbols have the same complete
trading-date cutoff. Mixed dates, insufficient history, or provider failure
fail the workflow instead of publishing a partial or guessed signal.
