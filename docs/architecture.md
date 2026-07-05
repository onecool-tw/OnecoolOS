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
Scenario
↓
OFAI
```

## v0.2 Beta Architecture

```text
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
Dashboard
↓
Scenario
↓
OFAI
↓
Decision
↓
Future Recommendation Engine
↓
Future LLM
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
| Scenario | Structured scenario objects |
| OFAI | Decisions and recommendations |
| Decision | Decision options, scores, readiness, and audit trails |

## Layer Responsibilities

| Layer | Responsibility |
| --- | --- |
| Business Logic | Calculate deterministic metrics and signals |
| Analytics | Store derived snapshots |
| Dashboard | Present analytics and service-backed display models |
| Scenario | Structure A/B/C/D possible futures |
| OFAI | Prepare deterministic decision context |
| Decision | Evaluate options, trade-offs, readiness, and audit trails |

## Decision Platform

The v0.2 Beta Decision Platform is the architecture path from deterministic
metrics to future AI-assisted decisions:

```text
Business Logic
↓
Analytics
↓
Dashboard
↓
Scenario
↓
OFAI
↓
Decision
```

Business Logic calculates. Analytics stores. Dashboard presents. Scenario
structures possibilities. OFAI prepares context. Decision evaluates options and
audit trails. Future Recommendation and LLM layers must consume Decision and
OFAI context rather than bypassing deterministic layers.

## Decision Boundaries

| Boundary | Rule |
| --- | --- |
| Business Logic | Calculates metrics, does not choose actions |
| Analytics | Stores snapshots, does not calculate new recommendations |
| Dashboard | Presents information, does not calculate or decide |
| Scenario | Structures possibilities, does not recommend |
| OFAI | Prepares context, does not call LLMs in v0.2 |
| Decision | Evaluates options, does not make final user decisions |

### Decision

Decision Engine evaluates structured options, candidates, constraints, scores,
readiness states, and audit trails. It is deterministic and auditable. It does
not recommend final actions, call LLMs, predict markets, mutate source data,
provide legal/tax/financial advice as final truth, or execute actions.

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

Collectible connectors are the foundation for Collectible Radar MVP. They
accept local fixture/export records from eBay Sold, Card Ladder, PWCC, Goldin,
and Fanatics Collect and normalize them into shared collectible market records.
They do not call live APIs, scrape websites, choose final valuation, calculate
confidence, or decide which marketplace is correct.

Collectible live ingestion must prefer safe, user-approved, export-based or
API-based workflows. Unauthorized scraping is not part of the MVP. The live
connector readiness review is documented in
`docs/live-connectors/collectible-readiness.md`.

PSA Collection Integration is the first production-ready ingestion path. The
connector-layer importer reads real PSA Collection CSV exports, validates
certificates and grades, preserves identifiers, returns normalized sports card
asset records, and emits `ImportSummary` plus reusable `ImportAudit`. It only
imports. It does not calculate valuation, confidence, business logic, or
recommendations, and it does not mutate source CSV files, Ledger, Valuation, or
production data.

For sports cards, eBay Sold is the Primary Market Price source. Card Ladder,
PWCC, Goldin, Fanatics Collect, and Manual inputs are Validation Sources.
Valuation confidence and source agreement belong to later Valuation, Business
Logic, Analytics, Dashboard, and Decision layers.

eBay Sold readiness is documented in
`docs/live-connectors/ebay-sold-readiness.md`. Approved ingestion options are
official eBay API if allowed and available, user-provided CSV / JSON exports,
and manual fixture imports. Unauthorized scraping is rejected for MVP. eBay
Sold records must remain independent valuation records and must not overwrite
valuation history or hide disagreement with validation sources.

Manual Valuation Import sits at the Valuation boundary as an auditable
fallback / validation input. It converts user-provided CSV or JSON observations
into independent `ValuationRecord` objects with source `MANUAL` and reusable
`ImportAudit`. It does not overwrite history, replace eBay Sold as Primary
Market Price, calculate confidence, calculate agreement, predict prices,
recommend actions, call APIs, scrape websites, or mutate source files.

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

The Collectible Valuation Mapper sits between collectible market records and
Valuation. It converts each market observation into a `ValuationRecord` plus
metadata for source role, external ID, raw market record ID, and raw payload.
It does not choose final market value, calculate confidence, resolve source
agreement, or mutate raw imports.

Market Intelligence sits after valuation mapping and before Business Logic. It
evaluates market data quality only: Primary Market Price presence, Validation
Source coverage, source agreement, freshness, liquidity, warnings, and
explainable confidence components. It does not determine final valuation,
predict prices, recommend buying or selling, call live APIs, mutate source
data, or modify valuation history.

`reference_datetime` is injected into Market Intelligence builders so replay,
backtesting, and historical reconstruction remain deterministic.

### Portfolio

Portfolio aggregates current holdings and summary values. It consumes Assets,
Ledger, and Valuation, but owns no source history.

### Business Logic

Business Logic owns deterministic calculations, policies, and rule-based
signals. Calculators produce metrics. Evaluators produce signals. Policies
configure rules. Business Logic consumes read-only context and stores no source
data.

