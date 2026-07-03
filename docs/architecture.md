# Onecool OS Architecture

Onecool OS v0.1.0 Alpha uses a layered architecture. Each layer owns one clear
responsibility and exposes data upward through explicit models, loaders, or
services. Upper layers must not bypass lower-layer boundaries.

## Layered Architecture

```text
External Sources
↓
Connector
↓
Normalize
↓
Assets
↓
Ledger
↓
Valuation
↓
Portfolio
↓
Business Logic
↓
Analytics
↓
Services
↓
Dashboard
↓
OFAI
```

## Source of Truth

| Layer | Source of Truth |
| --- | --- |
| Connector | Raw external input |
| Normalize | Standardized records |
| Assets | Asset identity |
| Ledger | Transactions and lifecycle events |
| Valuation | Valuation history |
| Portfolio | Current holdings and aggregation |
| Business Logic | Deterministic calculations, policies, and signals |
| Analytics | Derived snapshots |
| Services | Read-only access interface |
| Dashboard | Display-only views |
| OFAI | Decisions and recommendations |

## Data Flow

External files and platform exports enter through Connectors. Normalize turns
connector output into standardized records. Assets describe what exists. Ledger
records what happened. Valuation records what assets are worth. Portfolio
aggregates current holdings. Business Logic calculates deterministic metrics
and rule-based signals. Analytics stores derived snapshots. Services expose
stable read-only interfaces. Dashboard displays service-backed views. OFAI will
consume context and recommendations in future sprints.

## Module Responsibilities

### Connector

Connectors import or sync raw external files and platform outputs. They should
not own business rules or normalized portfolio state.

### Normalize

Normalize standardizes connector output into canonical records. It validates
shape and source identity before data reaches business layers.

### Assets

Assets own identity and descriptive metadata for funds, securities, sports
cards, real estate, cash, and future asset classes.

### Ledger

Ledger owns transaction history and lifecycle events. Asset modules should not
store transaction history independently.

### Valuation

Valuation owns valuation history. Valuation records are historical and should
not overwrite previous records.

### Portfolio

Portfolio aggregates current holdings and summary values. It consumes Assets,
Ledger, and Valuation, but owns no source history.

### Business Logic

Business Logic owns deterministic calculations, policies, and rule-based
signals. Calculators produce metrics. Evaluators produce signals. Policies
configure rules. Business Logic consumes read-only context and stores no source
data.

The first Business Logic Engine is Cash Flow. It consumes Ledger data through
`BusinessLogicContext` and produces deterministic `CASH_FLOW` metric results.
It does not own or modify ledger transactions.

The second Business Logic Engine is Allocation. It consumes values already
available in `BusinessLogicContext`, groups holdings or positions by asset
category, and produces deterministic `ALLOCATION` metric results. It does not
calculate ROI, IRR, Risk, rebalancing, recommendations, market prices, API
data, or currency conversion.

### Analytics

Analytics owns derived snapshots, including performance, allocation, cash flow,
and risk summaries produced from validated lower layers.

### Services

Services provide stable read-only access for CLI, Dashboard, API, Automation,
and OFAI. Services consume lower layers and do not mutate files.

### Dashboard

Dashboard owns display-only views. It consumes Services and does not own or
modify source data.

### OFAI

OFAI will own future decisions and recommendations. It must consume validated
context from lower layers rather than inventing source data.

## Read-Only Boundaries

- Dashboard is display-only.
- Services are read-only in the Alpha architecture.
- Business Logic does not modify Portfolio, Ledger, Valuation, or Analytics.
- Analytics does not modify Portfolio, Ledger, or Valuation.
- Portfolio does not own source history.
- Valuation records are append-style history.
- Ledger transactions and events are immutable records.
- Connectors preserve raw input boundaries.

Future mutation workflows should be implemented through explicit command or
use-case layers, not by directly mutating display, service, analytics, or
aggregation objects.

## Architecture Principles

- Model first.
- Asset first.
- Valuation before decision.
- Scenario before prediction.
- Architecture freeze unless explicitly approved.
- Test before trust.
- Daily-use workflows over one-time demos.
- Readability over unnecessary abstraction.
- Stable boundaries before automation.
