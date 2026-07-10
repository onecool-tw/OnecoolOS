# Onecool OS

Onecool OS is a personal asset operating system for modeling assets, valuing
positions, testing scenarios, and supporting better personal decisions.

This document is the single source of truth for product direction,
architecture, module expectations, and development workflow.

## Mission

Build a daily-use personal asset operating system that keeps asset data,
valuation, scenarios, and decisions in one coherent local-first system.

## Vision

Onecool OS should become a personal decision operating system: a trusted place
to understand what a person owns, what it is worth, what could happen next, and
which actions deserve attention.

The system should grow from simple asset models into valuation, intelligence,
reporting, and dashboard layers without losing modularity or becoming dependent
on one external service.

## Philosophy

Onecool OS values clear models, explainable calculations, and practical daily
use over speculative automation. The system should help users think, compare,
and decide. It should not hide uncertainty behind false precision.

Every feature should make the asset picture more accurate, the valuation more
transparent, or the decision workflow more useful.

## Core Principles (Constitution)

- Model First: Every module starts with clear domain models before services,
  storage, or user interfaces.
- Asset First: Asset identity and ownership structure come before analytics.
- Valuation Before Decision: The system must know how positions are valued
  before recommending or ranking actions.
- Scenario Before Prediction: Scenario analysis is preferred over pretending to
  know the future.
- Architecture Freeze: Established architecture must not be redesigned without
  explicit approval.
- Test Before Trust: Every milestone must include tests and must pass before
  release.
- Daily Use: Features should support repeatable daily workflows, not one-time
  demonstrations.

## Architecture

Onecool OS data flow:

```text
External Platform
↓
imports/
↓
Connector
↓
Normalizer
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
Dashboard / CLI / API / Automation
↓
Scenario
↓
OFAI
↓
Future LLM
```

Service-facing surfaces:

```text
Services
↓
Dashboard
Services
↓
CLI
Services
↓
API
Services
↓
Automation
Services
↓
OFAI
```

Connectors import or sync data from external platforms and local exports. They
translate platform-specific files, APIs, or account views into Onecool OS
formats without owning business logic.

Collectible connectors support the Collectible Radar MVP. They preserve source
identity and normalize local market records without selecting final valuation.
For sports cards, eBay Sold is the Primary Market Price. Card Ladder, PWCC,
Goldin, Fanatics Collect, and Manual inputs are Validation Sources. Connector
output must keep enough raw source context for later valuation confidence and
source agreement checks.

The Collectible Valuation Mapper converts each `CollectibleMarketRecord` into
ValuationRecord-compatible history plus metadata. It preserves source role,
external ID, sale price, currency, sale date, URL, raw payload, and raw market
record ID. Mapping does not resolve source consensus, calculate confidence,
select a final market value, or overwrite valuation history.

Market Intelligence evaluates market data quality and reliability. It is a
reusable capability for Collectible Radar, House Radar, Fund Radar, Stock
Radar, Business Radar, and future products. It consumes valuation records and
produces explainable assessments for Primary Market Price, Validation Sources,
source agreement, coverage, freshness, liquidity, warnings, and confidence.
It does not determine final valuation, predict prices, recommend actions, call
live APIs, mutate source data, or modify valuation history. `reference_datetime`
must be injectable for deterministic replay and historical reconstruction.

The Collectible Intelligence Engine is the first product-specific Business
Logic consumer of Market Intelligence. It produces deterministic collectible
quality signals for market quality, valuation quality, liquidity quality,
source quality, review status, and warnings. It does not choose final
valuation, predict prices, recommend buy/sell/hold actions, set target prices,
call APIs, mutate source data, mutate valuation history, or perform OFAI
reasoning.

