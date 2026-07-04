# Changelog

All notable changes to Onecool OS will be documented in this file.

The format follows Keep a Changelog principles, and commits follow Conventional
Commits.

## [Unreleased]

### Added

- Collectible Radar MVP ADR.
- Collectible connector foundation for local eBay Sold, Card Ladder, PWCC,
  Goldin, and Fanatics Collect records.
- Collectible source role mapping for Primary Market Price, Validation Source,
  and Manual Fallback.
- Collectible Valuation Mapper from `CollectibleMarketRecord` to
  `ValuationRecord` plus source metadata.
- Market Intelligence foundation with confidence, agreement, coverage,
  freshness, liquidity, warnings, and deterministic `reference_datetime`.
- v0.2.0 Beta architecture freeze documentation.
- Decision Platform architecture for Business Logic, Analytics, Dashboard,
  Scenario, OFAI, and Decision responsibilities.
- Decision Engine foundation with deterministic options, candidates,
  constraints, scores, readiness states, results, and audit trails.
- Cash Flow Engine as the first Business Logic Engine.
- Business Logic Pipeline Runner for deterministic engine orchestration.
- Analytics Integration mapping from Business Logic pipeline results to
  AnalyticsSnapshot-compatible payloads.
- Dashboard Analytics views for Cash Flow, Allocation, Performance, Risk, and
  Pipeline summaries.
- Scenario Engine foundation with deterministic A/B/C/D scenario models,
  validation, and builder.
- OFAI foundation with deterministic context, plan model, planner, validation,
  and planning enums.
- Structured pipeline execution reports with engine results, signal results,
  executed engines, skipped engines, and errors.
- Allocation Engine as a deterministic Business Logic Engine.
- Risk Engine as the first deterministic Business Logic assessment engine.
- Performance Engine for deterministic unrealized performance metrics.
- Cost basis, market value, unrealized gain, and unrealized return results
  from `BusinessLogicContext`.
- Risk signals for concentration, liquidity, cash ratio, diversification,
  missing valuation data, and missing ledger history.
- Portfolio category totals and weights from values already available in
  `BusinessLogicContext`.
- Deterministic cash inflow, cash outflow, net cash flow, and cost summaries
  from Ledger data.
- Business Logic foundation under `onecool_os.business_logic`.
- Business logic context, metric results, signal results, calculator and
  evaluator contracts, policies, and registry.
- v0.1.0 Alpha architecture freeze documentation.
- Alpha release notes under `docs/releases/v0.1.0-alpha.md`.
- Dashboard foundation under `onecool_os.dashboard`.
- Display-only dashboard view and section models, builder, and CLI demo.
- Service Layer foundation under `onecool_os.services`.
- Read-only Ledger, Valuation, Portfolio, and Analytics services for future
  CLI, Dashboard, API, Automation, and OFAI workflows.
- Analytics Engine foundation under `onecool_os.analytics`.
- Immutable analytics snapshots, risk and metric enums, validation, and JSON
  loader support.
- Demo analytics book under `data/analytics/analytics.example.json`.
- Portfolio aggregation foundation with holdings, summary fields, validation,
  and JSON loader support.
- Demo aggregation portfolio template under
  `data/portfolio/portfolio.example.json`.
- Universal valuation platform under `onecool_os.valuation`.
- Immutable valuation history records, source and confidence enums, source
  priority rules, and valuation JSON loader.
- Demo valuation book under `data/valuation/valuation.example.json`.
- Transaction and Ledger foundation with immutable `Transaction` and `Event`
  records.
- Shared `TransactionType`, `TransactionStatus`, and `EventType` enums.
- Ledger JSON loader with transaction and event validation.
- Demo ledger template under `data/transactions/ledger.example.json`.
- Official project roadmap and version planning documentation.
- Canonical Normalize Layer foundation under
  `onecool_os.connectors.normalize`.
- `BaseNormalizer` and `NormalizedRecord` contracts for connector output.
- Repository import layout under `imports/` for raw external platform exports.
- Documentation separating raw imports from normalized `data/portfolio/` files.
- Sports Cards inventory foundation with inventory IDs, certificate numbers,
  quantity state, storage metadata, and last inventory update.
- Connector Layer documentation in the master specification and README.
- PSA Collection CSV Connector documentation for Sports Cards.
- Shared transaction framework under `onecool_os.transactions`.
- Immutable base transaction records, transaction type enum, transaction
  registry, and JSON loader.
- Demo transaction template under `data/transactions/transactions.example.json`.
- Securities asset module foundation under `onecool_os.assets.securities`.
- Securities JSON loader and interactive portfolio creator.
- Securities CLI commands for local import and portfolio file creation.
- Interactive `python -m onecool_os funds create` wizard for local real fund
  portfolio files.
