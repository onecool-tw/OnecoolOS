# Taiwan family read-only snapshot

Public HTTPS endpoint (after Pages is enabled and deployment succeeds):
https://onecool-tw.github.io/OnecoolOS/taiwan_stock_family_latest.json

Consumers read this GitHub Pages endpoint. The canonical repository artifact
remains `data/public/taiwan_stock_family_latest.json` on main.
Consumers must not run CTA,
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

## Static publication

`publish-taiwan-family-pages.yml` copies only this JSON into the Pages artifact,
without invoking the exporter or any calculation. It runs after the three
existing writer workflows succeed, including their bot-generated commits, and
on relevant main pushes or manual dispatch. No additional data store is created.
The deploy step uses only contents-read, pages-write and OIDC permissions.
After deployment, an unauthenticated HTTPS read must match the checked-out
snapshot byte for byte (including all dates, statuses, CTA, ranks and scores).
The deployment summary records the source commit. A failed publication leaves
the previous public version in place; consumers must check source dates/status.

One-time repository setting: Settings > Pages > Build and deployment > Source
must be `GitHub Actions`. The deployment does not create administrative tokens
or change repository settings. Then run `Publish Taiwan Family Snapshot Pages`
from Actions (or rerun a failed initial deployment).

Local or external publication check:
`python scripts/verify_taiwan_family_pages.py <staged-file-or-https-url>`
