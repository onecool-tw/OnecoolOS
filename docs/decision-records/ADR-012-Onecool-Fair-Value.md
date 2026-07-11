# ADR-012 Onecool Fair Value

Status: Accepted

## Context

Onecool OS now has provider-independent eBay Sold Evidence, Research Queue,
Research Workbench, RuntimeSession evidence attachment, Portfolio NAV, and
Investment Performance. The next boundary is a deterministic layer that turns
verified sold comparable evidence into an auditable collectible fair value.

Onecool Fair Value is not a provider, valuation API, NAV engine, dashboard
feature, or recommendation layer. It accepts only validated evidence that has
already passed the eBay Sold Evidence rules.

## Decision

Create a dedicated Fair Value engine under `onecool_os.fair_value`.

The engine consumes verified eBay Sold evidence and produces
`OnecoolFairValueSnapshot` records. Future ValuationRecord integration may use
these snapshots as canonical collectible market price inputs, but this ADR
does not create valuation records.

## Architecture

```text
Verified eBay Sold Evidence
↓
Comparable Aggregation
↓
Statistics
↓
Evidence Quality Score
↓
Onecool Fair Value
↓
Future ValuationRecord
```

## Comparable Selection

Only `VERIFIED` eBay Sold evidence may participate.

The engine rejects evidence with:

- `NEEDS_REVIEW`, `REJECTED`, or `NO_MATCH` status
- identity mismatch
- grade mismatch
- wrong parallel
- missing sold date
- missing sold price
- missing eBay item ID

The default sample window is the latest 10 verified sold comparable records
within 180 days. Sample size and window length are configurable.

Duplicate sold records are de-duplicated by eBay item ID or sold URL before
statistics are calculated.

## Statistics

The engine calculates:

- minimum
- maximum
- median
- arithmetic mean
- trimmed mean
- standard deviation
- sample count
- latest sold date
- oldest included date

The engine uses `Decimal` arithmetic and does not use float internally.

## Fair Value Rule

- Five or more verified comparables: median, confidence `HIGH`
- Three or four verified comparables: median, confidence `MEDIUM`
- One or two verified comparables: median, confidence `LOW`
- Zero verified comparables: no fair value, confidence `INSUFFICIENT_DATA`

The engine never fabricates prices. If there is no verified evidence, it
reports insufficient data.

## Evidence Quality Score

Evidence Quality Score is a deterministic 0-100 score with component
breakdown:

- sample size
- identity match
- freshness
- liquidity
- evidence completeness

Warnings remain visible and include low sample size, low liquidity, stale or
missing sold evidence, and insufficient verified evidence.

## Liquidity

Liquidity is derived from sold comparable counts inside 30, 90, and 180 days.

- `HIGH`: at least five sales in 30 days
- `MEDIUM`: at least three sales in 90 days
- `LOW`: at least one sale in 180 days
- `ILLIQUID`: no included sales

## Freshness

Freshness is derived from the latest included sold date.

- `CURRENT`: latest sale within 30 days
- `AGING`: latest sale within 31-90 days
- `STALE`: latest sale older than 90 days
- `UNKNOWN`: no included sale

## Runtime Boundary

`RuntimeSession` may expose convenience methods:

- `build_fair_value()`
- `fair_value(asset_id)`

RuntimeSession delegates to the Fair Value engine. It does not calculate fair
value internally.

## Boundaries

The Fair Value engine must not:

- scrape websites
- call providers
- create NAV
- create recommendations
- calculate portfolio ROI
- mutate evidence
- update Dashboard
- create ValuationRecord objects in this foundation sprint

## Consequences

Onecool OS gains a deterministic and replayable fair value boundary for
collectibles. ValuationRecord integration can be implemented later without
mixing provider research, evidence validation, fair value calculation, NAV,
Dashboard presentation, or recommendations.
