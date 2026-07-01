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
Connector
↓
Assets
↓
Transactions
↓
Valuation
↓
Allocation
↓
Risk
↓
Scenario
↓
Decision
```

Connectors import or sync data from external platforms and local exports. They
translate platform-specific files, APIs, or account views into Onecool OS
formats without owning business logic.

Assets describe what the user owns. They preserve identity, category,
metadata, and ownership-specific fields for each asset class.

Transactions record what happened. They are immutable event records used to
derive portfolio state over time.

Valuation estimates worth. It consumes assets, positions, market data, and
connector-provided context to produce explainable valuation results.

Allocation analyzes distribution. It uses valuation outputs to describe where
capital is concentrated across assets, categories, currencies, and accounts.

Risk, Scenario, and Decision layers build on validated asset, transaction,
valuation, and allocation data. They must not bypass the lower layers.

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

Provides shared asset, position, portfolio, registry, and loader primitives.
Portfolio Engine owns common valuation math such as cost basis, market value,
and unrealized PnL.

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

The current connector is the PSA Collection CSV Connector for Sports Cards.
Planned connectors include eBay Orders, Card Ladder, BGS, and COMC.

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
- v0.4 Portfolio: Portfolio Engine, asset normalization, demo portfolio, and
  JSON import.
- v0.5 Asset Modules: Asset module package foundation, starting with Funds.
- v0.6 Valuation: Shared valuation services, valuation inputs, and valuation
  summaries.
- v0.7 Intelligence: Scenario analysis, signals, and decision support.
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
Connector
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