Radar Engine detects meaningful changes over time. It is reusable for
Collectible Radar, House Radar, Fund Radar, Stock Radar, Business Radar,
Emergency Radar, and future products. Radar consumes deterministic
intelligence output and produces snapshots for new, resolved, changed, and
escalated signals. It does not calculate valuation, modify historical data,
predict markets, recommend buy/sell actions, call APIs, mutate source data, or
perform LLM reasoning. Analytics stores Radar output, Dashboard displays Radar
output, and Decision consumes Radar output.

Timeline Analytics summarizes historical Radar snapshots across time. It is a
reusable analytics capability for Collectible Radar, House Radar, Fund Radar,
Stock Radar, Business Radar, Emergency Radar, and future products. Timeline
Analytics produces trend direction, trend strength, trend summary, signal
statistics, quality trends, warnings, and radar snapshot IDs. It does not
calculate valuation, modify history, predict markets, recommend actions,
mutate source data, or call APIs. Dashboard displays Timeline Analytics.
Decision and OFAI consume Timeline Analytics.

Dashboard is a presentation layer. Collectible Dashboard assembles existing
Business Logic, Market Intelligence, Radar, Timeline Analytics, and optional
Decision outputs into display sections. It does not recalculate confidence,
trend, valuation, or quality. It never predicts, recommends actions, mutates
data, or owns source data.

Daily Radar Report is the first user-facing product output. It consumes the
Collectible Dashboard and assembles structured report sections for collection
summary, market summary, today's changes, timeline summary, review queue, and
warnings. It does not recalculate business logic, valuation, confidence, trend,
or quality, and it never predicts markets or recommends actions.

Decision Queue prioritizes review work from deterministic Daily Radar Report
outputs. It classifies warnings and review items into critical, high, medium,
and low priority groups. Decision Queue does not calculate valuation, predict
prices, recommend buy/sell actions, modify source data, mutate history, call
APIs, or invoke LLMs.

Collectible OFAI Context prepares structured deterministic context from the
Daily Radar Report and Decision Queue. It summarizes collection state, market
quality, radar changes, timeline trend, review priorities, and warnings. It is
not an AI model and does not recommend actions, predict prices, call LLMs,
mutate source data, modify history, or calculate valuation.

The Collectible Golden Dataset protects the full deterministic Collectible
Radar pipeline from regression. It stores synthetic fixtures and expected
outputs under `tests/golden/collectibles/`. Golden tests cover connector
normalization, valuation mapping, Market Intelligence, Collectible
Intelligence, Radar, Timeline Analytics, Dashboard, Daily Radar Report,
Decision Queue, and OFAI Context without private data, APIs, scraping,
prediction, recommendations, or production data mutation.

`imports/` contains raw files exported from external platforms. Raw imports are
not Onecool OS internal data and should not be committed when they contain user
portfolio information.

The Canonical Normalize Layer converts connector input into
`NormalizedRecord` objects before data becomes asset, inventory, or transaction
state. Normalized user portfolio data belongs in `data/portfolio/`.

Assets describe what the user owns. They preserve identity, category,
metadata, and ownership-specific fields for each asset class.

Asset Master is a user-owned metadata layer that augments imported assets
without replacing source identity. For sports cards, PSA/BGS Collection import
remains authoritative for collectible identity. Asset Master may add durable
metadata such as eBay Sold search URL, PSA official URL, REF score, watch
status, target price, notes, optional cost override, and custom metadata. Asset
Master joins primarily by cert number and must not overwrite year, set, card
number, player, grade issuer, grade, variety, or cert number. eBay Sold search
URLs are research entry points only; they are not valuation records by
themselves.

Collection Sync is the mandatory integrity layer before runtime. It compares
PSA/BGS imported records with Asset Master metadata, produces deterministic
differences, warnings, and collection health, and never mutates imports,
automatically merges data, deletes records, calculates valuation, calls APIs,
or calls AI.

Runtime Session executes Collection Sync automatically after imported records
and Asset Master records enter runtime. Runtime stores `sync_report`,
`collection_health`, collection differences, generated time, and helper methods
for future decision-priority support. Dashboard, Daily Report, Decision Queue,
and OFAI remain presentation-only consumers and do not display sync output
until explicitly integrated.

