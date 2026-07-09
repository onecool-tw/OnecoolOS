# ADR-005 Investment Performance and Asset Lifecycle

## Status

Proposed

## Context

Onecool OS now supports real asset imports, valuation records, Source
Agreement, Market Intelligence, Ledger foundations, Dashboard, Daily Reports,
Decision Queue, and OFAI Context. The next architecture decision is how to
model investment performance and asset lifecycle without forcing users to
reconstruct years of historical transactions before the system becomes useful.

Many users already own assets before Onecool OS exists. Their current holdings
often arrive through portfolio imports, PSA Collection exports, broker
exports, fund files, cash balances, or manually prepared records. Requiring
complete historical transaction backfill would make product onboarding heavy,
error-prone, and unrealistic.

## Decision

Existing holdings use imported opening cost basis.

Historical transactions are optional and never required for initial use.
Future transactions should be recorded prospectively from the point Onecool OS
begins tracking the asset.

Performance and lifecycle are separate concerns:

- Performance measures returns, cost basis, gains, fees, proceeds, and holding
  period.
- Lifecycle tracks asset state transitions such as owned, listed, sold, paid,
  and archived.

Importers may preserve source fields that support performance and lifecycle,
but importers must not calculate performance or make lifecycle decisions beyond
deterministic source-state mapping.

## Core Principles

- Existing holdings use opening cost basis.
- Historical transactions are optional, not required.
- Future transactions should be recorded prospectively.
- Cost basis remains in the original transaction currency.
- FX conversion belongs to a future FX Engine.
- Performance and lifecycle are separate concerns.
- Imported source facts should remain auditable.
- Derived performance should be recalculable from source inputs.
- Dashboard displays performance and lifecycle state but does not calculate
  them.
- OFAI consumes context and should not own performance calculations.

## Lifecycle States

Supported lifecycle states:

- `OWNED`
- `LISTED`
- `SOLD`
- `PAID`
- `ARCHIVED`

### OWNED

The asset is currently owned and available for valuation, inventory, dashboard,
and review workflows.

### LISTED

The asset is owned but listed for sale. Listing state should not imply a sale
has occurred.

### SOLD

The asset has a completed sale event, but payment or settlement may not yet be
complete.

### PAID

Sale proceeds have been paid or settled.

### ARCHIVED

The asset is no longer active in daily workflows but remains preserved for
history, audit, and reporting.

## Performance Concepts

### Cost Basis

Cost basis is the imported or transaction-derived acquisition cost of the
position. For existing holdings, imported cost basis is accepted as the opening
position cost.

Cost basis remains in the original transaction currency. Currency conversion
is out of scope for this ADR and belongs to a future FX Engine.

### Current Market Value

Current market value comes from valuation records and source agreement policy.
It should not be calculated by importers.

### Unrealized Gain / Loss

Unrealized gain or loss compares current market value against cost basis while
the asset remains owned.

### Realized Gain / Loss

Realized gain or loss compares sale proceeds against cost basis and sale costs
after the asset is sold.

Realized gain/loss belongs to future lifecycle and sale-settlement workflows.
The collectible performance integration remains unrealized-only until the
Lifecycle Engine defines sold, paid, fee, and net-proceeds behavior.

### Holding Period

Holding period is measured from acquisition or opening-position date to the
current reference date, sale date, or archived date depending on context.

### Annualized Return

Annualized return is a derived performance metric. It should be calculated by a
future Performance Engine capability, not by importers.

### Fees

Fees include marketplace fees, payment fees, platform fees, grading fees,
shipping, insurance, taxes, and other explicit costs when available.

### Net Proceeds

Net proceeds represent sale proceeds after fees and costs when sale settlement
data is available.

## Data Strategy

### PSA CSV `My Cost`

`My Cost` should be treated as opening cost basis for existing PSA Collection
holdings.

It does not require reconstructing historical purchase transactions.

