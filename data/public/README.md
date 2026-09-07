# Taiwan family read-only snapshot

Read `taiwan_stock_family_latest.json` from main. Consumers must not run CTA,
market-pressure or Top 5 calculations. `market_pressure` is copied unchanged
from the formal daily context; only the existing Work writer owns that result.
`market_cta` comes from Market Dashboard; `top5` keeps the screen order and
scores, with individual CTA joined from its formal cache and checked against
context. No portfolio, credentials, holdings or unrelated Dashboard fields are exported.

Always display each source's actual date/status. Source timestamps do not mean
all markets share a cutoff. A fresh export does not make old data current.
Stale/missing data grants no new exposure. A BUY is not a buy order: all formal
market, individual and data gates still apply. Consumers may explain these
fields but must not override them or write to the source files.

Export: `python scripts/export_taiwan_family_snapshot.py`

Verify against current source bytes: `python scripts/export_taiwan_family_snapshot.py --check`

The exporter uses no network or signal engine. It rejects inconsistent joins
without replacing the last valid snapshot. Source SHA-256 digests permit
provenance checks. Repeated exports with identical sources are byte-identical.
Screen, Taiwan CTA and pressure persistence workflows export and validate before
committing. They share a writer lock and read latest main after acquiring it.