Ledger records what happened. Transactions capture financial changes. Events
capture lifecycle changes. Together, the ledger is the source of truth for
asset history and will be consumed by valuation and portfolio engines over
time.

Valuation owns valuation history. It stores historical valuation records from
manual inputs, normalized connector data, and future market providers. Records
are append-style history and should not overwrite previous records.

Portfolio summarizes derived positions, costs, and totals from validated asset,
ledger, and valuation data.

Business Logic owns deterministic calculations, policies, and rule-based
signals. It consumes read-only Portfolio, Ledger, Valuation, and Analytics
context. Calculators produce metrics. Evaluators produce signals. Policies
configure rules.

Analytics owns derived snapshots. It stores derived outputs from validated
lower layers and does not modify source data.

Services provide stable read-only interfaces for CLI, Dashboard, API,
Automation, and OFAI. They consume lower-layer data through loaders and do not
own source data.

Dashboard displays validated Portfolio and Analytics data through Services. It
owns display-only views and does not own source data.

Scenario Engine turns deterministic Business Logic, Analytics, and Dashboard
context into structured A/B/C/D scenario objects. It does not perform AI
reasoning, make recommendations, predict markets, or mutate source data.

OFAI prepares decision context from deterministic Business Logic, Analytics,
Dashboard, and Scenario inputs. OFAI is not an AI model in this foundation. It
does not call LLMs, make recommendations, predict markets, or mutate source
data.

### Source of Truth

| Layer | Owns |
| --- | --- |
| Connector | Raw external input |
| Normalize | Standardized records |
| Assets | Asset identity |
| Asset Master | User-owned metadata augmentation |
| Collection Sync | Data integrity report before runtime |
| Ledger | Transactions and lifecycle events |
| Valuation | Valuation history |
| Portfolio | Current holdings and aggregation |
| Business Logic | Deterministic calculations, policies, and signals |
| Analytics | Derived snapshots |
| Services | Read-only access interface |
| Dashboard | Display-only views |
| Scenario | Structured scenario objects |
| OFAI | Decisions and recommendations |

### Core Engine

Owns the application lifecycle, plugin loading, event publishing, service
registry, and SQLite-backed core persistence. Core Engine remains independent
from business modules.

### Infrastructure

Provides cross-cutting systems such as configuration, logging, scheduling,
database migrations, and developer workflow. Infrastructure must stay reusable
and must not contain asset-specific business logic.

### Market Engine

Coordinates market data providers through a provider interface and registry. It
normalizes market responses and keeps external data integrations isolated from
portfolio and asset modules.

### Portfolio Engine

Provides aggregation models, holdings, summaries, registry, and loader
primitives. Portfolio is not the owner of source data. It consumes Assets,
Ledger, and Valuation records to expose current holdings and calculated
summaries.

Portfolio owns no transaction history, no valuation history, and no asset
identity. Business Logic layers will calculate ROI, IRR, Allocation, Risk, and
Cash Flow. Portfolio itself should remain calculation-light.

### Business Logic Engine

Provides deterministic calculation and rule-evaluation contracts. Business
Logic consumes read-only Portfolio, Ledger, Valuation, and Analytics context.
It does not own source data and does not store source history.

Calculators produce metric results. Evaluators produce rule-based signals.
Policies configure rules but do not calculate by themselves. The registry
discovers available calculators and evaluators.

The Business Logic Pipeline Runner orchestrates registered calculators and
evaluators in deterministic order. It produces a structured pipeline execution
report containing metric results, signal results, executed engines, skipped
engines, and errors. The runner does not calculate by itself, store results,
write files, or mutate `BusinessLogicContext`.

Analytics Integration maps Business Logic pipeline output into
AnalyticsSnapshot-compatible structures. It maps known Cash Flow, Allocation,
Performance, and Risk metrics and preserves pipeline metadata. It does not
calculate metrics, store data, write files, or mutate source data.

