# Card valuation boundaries

The weekly card automation and legacy FairValue engine have different purposes.
They must not silently supply each other's values or Fresh classifications.

| Output | Basis | Freshness / evidence |
|---|---|---|
| Weekly Market NAV | Existing automation's PSA-first lookup, qualified comps median | At least 2 eligible sales in 30 days for Fresh; carry-forward at most 90 days |
| Legacy FairValue | Verified eBay evidence median, default latest 10 within 180 days; configurable engine parameters | Existing legacy confidence/freshness rules; not weekly Fresh |

Every legacy snapshot serializes `valuation_basis=LEGACY_EBAY_EVIDENCE_MEDIAN`
and `weekly_market_nav_compatible=false`. Weekly reports must identify their
basis as `WEEKLY_PSA_FIRST_30D` and preserve source date, evidence and carried status.
PSA-first is a lookup sequence; it does not alter the repository's existing
valuation source confidence priority. Read failures or old snapshots do not
refresh evidence dates. Do not replace weekly values with the legacy median.
