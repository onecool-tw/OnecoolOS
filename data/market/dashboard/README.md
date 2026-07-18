# Onecool Market Dashboard

This directory is the GitHub-backed market CTA cache for Onecool OS.

- `dashboard_latest.json`: most recent complete successful update.
- `history/*.csv`: locally adjusted price history by display symbol.
- `snapshots/*.json`: dated dashboard snapshots for audit and fallback.

Only `.github/workflows/update-market-dashboard.yml` may call Alpha Vantage for
these seven symbols. Consumers must use `load_latest_dashboard()` and keep using
the most recent committed cache when a scheduled update fails.

The Monday Fund Intelligence consumer uses
`load_fund_intelligence_context()`. That function combines the latest fund Alpha
cache with this dashboard and performs no market-provider query.

Provider symbols are `SPY`, `QQQ`, `DIA`, `SOXX`, `NVDA`, `0050.TW`, and
`2330.TW`. Display symbols remain `0050` and `2330`.