The first Business Logic Engine is Cash Flow. It consumes Ledger data through
`BusinessLogicContext` and produces deterministic cash inflow, cash outflow,
net cash flow, and cost metrics. It does not calculate ROI, IRR, Allocation, or
Risk.

The second Business Logic Engine is Allocation. It consumes values already
available in `BusinessLogicContext`, groups holdings or positions by asset
category, and produces deterministic total value, category totals, and
allocation weights. It does not calculate ROI, gain/loss, CAGR, IRR, Risk,
rebalancing, recommendations, market prices, API data, or currency conversion.

The first Business Logic assessment engine is Risk. It consumes
`BusinessLogicContext` and produces deterministic `RISK` metric results and
rule-based `SignalResult` objects. It evaluates concentration, liquidity, cash
ratio, diversification, valuation availability, and ledger history
availability. It does not predict markets, perform AI reasoning, fetch external
data, or modify source records.

The Performance Engine computes deterministic unrealized performance from
`BusinessLogicContext`. It produces `PERFORMANCE` metric results for cost
basis, market value, unrealized gain, and unrealized return. ROI, IRR,
Benchmark, and Drawdown engines will extend this capability in later sprints.
It does not perform market prediction, AI reasoning, benchmark comparison, or
advanced return calculations.

### Analytics Engine

Provides derived analytics snapshots for portfolio-level metrics. Analytics
owns snapshots only and stores deterministic outputs produced from validated
lower layers.

Analytics does not modify source data. Dashboard consumes Analytics for
display, and OFAI consumes Analytics and Portfolio context for decisions and
recommendations.

### Service Layer

Provides stable read-only interfaces for CLI, Dashboard, API, Automation, and
OFAI. Services consume existing loaders and models from Ledger, Valuation,
Portfolio, and Analytics.

Services do not own source data and do not mutate underlying files. Future
mutation workflows should go through explicit command or use-case layers.

### Dashboard

Provides display-only views built from Services. Dashboard owns no source data
and does not write to Assets, Ledger, Valuation, Portfolio, Analytics, or data
files. Future web and mobile UI should consume Dashboard views or Services
rather than reading lower-layer files directly.

Dashboard Analytics views present Analytics-derived business intelligence such
as Cash Flow, Allocation, Performance, Risk, and Pipeline summaries. Dashboard
does not calculate metrics. Business Logic owns calculations, Analytics owns
derived snapshots, and Dashboard owns presentation.

### Scenario Engine

Provides deterministic A/B/C/D scenario planning models. Scenario Engine
prepares Base, Upside, Downside, and Stress scenario objects from structured
context. It does not make recommendations, perform AI reasoning, predict
markets, or own source data. OFAI will later reason over Scenario objects.

### OFAI

Provides the orchestration layer for future Onecool Financial AI workflows.
Business Logic calculates, Analytics stores derived snapshots, Dashboard
presents, Scenario Engine structures possibilities, and OFAI prepares decision
context. Future AI models may consume OFAI context, but OFAI does not call AI,
make recommendations, predict markets, or mutate source data in this
foundation.

### Decision Engine

Provides deterministic option evaluation. Decision Engine consumes validated
context from Business Logic, Analytics, Dashboard, Scenario Engine, and OFAI.
It evaluates options, constraints, scores, readiness states, and audit trails.
It does not make final recommendations, call LLMs, predict markets, mutate
source data, provide legal/tax/financial advice as final truth, or execute
actions. Recommendation Engine and LLM integration are future layers.

### Transaction & Ledger Layer

Provides immutable transaction and lifecycle event records for all asset
classes. Transactions record financial changes such as buys, sells, dividends,
interest, deposits, withdrawals, transfers, fees, taxes, splits, merges, and
adjustments. Events record asset lifecycle changes such as listings,
reservations, shipping, grading, property renovations, refinance events, and
valuation updates.

