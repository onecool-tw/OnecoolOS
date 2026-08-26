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

CTA is maintained in a separate background cache under `cta/`.  All 200
liquidity-universe members are updated so a newly selected candidate already
has a technical state, but CTA never changes the fundamental score, rank, or
Top 5 membership.  The daily context attaches CTA only to the published Top 5.

- Weekly 30/50 is the primary trend authority.
- Daily 50/200 is auxiliary confirmation and may only restrict adding.
- Adjusted history and completed trading weeks are required.
- Per-symbol failures become `UNKNOWN`, or `STALE_LAST_KNOWN` when a prior
  valid observation exists; neither state is actionable.
- 0050 and 2330 market CTA remain owned by the separate Taiwan CTA module.
