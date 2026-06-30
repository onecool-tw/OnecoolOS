# Changelog

All notable changes to Onecool OS will be documented in this file.

The format follows Keep a Changelog principles, and commits follow Conventional
Commits.

## [Unreleased]

### Added

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