- Real fund portfolio import support from local `data/portfolio/funds.json`.
- Template-only fund portfolio file at `data/portfolio/funds.example.json`.
- Funds import validation for duplicate asset IDs and optional current prices.
- Modular CLI handlers under `onecool_os.cli`.
- CLI delegation tests for core and module commands.
- Shared asset base models under `onecool_os.assets.base`.
- Asset standard tests for Funds, Sports Cards, Real Estate, and Cash.
- Cash / FX asset module foundation under `onecool_os.assets.cash`.
- Cash asset and position models with JSON loader validation.
- Cash demo CLI command for sample cash balance data.
- Example cash JSON file under `examples/`.
- Real Estate asset module foundation under `onecool_os.assets.real_estate`.
- Real estate asset and position models with JSON loader validation.
- Real estate demo CLI command for sample property data.
- Example real estate JSON file under `examples/`.
- Sports Cards asset module foundation under
  `onecool_os.assets.sports_cards`.
- Card asset and position models with JSON loader validation.
- Cards demo CLI command for sample card data.
- Example sports cards JSON file under `examples/`.
- Master project specification under `docs/master-spec.md`.
- Project documentation under `docs/`.
- Architecture Decision Record for Core Engine architecture choices.
- Contributing workflow documentation.

## [0.6.1] - 2026-06-30

### Added

- Allocation Engine foundation under `onecool_os.intelligence.allocation`.
- Allocation calculations from normalized `ValuationResult` records.
- Allocation demo CLI command with mocked valuation results.

## [0.6.0] - 2026-06-30

### Added

- Valuation Engine foundation under `onecool_os.intelligence.valuation`.
- Demo valuator with mocked values for Funds, Sports Cards, Real Estate, and
  Cash.
- Valuation demo CLI command.

## [0.5.0] - 2026-06-29

### Added

- Funds asset module foundation under `onecool_os.assets.funds`.
- Fund asset and position models mapped to existing Portfolio primitives.
- Funds JSON loader with validation for missing fields, asset type, quantity,
  and invalid JSON.
- Funds import CLI command for sample fund data.
- Example funds JSON file under `examples/`.

## [0.4.3] - 2026-06-29

### Added

- Portfolio JSON import demo using the existing in-memory Portfolio models.
- `PortfolioLoader` validation for required fields, asset types, quantities,
  and invalid JSON.
- Portfolio import CLI summary output.
- Example portfolio JSON file under `examples/`.

## [0.4.2] - 2026-06-29

### Changed

- Normalized Portfolio `Asset` model with a separate `symbol` field.
- Added asset type validation.
- Updated portfolio demo output to categorize SPY, QQQ, and GLD as `ETF`.

## [0.4.1] - 2026-06-29

### Added

- In-memory Portfolio CLI demo with sample SPY, QQQ, and GLD positions.
- Demo output for market value, total cost, and unrealized PnL.
- Tests confirming the demo requires no network or file writes.

## [0.4.0] - 2026-06-29

### Added

- Portfolio Engine foundation package.
- Generic Asset, Position, Portfolio, and PortfolioRegistry models.
- Portfolio Engine CLI status command.
- Portfolio foundation tests.

## [0.3.2] - 2026-06-29

### Added

- Manual Yahoo Finance fetch validation workflow.
- Safe validation output with status and error details.
- Tests for mocked success, invalid symbols, network failures, and secret-safe
  output.

## [0.3.1] - 2026-06-29

### Added

- Yahoo Finance market provider backed by `yfinance`.
- Normalized `SPY` fetch support.
- Market fetch CLI command.
- Market provider configuration.
- Yahoo Finance provider tests with mocked yfinance calls.

## [0.3.0] - 2026-06-29

### Added

- Market Engine foundation package.
- Market provider abstraction and provider registry.
- Built-in `MockProvider` for local development and tests.
- Market Engine CLI status command.
- Market Engine tests.

## [0.2.2] - 2026-06-29

### Added

- Lightweight Scheduler System.
- Manual, daily, weekly, and monthly job support.
- Built-in `core.health` scheduler job.
- Scheduler CLI commands for listing and running jobs.
- Scheduler tests.

## [0.2.1] - 2026-06-29

### Added

- Centralized logging system with system and module-specific loggers.
- Rotating file log support with console output.
- Logging CLI status command.
- Logging tests.

## [0.2.0] - 2026-06-29

### Added

- Centralized configuration files under `config/`.
- Configuration loader with default settings, user overrides, environment
  overrides, validation, and safe handling of missing optional files.
- Sanitized `python -m onecool_os config` CLI output.
- Config System tests.

## [0.1.0] - 2026-06-28

### Added

- Core Engine lifecycle.
- SQLite persistence and migrations.
- Plugin Architecture.
- Event Bus with persistent event log.
- Service Registry.
- Built-in `core.health` plugin.
- CLI commands for initialization, status, and plugin listing.
- Test coverage for database migrations, engine lifecycle, and plugins.
