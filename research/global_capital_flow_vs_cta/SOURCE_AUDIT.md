# Release-time and historical CTA parity audit — 2026-11-10

## Evidence confirmed (not performance validation)

1. Federal Reserve H.4.1 usually publishes Thursdays 4:30 p.m. **America/New_York**; holidays may delay releases. Historical release calendar: https://www.federalreserve.gov/releases/h41/ .
2. ALFRED provides downloadable historical H.4.1 release dates: https://alfred.stlouisfed.org/release/downloaddates?rid=20 . Release date alone is not a timestamp, nor proof that **each specific WALCL observation** was updated on that date. Match WALCL series vintages and source publication for each value.
3. ALFRED real-time period semantics and revisions: https://fred.stlouisfed.org/docs/api/fred/realtime_period.html .
4. FRED warns release dates do not necessarily indicate FRED/ALFRED site availability: https://fred.stlouisfed.org/docs/api/fred/release_dates.html .
5. The ICE BofA HY OAS series BAMLH0A0HYM2 publicly includes only the past ~3 years starting April 2026; source license/historical archive required for older years: https://fred.stlouisfed.org/series/BAMLH0A0HYM2 .

## Current research implementation and limitations

- `cta_replay.py` calls the **production** `_detect_cross` and `cross_priority_cta` on each historical cutoff. Trading policy remains separate.
- Latest ISO week is withheld until a verified Friday close; holiday-shortened current weeks are **conservatively withheld** until the next ISO week. Not the same as a full point-in-time exchange-calendar model.
- `test_cta_replay.py` includes historical Friday parity checks against production `calculate_cta`; these have been **committed but have not been independently executed in GitHub CI in this research turn**.
- Input historic prices are latest locally adjusted series; point-in-time adjustments, historical broker-fill execution, and FX/currency basis are not yet fully validated.
- ALFRED access requires appropriate archival retrieval; a FRED current-vintage series alone must not populate the historical vintage ledger.
- `pit_guard.py` validates schema, timestamps, and evidence *presence*, but does **not** authenticate the source URL's contents or prove that `available_at_utc` is correct. A second independent source-evidence review is required.
- Never publish CAGR / Sharpe / max drawdown for capital-flow and hybrid strategies without synchronized price, release-vintage and actual execution ledgers, same eligible sample, walk-forward and source provenance.

## Delivery / stop conditions

Ready: separate research code, release audit, source links, fail-closed PIT loader, draft PR.
Blocked: verified WALCL & HY spread release-vintage ledgers across 2010–2026; independent CTA parity-run evidence; non-Friday holiday validation; four-way backtest with costs and out-of-sample.
Do not modify or merge production CTA, dashboard, workflow, or schedules.
