# ADR-007 Portfolio NAV Engine

## Status

Proposed

## Context

Onecool OS now has RuntimeSession, Asset Master, Collection Sync, valuation
records, eBay Sold Evidence, ORF, Dashboard, Daily Report, Decision Queue, and
OFAI Context. The next product need is a deterministic portfolio NAV layer
that can calculate cost, market value, unrealized gain/loss, ROI, and
valuation coverage without turning Dashboard or RuntimeSession into
calculation owners.

## Decision

Create `onecool_os.portfolio.nav` as the Portfolio NAV Engine.

The engine consumes runtime assets, existing `ValuationRecord` objects, and
upstream evidence status. It produces immutable `AssetNavLine` and
`PortfolioNavSnapshot` outputs.

NAV is derived only from eligible valuation records. Missing values are never
treated as zero. Verified and estimated coverage are separate. Evidence
validation remains upstream. NAV is not a recommendation.

## Currency Policy

No FX conversion occurs in the NAV Engine.

The deterministic design is one currency per snapshot. A snapshot may
aggregate only assets whose cost currency matches the snapshot currency. If an
asset has market value in a different currency from its cost basis, the engine
does not calculate gain/loss for that asset and marks the snapshot
`CURRENCY_MISMATCH`.

The engine never silently converts currencies and never builds a mixed
currency aggregate.

## Valuation Policy

For each asset, the engine may use eligible Primary Market Price valuation
records, supporting estimate valuation records classified as `ESTIMATED`, and
upstream verified eBay Sold evidence status when evidence is available.

The engine must not use `NEEDS_REVIEW`, `REJECTED`, `NO_MATCH`, or unverified
evidence as trusted NAV input.

When multiple eligible valuation records exist for one asset, the engine uses
the latest valuation date and then deterministic tie-break by valuation record
ID. It does not average records and does not calculate median in this sprint.

## Calculation Policy

Per asset:

- `unrealized_gain_loss = market_value - cost_basis`
- `roi_percent = unrealized_gain_loss / cost_basis * 100`

Portfolio snapshot:

- `total_cost_basis = sum eligible cost basis in snapshot currency`
- `total_market_value = sum eligible market values in snapshot currency`
- `unrealized_gain_loss = total_market_value - total_cost_basis`
- `roi_percent = unrealized_gain_loss / total_cost_basis * 100`
- `valuation_coverage_percent = assets_with_market_value / total_assets * 100`
- `verified_coverage_percent = verified_assets / total_assets * 100`

Money values are rounded to two decimal places. Percent values are rounded to
four decimal places. `Decimal` is used internally.

## Boundaries

NAV Engine does not:

- Call eBay, Gemini, ChatGPT, Card Ladder, or external APIs.
- Scrape websites.
- Create valuation records.
- Select prices from unverified evidence.
- Estimate missing values.
- Perform FX conversion.
- Modify Asset Master.
- Mutate RuntimeSession.
- Change Dashboard presentation.
- Recommend buy, hold, or sell actions.

## Consequences

Dashboard, Daily Report, Decision Queue, and OFAI can consume NAV snapshots
later without recalculating portfolio NAV. The tradeoff is that mixed-currency
portfolio totals remain unavailable until a future FX Engine exists.

## Future Work

- Portfolio NAV Dashboard Integration
- Portfolio NAV Daily Report Integration
- FX Engine
- Median / average comparable policy, if explicitly approved
- Persistent NAV snapshots
