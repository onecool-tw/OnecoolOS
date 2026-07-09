# Performance Closed-Loop Review

Investment Performance is now connected across the first full Onecool OS
presentation and context loop. The loop starts with deterministic performance
calculation and ends with OFAI-ready deterministic context.

This review verifies that the flow remains consistent with ADR-005:
Investment Performance and Asset Lifecycle.

## Closed-Loop Summary

The reviewed loop is:

```text
Investment Performance Engine
↓
Collectible Performance Integration
↓
Performance Dashboard
↓
Performance Daily Report
↓
Performance Decision Queue
↓
Performance OFAI Context
```

The closed loop is deterministic, replayable, and presentation-safe. It does
not predict prices, recommend buy/sell actions, call APIs, mutate user data, or
overwrite valuation history.

## Layer Responsibility Review

| Layer | Responsibility | Boundary |
| --- | --- | --- |
| Investment Performance Engine | Calculates cost basis, market value, unrealized gain/loss, unrealized gain percent, and holding days | Does not calculate FX, IRR/XIRR, realized gain/loss, annualized return, confidence, source agreement, or recommendations |
| Collectible Performance Integration | Maps PSA/BGS-style collectible records and caller-prepared valuation records into performance snapshots | Does not parse notes for local currency cost, select final valuation, or mutate source records |
| Performance Dashboard | Displays performance snapshots as portfolio summary, asset table, top movers, and warnings | Does not recalculate performance or valuation |
| Performance Daily Report | Assembles dashboard performance sections into report sections | Does not calculate performance, FX, realized gain/loss, or recommendations |
| Performance Decision Queue | Prioritizes performance review work from report output | Does not recommend buy/sell actions or calculate financial metrics |
| Performance OFAI Context | Prepares deterministic investment context for future OFAI reasoning | Does not invoke LLMs, predict prices, recommend actions, or mutate inputs |

## Data Flow Review

### 1. Engine Output

`InvestmentPerformanceEngine` produces `InvestmentPerformanceSnapshot` records.
Snapshots include:

- `asset_id`
- `cost_basis`
- `cost_currency`
- `market_value`
- `market_currency`
- `unrealized_gain`
- `unrealized_gain_percent`
- `holding_days`
- `performance_status`
- `warnings`
- `generated_at`

### 2. Collectible Mapping

`CollectiblePerformanceBuilder` connects sports-card records to the reusable
engine:

- `My Cost` or normalized `cost` becomes opening cost basis.
- Original cost currency is preserved.
- Acquisition date is used only for holding days.
- Caller-prepared valuation records provide market value.
- Notes are not parsed for TWD or alternate local-currency cost.

### 3. Dashboard Presentation

Performance Dashboard consumes snapshots and presents:

- total cost basis
- total market value
- total unrealized gain/loss
- total unrealized percent
- performing asset count
- missing valuation count
- missing cost basis count
- asset performance table
- top gainers
- top losers
- largest position
- oldest holding
- newest holding
- warnings

Dashboard aggregation is presentation-only and uses fields already present in
the snapshots.

### 4. Daily Report Assembly

Collectible Daily Radar Report consumes existing Dashboard performance
sections and adds:

- Performance Summary
- Top Movers
- Performance Warnings

The report layer does not calculate performance.

### 5. Decision Queue Prioritization

Decision Queue consumes Daily Report performance output and classifies review
work:

- Critical: Missing Cost Basis, Missing Market Value
- High: Insufficient Data, Currency Mismatch
- Medium: Missing Holding Date
- Low: Performance Review Only

This is prioritization only. It is not a recommendation engine.

### 6. OFAI Context Preparation

Collectible OFAI Context consumes the Daily Report and Decision Queue and
prepares:

- Performance Overview
- Performance Review Priorities
- Performance Warnings
- Top Gainers
- Top Losers

OFAI Context remains deterministic context preparation, not AI reasoning.

## Public Contract Review

The following contracts are now part of the performance closed loop:

- `InvestmentPerformanceSnapshot`
- `InvestmentPerformanceEngine`
- `CollectiblePerformanceBuilder`
- `PerformanceDashboard`
- `PerformanceDashboardBuilder`
- `CollectibleDailyRadarReport.performance_summary`
- `CollectibleDailyRadarReport.top_movers`
- `DecisionQueue`
- `DecisionQueueItem`
- `CollectibleOFAIContext.performance_overview`
- `CollectibleOFAIContext.performance_review_priorities`
- `CollectibleOFAIContext.top_movers`

These surfaces should remain backward compatible during the v0.4 beta cycle
unless a future release explicitly documents a breaking change.

## Boundary Verification

Performance Engine calculates only:

- cost basis
- market value
- unrealized gain/loss
- unrealized gain percent
- holding days

Dashboard displays only.

Daily Report assembles only.

Decision Queue prioritizes review work only.

OFAI prepares deterministic context only.

No layer in this loop:

- predicts prices
- recommends buy/sell actions
- calls APIs
- scrapes websites
- mutates performance snapshots
- mutates valuation history
- mutates reports
- mutates decision queues
- invokes LLMs

## Known Limitations

- No FX Engine.
- No IRR/XIRR.
- No realized gain/loss.
- No lifecycle sale settlement.
- No annualized return unless explicitly added in a future engine.
- No market prediction.
- No recommendation engine.
- No persistent performance history store.
- No dashboard UI beyond structured data models.

## Future Risks

- Multi-currency portfolios require an FX Engine before cross-currency totals
  can be trusted.
- Realized performance requires Lifecycle and Ledger sale-settlement rules.
- Annualized return should not be added casually; it requires clear date,
  cash-flow, and holding-period semantics.
- Decision Queue priority language must continue to avoid recommendation
  phrasing.
- OFAI Context should stay deterministic until an explicit LLM integration
  layer is approved.

## v0.4 Beta Readiness

Investment Performance is ready for v0.4 beta as a deterministic unrealized
performance loop for collectible holdings.

Ready:

- opening cost basis policy from ADR-005
- collectible performance snapshots
- dashboard performance presentation
- daily report performance presentation
- decision queue performance prioritization
- OFAI performance context
- regression tests for each layer

Not ready for v0.4 beta:

- FX-adjusted performance
- realized gain/loss
- annualized return
- IRR/XIRR
- sale settlement lifecycle
- recommendation workflows

## Recommended Next Step

Prepare the v0.4.0-beta release documentation. The release should describe
Investment Performance as an unrealized, deterministic, opening-cost-basis
workflow and explicitly defer FX, realized gain/loss, IRR/XIRR, and
recommendations.
