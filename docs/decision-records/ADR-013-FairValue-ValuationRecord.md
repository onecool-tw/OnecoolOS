# ADR-013 Fair Value to ValuationRecord

Status: Accepted

## Context

ADR-012 introduced Onecool Fair Value as the deterministic layer that converts
verified eBay Sold evidence into auditable collectible fair value snapshots.
Portfolio NAV already consumes `ValuationRecord` objects, so the next boundary
is a canonical integration path from Fair Value into the existing valuation
runtime.

## Decision

Create `onecool_os.valuation.integration` as the deterministic bridge from
`OnecoolFairValueSnapshot` to `ValuationRecord`.

For collectible assets, `ONECOOL_FAIR_VALUE` is the canonical valuation source
created from verified evidence. The integration layer creates exactly one
trusted `ValuationRecord` per asset and valuation source. If Fair Value has
`INSUFFICIENT_DATA`, the integration layer creates a runtime placeholder
status instead of a trusted valuation record.

## Architecture

```text
Verified Evidence
↓
Onecool Fair Value
↓
ValuationRecord
↓
Portfolio NAV
↓
Dashboard
↓
Daily Report
```

## Valuation Source Model

The valuation source enum now includes:

- `ONECOOL_FAIR_VALUE`
- `CARD_LADDER`
- `MANUAL`
- `EBAY_ONLY`
- `CUSTOM`

This sprint only creates trusted records from `ONECOOL_FAIR_VALUE`. Future
source arbitration will decide how multiple source-specific records coexist.

## Canonical Rules

- Trusted Fair Value creates one `ValuationRecord`.
- `INSUFFICIENT_DATA` creates no trusted valuation.
- Missing market value is rejected.
- Missing currency is rejected.
- Invalid confidence is rejected.
- Duplicate valuation source for the same asset is rejected.
- Duplicate valuation record IDs are rejected.
- Missing asset identity is rejected.

The system never invents prices for missing evidence.

## Metadata Preservation

The integration mapping preserves:

- valuation record ID
- asset ID
- cert number
- valuation source
- market value
- currency
- confidence
- Evidence Quality Score
- latest sold date
- sample count
- freshness status
- liquidity
- warnings
- reference datetime
- generated datetime

The NAV-facing object remains the existing `ValuationRecord`.

## Runtime Boundary

RuntimeSession exposes:

- `build_valuation_records()`
- `valuation_records()`
- `valuation_record(asset_id)`

RuntimeSession delegates to valuation integration and does not calculate Fair
Value, select sources, estimate missing prices, perform FX conversion, create
NAV, or update presentation layers.

## Boundaries

This integration must not:

- call providers
- scrape websites
- calculate NAV
- update Dashboard rendering
- generate reports
- mutate Fair Value snapshots
- mutate Evidence
- estimate missing prices
- create recommendations
- perform FX conversion

## Consequences

Onecool OS now has a canonical collectible valuation flow:

```text
Verified Evidence -> Fair Value -> ValuationRecord -> Portfolio NAV
```

Portfolio NAV continues to consume only `ValuationRecord` objects. Fair Value
remains auditable and immutable, while valuation runtime becomes the stable
handoff point for downstream portfolio and presentation layers.
