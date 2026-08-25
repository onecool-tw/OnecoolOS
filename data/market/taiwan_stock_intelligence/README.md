# Taiwan Stock Intelligence Screen

`screen_latest.json` is the only formal Taiwan Top 5 screening artifact.

- Universe: up to 200 four-digit listed common stocks ranked by official daily
  trade value.
- Sources: TWSE daily prices, official valuation ratios, monthly revenue, and
  quarterly income statements.
- Formal candidates: score at least 80.
- Watchlist: score from 75 through 79.99.
- Portfolio hygiene: at most two names from one industry and at most five formal
  names in the published table.
- Data quality: one price/valuation cutoff, one revenue month, one financial
  quarter, duplicate checks, and no estimated-value filling.

CTA is intentionally out of scope.  The screen must never calculate or rewrite
0050 or 2330 CTA.  User-requested ticker reviews remain separate unless that
symbol appears in `top5` or `watchlist`.