The Collectible Intelligence Engine consumes Market Intelligence and produces
collectible-specific quality signals for market quality, valuation quality,
liquidity quality, source quality, review status, and warnings. It does not
choose final valuation, predict prices, recommend buy/sell/hold actions, set
target prices, call APIs, mutate source data, mutate valuation history, or
perform OFAI reasoning.

Radar Engine sits after deterministic intelligence and before Analytics. It
detects meaningful changes over time and produces new, resolved, changed, and
escalated signals. Radar does not calculate valuation, modify historical data,
predict markets, recommend buy/sell actions, call APIs, mutate source data, or
perform LLM reasoning. Analytics stores Radar output, Dashboard displays it,
and Decision consumes it.

Timeline Analytics sits after Radar Engine. It summarizes historical Radar
snapshots into deterministic trend direction, trend strength, trend summaries,
signal statistics, quality trends, warnings, and source snapshot IDs. It does
not calculate valuation, modify history, predict future performance, recommend
actions, mutate source data, or call APIs. Dashboard displays Timeline
Analytics. Decision and OFAI consume it.

Dashboard remains presentation-only. Collectible Dashboard assembles existing
Business Logic, Market Intelligence, Radar, Timeline Analytics, and optional
Decision outputs into display sections. It does not recalculate confidence,
trend, valuation, quality, or business rules.

Daily Radar Report sits after Dashboard as a structured presentation output. It
consumes Dashboard sections and assembles fixed report sections without
terminal, HTML, PDF, or Web formatting. It does not recalculate business logic,
valuation, confidence, trend, quality, or recommendations.

Decision Queue sits after Daily Radar Report. It prioritizes deterministic
review work into critical, high, medium, and low groups. It classifies; it does
not recommend. It does not calculate valuation, predict prices, mutate source
data, mutate history, call APIs, or invoke LLMs.

Collectible OFAI Context sits after Decision Queue. It prepares deterministic
context for future OFAI workflows by summarizing collection state, market
quality, radar changes, timeline trend, review priorities, and warnings. It is
not an AI model and does not recommend actions, predict prices, call LLMs,
mutate source data, modify history, or calculate valuation.

The Collectible Golden Dataset sits beside the pipeline as a regression safety
net. It provides synthetic fixture inputs and expected outputs for connector
normalization, valuation mapping, Market Intelligence, Collectible
Intelligence, Radar, Timeline Analytics, Dashboard, Daily Radar Report,
Decision Queue, and OFAI Context. It does not call APIs, scrape websites,
predict prices, recommend actions, mutate production data, or include private
user data.

The Business Logic Pipeline Runner orchestrates registered calculators and
evaluators in deterministic order. It returns a structured execution report for
Analytics, Services, Dashboard, and future OFAI consumption. The pipeline does
not calculate by itself, store results, write files, or mutate context.

Analytics Integration maps pipeline reports into AnalyticsSnapshot-compatible
structures. It is a bridge from Business Logic to Analytics and does not
calculate metrics, store data, write files, or mutate source data.

The first Business Logic Engine is Cash Flow. It consumes Ledger data through
`BusinessLogicContext` and produces deterministic `CASH_FLOW` metric results.
It does not own or modify ledger transactions.

The second Business Logic Engine is Allocation. It consumes values already
available in `BusinessLogicContext`, groups holdings or positions by asset
category, and produces deterministic `ALLOCATION` metric results. It does not
calculate ROI, IRR, Risk, rebalancing, recommendations, market prices, API
data, or currency conversion.

The first Business Logic assessment engine is Risk. It consumes
`BusinessLogicContext` and produces deterministic `RISK` metric results plus
rule-based signals. It evaluates portfolio health without market prediction,
AI reasoning, external APIs, or source data mutation.

The Performance Engine computes deterministic unrealized performance from
`BusinessLogicContext`. It produces `PERFORMANCE` metric results for cost
basis, market value, unrealized gain, and unrealized return while leaving ROI,
IRR, benchmark comparison, and drawdown to later engines.

### Analytics

Analytics owns derived snapshots, including performance, allocation, cash flow,
and risk summaries produced from validated lower layers.

### Services

Services provide stable read-only access for CLI, Dashboard, API, Automation,
and OFAI. Services consume lower layers and do not mutate files.

### Dashboard

Dashboard owns display-only views. It consumes Services and does not own or
modify source data.

Dashboard Analytics views present Analytics-derived Cash Flow, Allocation,
Performance, Risk, and Pipeline summaries. Dashboard does not calculate
metrics; Business Logic owns calculations and Analytics owns derived
snapshots.

### Scenario

Scenario owns deterministic A/B/C/D scenario objects. It consumes structured
Business Logic, Analytics, and Dashboard context and prepares trusted scenario
inputs for future OFAI. Scenario does not make recommendations, perform AI
reasoning, predict markets, or mutate source data.

### OFAI

OFAI prepares decision context from deterministic Business Logic, Analytics,
Dashboard, and Scenario inputs. OFAI is an orchestration layer, not an AI
model. It does not call LLMs, make recommendations, predict markets, or mutate
source data in this foundation.

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
