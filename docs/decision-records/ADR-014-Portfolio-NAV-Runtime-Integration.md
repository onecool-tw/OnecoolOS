# ADR-014 Portfolio NAV Runtime Integration

Status: Accepted

## Context

Onecool OS has RuntimeSession, eBay Sold Evidence, Onecool Fair Value,
Fair Value to ValuationRecord integration, Portfolio NAV, and Dashboard NAV
presentation. The missing boundary was a deterministic runtime path that feeds
canonical Fair Value valuation records into the existing Portfolio NAV Engine.

## Decision

RuntimeSession now exposes `build_live_portfolio_nav()`.

The method orchestrates only:

```text
RuntimeSession
↓
OnecoolFairValueEngine
↓
FairValueValuationEngine
↓
ValuationRecord collection
↓
PortfolioNavEngine
↓
PortfolioNavSnapshot
```

RuntimeSession does not calculate Fair Value, create valuation rules, calculate
NAV, mutate assets, mutate evidence, or cache duplicated calculation state.

## Canonical Valuation Rule

For collectibles in this integration:

- `ONECOOL_FAIR_VALUE` is the canonical trusted valuation source.
- `INSUFFICIENT_DATA` Fair Value snapshots produce no trusted
  `ValuationRecord`.
- `NEEDS_REVIEW`, `REJECTED`, and `NO_MATCH` evidence remains excluded
  upstream.
- Missing values remain missing.
- Supporting estimates are not silently used in live NAV.
- Source arbitration across Card Ladder, Manual, or future APIs is deferred.
- Multiple canonical records are resolved by existing NAV selection rules:
  latest valuation date first, then deterministic valuation record ID
  tie-break, with a warning.

## Partial Coverage

Partial coverage is valid and must be explicit.

If 1 of 50 assets has a trusted value:

- total assets: 50
- assets with market value: 1
- missing value assets: 49
- valuation coverage: 2.00%
- verified coverage: 2.00%
- NAV status: `PARTIAL`

Market value sums only valued assets. Missing assets are excluded and are not
treated as zero.

## Dashboard Boundary

Dashboard consumes existing `PortfolioNavSnapshot` output. It does not
recalculate NAV, Fair Value, valuation coverage, verified coverage, or source
selection. When NAV is partial, Dashboard displays:

> Portfolio market value reflects valued assets only; missing assets are
> excluded, not treated as zero.

## Boundaries

This integration must not:

- call providers
- scrape eBay
- call Gemini or ChatGPT
- generate research evidence
- invent market values
- perform FX conversion
- calculate buy / hold / sell
- change fair-value methodology
- change evidence validation rules
- place NAV calculations inside RuntimeSession
- write calculated analytics back into Asset Master

## Consequences

The canonical collectible market valuation path is now operational:

```text
Verified Evidence -> Fair Value -> ValuationRecord -> Portfolio NAV -> Dashboard
```

Real data with no verified evidence continues to report insufficient data
honestly. Synthetic tests can prove partial coverage without making fabricated
real-data claims.
