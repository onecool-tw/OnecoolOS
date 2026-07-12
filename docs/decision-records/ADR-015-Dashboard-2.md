# ADR-015 Dashboard 2.0

Status: Accepted

## Context

Onecool OS now has RuntimeSession, Research Queue, verified evidence, Onecool
Fair Value, canonical ValuationRecords, and live Portfolio NAV snapshots. The
next step is a production-ready portfolio dashboard snapshot for Onecool
Collection Portfolio.

Dashboard must remain presentation-only. It consumes runtime outputs and does
not own calculations.

## Decision

Create Dashboard 2.0 as a display snapshot layer:

```text
RuntimeSession
↓
Research Queue / Fair Value / ValuationRecord / Portfolio NAV
↓
DashboardSnapshot
```

RuntimeSession exposes `dashboard_snapshot()`, which delegates to
`DashboardSnapshotBuilder`. The builder packages existing runtime outputs into
display-ready sections. It does not call providers, call AI, scrape websites,
mutate runtime, mutate Asset Master, calculate Fair Value, calculate NAV, or
create recommendations.

## Dashboard Sections

Dashboard 2.0 includes:

- Portfolio Summary
- Portfolio NAV
- Research Queue
- Evidence
- Valuation
- Coverage
- Top Holdings
- Missing Valuation
- Latest Updates
- Warnings

## Source Boundaries

All displayed values come from existing runtime outputs:

- RuntimeSession assets and timestamps
- Research Queue snapshot
- eBay Sold Evidence helpers
- Onecool Fair Value snapshots
- Fair Value to ValuationRecord integration
- Portfolio NAV snapshots
- Collection Sync differences

Dashboard does not merge research coverage, evidence coverage, valuation
coverage, and NAV coverage into one metric. Each remains independently
visible.

## Portfolio Value Disclosure

If NAV coverage is incomplete, Dashboard displays:

> Portfolio value reflects valued assets only. Missing assets are excluded,
> not treated as zero.

Coverage is a trust indicator, not an investment recommendation.

## Boundaries

Dashboard must never:

- calculate Fair Value
- calculate NAV
- calculate ROI
- calculate statistics
- call providers
- call AI
- scrape websites
- mutate RuntimeSession
- mutate Asset Master
- write analytics back into user-owned files

## Consequences

Onecool Collection Portfolio now has a stable DashboardSnapshot contract. This
becomes the read-only input for future Daily Collection Report, web UI, and
other presentation adapters.