The ledger is the source of truth for asset history. Asset modules should not
own transaction history. Valuation and Portfolio engines will consume validated
ledger data in later sprints.

### Valuation Layer

Provides immutable valuation history records for all asset classes. Valuation
records include source, source priority, currency, value fields, dates,
confidence, notes, URLs, and tags. Multiple valuation records can exist for the
same asset on the same date when they come from different sources.

Collectible valuation mapping records eBay Sold observations as Primary Market
Price inputs and Card Ladder, PWCC, Goldin, Fanatics Collect, and Manual
observations as independent Validation Source inputs.

Runtime valuation providers sit before `ValuationRecord` creation. Providers
own source search, normalization, validation, and non-secret metadata, but they
do not choose final value, mutate imported records, call unauthorized services,
or change Dashboard, Performance, Importer, or Business Logic behavior. The
first provider architecture includes placeholders for Gemini Research Agent,
ChatGPT Research Agent, and Manual runtime valuation so future authorized
providers can plug into the same `ValuationRecord` contract.

Source Agreement evaluates whether Primary Market Price records and Validation
Source records are close, divergent, missing, or conflicting. It produces
`SourceAgreementResult` with deterministic score, level, spread, source count,
missing sources, warnings, and raw valuation IDs. It does not select final
market value, replace eBay Sold, mutate valuation history, predict prices, or
recommend actions.

Investment Performance implements ADR-005 as a reusable runtime layer. Existing
holdings may use imported opening cost basis, historical transaction backfill
is optional, and future transactions are tracked prospectively. The engine
produces `InvestmentPerformanceSnapshot` records with cost basis, market
value, unrealized gain/loss, unrealized gain percent, and holding days. It does
not convert currencies, annualize returns, calculate IRR/XIRR, calculate source
agreement, calculate confidence, recommend actions, or mutate ledger and
valuation history.

Collectible Performance Integration is the first asset-specific adapter for
this layer. PSA/BGS collection records use `My Cost` or normalized `cost` as
opening cost basis. Cost basis stays in the original source currency. The
adapter does not parse notes for TWD or local-currency cost, does not choose a
final valuation source, and does not calculate realized gain/loss.

Performance Dashboard Integration is presentation-only. It consumes
`InvestmentPerformanceSnapshot` records from the Performance layer and exposes
portfolio performance, asset performance tables, deterministic summaries, and
warnings for Collectible Radar. Dashboard does not recalculate performance,
valuation, FX, confidence, source agreement, IRR/XIRR, or recommendations.

Performance Daily Report Integration is also presentation-only. It consumes
Dashboard performance sections and displays performance summary, top gainers,
top losers, and warnings in the Collectible Daily Radar Report. It does not
recalculate performance, realized gain/loss, FX, valuation, confidence, or
recommendations.

Performance Decision Queue Integration consumes the Daily Report performance
summary and warnings. It prioritizes review work for missing cost basis,
missing market value, insufficient data, currency mismatch, and missing holding
dates. It performs no calculations and does not recommend buy/sell actions.

Performance OFAI Context Integration prepares deterministic investment
performance context from the Daily Report and Decision Queue. It exposes
performance overview, top movers, warnings, and review priorities to future
OFAI reasoning. It does not recalculate performance, invoke LLMs, predict
prices, or recommend actions.

The Performance Closed-Loop Review verifies the complete ADR-005 path as a
v0.4 beta candidate. It confirms that the Engine calculates, Collectible
Performance adapts, Dashboard displays, Daily Report assembles, Decision Queue
prioritizes review work, and OFAI prepares deterministic context.

The v0.4.0-beta release preparation freezes this Investment Performance Beta
scope and documents deferred work such as FX, realized gain/loss, lifecycle
sale settlement, IRR/XIRR, annualized return, prediction, and recommendation.