Collectible performance integrations may consume normalized PSA/BGS records and
pass `My Cost` or normalized `cost` into the reusable Investment Performance
Engine as opening cost basis. The original source currency must be preserved.
Notes must not be parsed to derive alternate local-currency cost such as TWD
cost. FX conversion belongs to a future FX Engine.

### PSA Sold Fields

PSA sale fields can become future realized performance inputs when present:

- `Sold Price`
- `Sold Fees`
- `Sold Proceeds`
- `Sold Date`
- `Sold On`
- `Payment Date`

These fields should feed Ledger and lifecycle events in future work.

### Manual Input

Manual input is allowed but optional. Users may provide opening cost basis,
manual valuation, sale proceeds, fees, or lifecycle notes when source exports
are incomplete.

Manual input should be preserved as auditable source data.

### Historical Backfill

Historical backfill is not required.

Users may optionally backfill historical transactions later, but Onecool OS
must remain useful with opening positions plus prospective future events.

## Boundaries

### Performance Engine

Performance Engine calculates returns and performance metrics. It consumes
opening cost basis, future Ledger transactions, valuation records, and
reference dates.

It should calculate:

- cost basis
- current market value
- unrealized gain / loss
- realized gain / loss
- holding period
- annualized return
- fees
- net proceeds

### Lifecycle Engine

Lifecycle Engine tracks asset state. It consumes source state, inventory state,
Ledger events, and sale/payment events.

It should track transitions between:

```text
OWNED
↓
LISTED
↓
SOLD
↓
PAID
↓
ARCHIVED
```

The lifecycle path is not always linear. Assets may be delisted, relisted, or
archived manually in future workflows.

### Ledger

Ledger records future events prospectively. It should not require complete
historical transaction reconstruction for existing holdings.

Ledger should own future buy, sell, fee, payment, transfer, and adjustment
events.

### Importer

Importer preserves source facts and maps them into normalized records. Importer
does not calculate performance, annualized return, source agreement,
recommendations, or final valuation.

### Dashboard

Dashboard only displays performance and lifecycle outputs from lower layers.
It does not calculate returns or mutate lifecycle state.

### OFAI

OFAI consumes deterministic context from Performance, Lifecycle, Dashboard,
Decision Queue, and related layers. OFAI does not own performance calculation,
lifecycle state, or source records.

## Consequences

### Positive

- Users can start with current holdings without reconstructing years of
  history.
- Imported cost basis becomes enough for useful unrealized performance.
- Future transactions remain clean and prospective.
- Performance and lifecycle can evolve independently.
- FX complexity is deferred to a dedicated future engine.

### Tradeoffs

- Early performance may not be as precise as a fully reconstructed historical
  ledger.
- Opening cost basis must be trusted as imported or manually supplied.
- Realized performance for already-sold historical assets may require optional
  manual or source-field support.
- Multi-currency reporting requires explicit future FX policy.

## MVP Decision

For MVP and Beta:

- Accept opening cost basis from imports.
- Do not require historical backfill.
- Track future transactions prospectively.
- Keep cost basis in original currency.
- Keep FX conversion out of scope.
- Keep importer behavior simple and auditable.
- Treat PSA `My Cost` as opening cost basis.
- Treat PSA sold fields as documented future realized-performance inputs.

## GA Decision

Before GA, Onecool OS should add:

- Performance Engine support for opening positions and prospective Ledger
  events.
- Lifecycle Engine support for `OWNED`, `LISTED`, `SOLD`, `PAID`, and
  `ARCHIVED`.
- Explicit mapping from PSA sold fields into Ledger and lifecycle events.
- Optional historical backfill workflows.
- FX Engine design for multi-currency performance reporting.
- Dashboard surfaces for unrealized, realized, and lifecycle summaries.

## Related Documents

- `docs/trials/psa-collection-gap-analysis.md`
- `docs/trials/collectible-radar-real-data-trial.md`
- `docs/releases/performance-closed-loop-review.md`
- `docs/releases/v0.3.0-beta.md`
- `docs/decision-records/ADR-004-Collectible-Radar-MVP.md`
