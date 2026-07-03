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
Dashboard / CLI / API / Automation / OFAI
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

`imports/` contains raw files exported from external platforms. Raw imports are
not Onecool OS internal data and should not be committed when they contain user
portfolio information.

The Canonical Normalize Layer converts connector input into
`NormalizedRecord` objects before data becomes asset, inventory, or transaction
state. Normalized user portfolio data belongs in `data/portfolio/`.

Assets describe what the user owns. They preserve identity, category,
metadata, and ownership-specific fields for each asset class.

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

OFAI builds decisions and recommendations on validated lower-layer data. It
must not bypass Connector, Normalize, Asset, Ledger, Valuation, or Portfolio
records.

### Source of Truth

| Layer | Owns |
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

The first Business Logic Engine is Cash Flow. It consumes Ledger data through
`BusinessLogicContext` and produces deterministic cash inflow, cash outflow,
net cash flow, and cost metrics. It does not calculate ROI, IRR, Allocation, or
Risk.

The second Business Logic Engine is Allocation. It consumes values already
available in `BusinessLogicContext`, groups holdings or positions by asset
category, and produces deterministic total value, category totals, and
allocation weights. It does not calculate ROI, gain/loss, CAGR, IRR, Risk,
rebalancing, recommendations, market prices, API data, or currency conversion.

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

Source priority rules are asset-specific:

- Sports Cards: eBay Sold, Card Ladder, PWCC, Goldin, Fanatics, PSA Estimate,
  Manual.
- Securities: Yahoo, Polygon, Broker, Manual.
- Funds: Fund NAV, Morningstar, Broker, Manual.
- Real Estate: Real Estate Transaction, Bank Valuation, Manual.
- Cash: Broker, Manual.

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
Planned connectors include eBay Orders, Card Ladder, BGS, and COMC.

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