Market Intelligence is the layer that evaluates market data confidence
quality. Market Intelligence v2 consumes optional `SourceAgreementResult`
instead of independently reimplementing source agreement when the result is
provided. It uses agreement score, level, participating sources, missing
sources, and warnings from Source Agreement while keeping backward-compatible
legacy behavior when no Source Agreement result is available. Business Logic
consumes Market Intelligence for deterministic metrics and signals. Dashboard
displays Market Intelligence. Decision consumes Market Intelligence to identify
review readiness and source verification needs.

Collectible Intelligence consumes Market Intelligence and prepares
collectible-specific deterministic signals for Analytics, Dashboard, Decision,
and OFAI. It remains a Business Logic layer and must not become a
Recommendation Engine.

Source priority rules are asset-specific:

- Sports Cards: eBay Sold, Card Ladder, PWCC, Goldin, Fanatics, PSA Estimate,
  Manual.
- Securities: Yahoo, Polygon, Broker, Manual.
- Funds: Fund NAV, Morningstar, Broker, Manual.
- Real Estate: Real Estate Transaction, Bank Valuation, Manual.
- Cash: Broker, Manual.

Manual Valuation Import is an auditable fallback / validation input path. It
loads user-provided CSV or JSON files, validates required valuation fields,
emits `ValuationRecord` objects with source `MANUAL`, and records
`ImportSummary` plus reusable `ImportAudit`. Manual valuations never overwrite
valuation history and never replace eBay Sold as the sports card Primary Market
Price.

Connectors import raw data. Normalize standardizes it. Valuation stores the
resulting valuation records. Portfolio and Dashboard consume valuation records
but do not own them.

### Asset Modules

Represent specific asset classes such as funds, sports cards, real estate,
cash, and gold. Asset modules map their domain models into Portfolio Engine
models while preserving asset-specific metadata and validation.

### Connector Layer

Provides adapters for external platforms, downloaded CSV files, broker exports,
valuation services, and future account sync workflows. Connectors normalize
external data into asset module schemas, transaction records, or valuation
inputs while keeping vendor-specific parsing isolated from asset business
models.

Connector input should live under provider-specific `imports/` directories:

- `imports/psa/`
- `imports/bgs/`
- `imports/ebay/`
- `imports/cardladder/`
- `imports/comc/`

Onecool OS internal normalized portfolio data should live under
`data/portfolio/`, including local files such as `funds.json`,
`securities.json`, `sports_cards.json`, `cash.json`, and `real_estate.json`.

The current connector is the PSA Collection CSV Connector for Sports Cards.
The connector-layer `PSACollectionImporter` is the first production-ready
ingestion foundation. It loads real PSA Collection CSV exports, validates cert
numbers and grades, preserves collection identifiers, and returns normalized
sports card asset records with `ImportSummary` and reusable `ImportAudit`.
It only imports and never calculates valuation, business logic, confidence, or
recommendations. It does not mutate source files, ledger, valuation history, or
production portfolio data. Planned connectors include eBay Orders, Card
Ladder, BGS, and COMC.

eBay Sold Manual Import is the first supported eBay Sold ingestion path. It
loads user-provided CSV or JSON files, validates required source identity and
sale fields, emits `CollectibleMarketRecord` observations with source
`EBAY_SOLD`, and records `ImportSummary` plus reusable `ImportAudit`. It does
not call APIs, scrape websites, add credentials, overwrite valuation history,
select final valuation, calculate confidence, recommend actions, predict
prices, or mutate source files.

Card Ladder Manual Import is the first supported Card Ladder ingestion path.
It loads user-provided CSV or JSON files, validates valuation value, source
identity, and asset identity fields, emits `CollectibleMarketRecord`
observations with source `CARD_LADDER`, and records `ImportSummary` plus
reusable `ImportAudit`. It is a Validation Source path. It never replaces eBay
Sold as Primary Market Price, overwrites valuation history, selects final
valuation, calculates confidence or source agreement, recommends actions,
predicts prices, calls APIs, scrapes websites, adds credentials, or mutates
source files.

### Normalize Layer

Provides canonical normalization contracts between Connectors and downstream
business layers. `BaseNormalizer` defines `source_name()`, `normalize()`, and
`validate()` so connector outputs can be checked before they update Inventory,
Transactions, Valuation inputs, or Allocation inputs.

`NormalizedRecord` represents a canonical connector output with
`external_source`, `external_id`, `record_type`, `payload`, optional
`raw_payload`, and optional `normalized_at`. The Normalize Layer does not own
asset business logic and does not change existing connector behavior.

### Intelligence Engine

Will analyze portfolio state, valuation changes, risk, scenarios, and decision
signals. It must explain its reasoning and depend on existing models instead of
duplicating asset logic.

### Reporting

Will produce summaries, exports, history views, and periodic reports. Reporting
must read from validated models and calculations rather than inventing new
business rules.

### Dashboard

Will provide the daily operating view for status, alerts, valuation, scenarios,
and next actions. Dashboard is a presentation layer and should not own business
logic.

## Roadmap

- v0.1 Core: Core Engine, SQLite persistence, plugin architecture, event bus,
  service registry, and base CLI.
- v0.2 Infrastructure: Configuration, logging, scheduler, and documentation
  foundations.
- v0.3 Market: Market Engine provider framework and initial Yahoo Finance
  provider.
- v0.4 Portfolio: Portfolio Engine, asset normalization, demo portfolio, JSON
  import, and transaction ledger foundation.
- v0.5 Asset Modules: Asset module package foundation, starting with Funds.
- v0.6 Valuation: Universal valuation records, source priority rules,
  valuation inputs, and portfolio aggregation foundation.
- v0.7 Intelligence: Analytics snapshots, scenario analysis, signals, and
  decision support.
- v0.8 Reporting: Reports, exports, summaries, and historical views.
- v0.9 Dashboard: Daily operating dashboard and consolidated status.
- v1.0 Personal Decision Operating System: Integrated daily-use product for
  personal asset decisions.

## Development Workflow

```text
Product Owner
↓
Chief Architect
↓
Specification
↓
Codex Implementation
↓
Tests
↓
Review
↓
Release
```

Product direction starts with the Product Owner. Architecture decisions are
checked by the Chief Architect. Implementation follows the accepted
specification, passes tests, receives review, and is released with a clear
commit history.

## Module Standards

Every module should contain:

- Models
- Engine
- Registry
- Loader
- CLI
- Tests
- Documentation

Modules may omit a component only when the milestone explicitly does not need
it yet. Missing components should be intentional, not accidental.

## Asset Modules

Initial asset module families:

- Funds
- Sports Cards
- Real Estate
- Cash
- Gold

Asset modules should preserve their domain-specific fields while mapping into
the shared Portfolio Engine models for common calculations.

Sports Cards are inventory-style assets. Each card is an individual asset and
must not be aggregated simply because it has the same player, set, or card
number as another card. Future valuation, transactions, grading, and sales
workflows operate on individual card records.

Sports Cards inventory flow:

```text
External Platform
↓
imports/
↓
Connector
↓
Normalizer
↓
data/portfolio/
↓
Inventory
↓
Asset
↓
Transaction
↓
Valuation
```

Inventory extends the Sports Cards asset module. Each inventory item represents
one physical graded card and may track certificate number, quantity state,
storage location, and last inventory update. Inventory does not redesign the
Portfolio Engine and does not replace immutable transaction records.

Default sports card valuation source priority:

1. eBay Sold
2. Card Ladder
3. PWCC
4. Goldin
5. Fanatics
6. Manual

## Versioning Rules

Onecool OS follows Semantic Versioning.

- Major versions introduce product-level compatibility boundaries.
- Minor versions introduce milestones and new functional areas.
- Patch versions fix defects or add narrow, backward-compatible improvements.

Every release should update documentation and tests when behavior changes.

## Coding Principles

Keep modules small.

Prefer composition over inheritance.

Avoid unnecessary abstractions.

Prioritize readability.
