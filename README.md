# Onecool OS

Onecool OS is a Python-based personal asset operating system. Milestone 1
delivers the Core Engine: SQLite persistence, plugin loading, event publishing,
service registration, and a command-line entry point.

## Project Overview

Onecool OS models personal assets, tracks portfolio value, validates market and
asset data, and prepares the system for valuation, intelligence, reporting, and
dashboard workflows. The official product specification is maintained in
[docs/master-spec.md](docs/master-spec.md).

## Requirements

- Python 3.11+
- SQLite, included with Python

Install development dependencies:

```bash
python -m pip install -r requirements.txt
```

## Quick Start

Initialize the local database:

```bash
python -m onecool_os init
```

Check engine status:

```bash
python -m onecool_os status
```

List loaded plugins:

```bash
python -m onecool_os plugins
```

Show sanitized configuration:

```bash
python -m onecool_os config
```

Inspect logging status:

```bash
python -m onecool_os logs
```

List scheduler jobs:

```bash
python -m onecool_os scheduler list
```

Run a scheduler job manually:

```bash
python -m onecool_os scheduler run core.health
```

Show Market Engine status:

```bash
python -m onecool_os market status
```

Fetch market data:

```bash
python -m onecool_os market fetch SPY --provider yahoo
```

Validate market data fetch:

```bash
python -m onecool_os market validate SPY --provider yahoo
```

Show Portfolio Engine status:

```bash
python -m onecool_os portfolio status
```

Show Portfolio CLI demo:

```bash
python -m onecool_os portfolio demo
```

Load the demo portfolio from JSON:

```bash
python -m onecool_os portfolio import examples/portfolio_demo.json
```

Load sample funds from JSON:

```bash
python -m onecool_os funds import examples/funds_demo.json
```

Show sample sports cards:

```bash
python -m onecool_os cards demo
```

Run tests:

```bash
python -m pytest
```

## Configuration

Onecool OS loads configuration from `config/settings.yaml`, optional
`config/user.yaml`, and environment variables. Missing `config/user.yaml` and
`config/secrets.yaml` files are safe and do not stop startup.

Configuration precedence:

1. Default settings in `config/settings.yaml`
2. User overrides in `config/user.yaml`
3. Environment variables

Required configuration sections:

- `app`: `name`, `version`, `timezone`, `language`
- `database`: `path`
- `paths`: `data_dir`, `cache_dir`, `logs_dir`, `exports_dir`
- `runtime`: `debug`, `environment`

`config/user.yaml` is for local user preferences and should not contain
credentials. `config/secrets.example.yaml` documents supported secret
placeholders; copy it to a local `config/secrets.yaml` when needed and do not
commit real secrets.

The `python -m onecool_os config` command prints sanitized configuration and
does not include secrets.

Environment variables:

- `ONECOOL_OS_DB_PATH`: SQLite database path. Defaults to
  `database.path` from configuration. This legacy variable remains supported.
- `ONECOOL_OS_DATABASE_PATH`: SQLite database path.
- `ONECOOL_OS_CONFIG_DIR`: Configuration directory. Defaults to `config`.
- `ONECOOL_OS_APP_NAME`, `ONECOOL_OS_APP_VERSION`, `ONECOOL_OS_TIMEZONE`,
  `ONECOOL_OS_LANGUAGE`: Application settings.
- `ONECOOL_OS_DATA_DIR`, `ONECOOL_OS_CACHE_DIR`, `ONECOOL_OS_LOGS_DIR`,
  `ONECOOL_OS_EXPORTS_DIR`: Runtime paths.
- `ONECOOL_OS_DEBUG`, `ONECOOL_OS_ENVIRONMENT`: Runtime behavior.
- `ONECOOL_OS_LOG_LEVEL`: Logging level. Supported values are `DEBUG`, `INFO`,
  `WARNING`, `ERROR`, and `CRITICAL`.
- `ONECOOL_OS_PLUGIN_PATHS`: Additional plugin directories separated by the OS
  path separator.

## Logging

Onecool OS provides centralized logging through `onecool_os.core.logging`.
Logging uses the configured `paths.logs_dir`, creates the directory safely when
missing, writes rotating file logs, and also emits console output.

Default log files:

- `logs/system.log`
- `logs/market.log`
- `logs/decision.log`

The current log level comes from `logging.level` when configured. If no explicit
logging level is set, `runtime.debug: true` enables `DEBUG`; otherwise the
default is `INFO`.

Inspect logging configuration and available log files:

```bash
python -m onecool_os logs
```

## Scheduler

Onecool OS includes a lightweight scheduler in `onecool_os.core.scheduler`.
The scheduler supports registering jobs, listing jobs, running a job manually,
safe error handling, and logging execution through the centralized Logging
System.

Supported schedule types:

- `manual`
- `daily`
- `weekly`
- `monthly`

Every job includes:

- `job_id`
- `name`
- `schedule_type`
- `enabled`
- `last_run_at`
- `next_run_at`
- `status`
- `error_message`

The built-in `core.health` job verifies Core Engine health and writes a log
entry.

List jobs:

```bash
python -m onecool_os scheduler list
```

Run a job manually:

```bash
python -m onecool_os scheduler run core.health
```

## Market Engine

Onecool OS includes a lightweight Market Engine foundation in
`onecool_os.market`. The Market Engine is provider-based so future market data
sources can plug in without changing core infrastructure.

Current Market Engine components:

- `MarketEngine`: Coordinates market providers.
- `MarketProvider`: Abstract provider interface.
- `ProviderRegistry`: Registers and retrieves providers.
- `MockProvider`: Built-in mock provider for local development and tests.

Provider interface:

- `connect()`
- `health_check()`
- `fetch()`
- `disconnect()`

The built-in `MockProvider` returns simple mock market data only. No real market
data provider or external API is implemented in this sprint.

### Yahoo Finance Provider

Onecool OS includes a Yahoo Finance provider backed by `yfinance`. The initial
supported symbol is `SPY`.

Yahoo Finance output is normalized with:

- `symbol`
- `provider`
- `last_price`
- `currency`
- `timestamp`
- `raw`

The provider is configured through `config/settings.yaml`:

```yaml
market:
  default_provider: yahoo
  providers:
    yahoo:
      enabled: true
```

Fetch SPY:

```bash
python -m onecool_os market fetch SPY --provider yahoo
```

### Manual Market Validation

Use the validation command to manually verify that the Yahoo Finance provider can
fetch `SPY` safely:

```bash
python -m onecool_os market validate SPY --provider yahoo
```

The validation command prints normalized data and always includes:

- `symbol`
- `provider`
- `last_price`
- `currency`
- `timestamp`
- `status`
- `error_message`

Validation handles missing dependencies, network/API failures, invalid symbols,
and empty responses without exposing secrets.

Show Market Engine status:

```bash
python -m onecool_os market status
```

## Portfolio Foundation

Onecool OS includes a lightweight Portfolio Engine foundation in
`onecool_os.portfolio`. It provides shared portfolio primitives for future asset
classes without implementing any specific asset class or database persistence in
this sprint.

Current Portfolio components:

- `PortfolioEngine`: Coordinates portfolio status.
- `PortfolioRegistry`: Creates and retrieves portfolios.
- `Portfolio`: Holds positions.
- `Asset`: Generic asset metadata.
- `Position`: Quantity, cost, optional current price, market value, and
  unrealized PnL.

Asset model:

- `asset_id`: Internal asset identifier.
- `symbol`: Tradable or display symbol when available.
- `asset_type`: Normalized asset category.
- `name`: Human-readable asset name.
- `currency`: Asset currency.

Supported asset types:

- `ETF`
- `MUTUAL_FUND`
- `STOCK`
- `SPORTS_CARD`
- `REAL_ESTATE`
- `GOLD`
- `CASH`
- `CRYPTO`
- `OTHER`

Portfolio status:

```bash
python -m onecool_os portfolio status
```

### Portfolio CLI Demo

The portfolio demo creates a hardcoded in-memory portfolio with sample `SPY`,
`QQQ`, and `GLD` positions. It does not fetch live prices, write files, or use
database persistence.

The demo uses normalized assets where `symbol` is the ticker and `asset_type`
is the category. `SPY`, `QQQ`, and `GLD` are categorized as `ETF`.

Run the demo:

```bash
python -m onecool_os portfolio demo
```

The output includes position quantities, average costs, current prices, market
values, unrealized PnL, total cost, total market value, and total unrealized PnL.

### Portfolio JSON Import Demo

Portfolio JSON import loads a demo portfolio into memory from a local JSON file.
It validates the payload, prints a summary, and does not write to disk or use
database persistence.

Run the import demo:

```bash
python -m onecool_os portfolio import examples/portfolio_demo.json
```

The JSON root must include:

- `portfolio_name`
- `positions`

Each position must include:

- `asset_id`
- `symbol`
- `asset_type`
- `name`
- `currency`
- `quantity`
- `average_cost`
- `current_price`

The import command validates missing fields, invalid JSON, unsupported
`asset_type` values, and invalid quantities. Output includes `Portfolio
Summary`, total cost, total market value, and total unrealized PnL.

## Funds Module

Onecool OS includes a Funds asset module foundation in
`onecool_os.assets.funds`. The module maps fund-specific models into the shared
Portfolio primitives and does not fetch live NAV data, call external APIs, or
write to database storage.

Current Funds components:

- `FundAsset`: Mutual fund metadata mapped to Portfolio `Asset`.
- `FundPosition`: Quantity, cost, optional current price, market value, and
  unrealized PnL.
- `FundLoader`: JSON loader for sample fund holdings.

`FundAsset` always maps to:

- `asset_type`: `MUTUAL_FUND`

Optional fund metadata:

- `fund_house`
- `region`
- `theme`

Run the funds import demo:

```bash
python -m onecool_os funds import examples/funds_demo.json
```

The funds JSON root must include:

- `funds`

Each fund must include:

- `asset_id`
- `symbol`
- `asset_type`
- `name`
- `currency`
- `quantity`
- `average_cost`
- `current_price`

The import command validates missing fields, invalid JSON, unsupported
`asset_type` values, and invalid quantities. Output includes the fund list,
total cost, total market value, and total unrealized PnL.

## Sports Cards Module

Onecool OS includes a Sports Cards asset module foundation in
`onecool_os.assets.sports_cards`. The module is model-first and does not
implement Card Ladder, eBay integration, valuation, OCR, image processing, or
database persistence.

Current Sports Cards components:

- `CardAsset`: Player, sport, set, card number, grader, grade, parallel, serial
  number, and currency.
- `CardPosition`: Quantity, purchase price, purchase date, and notes.
- `CardLoader`: JSON loader for sample card holdings.

Run the cards demo:

```bash
python -m onecool_os cards demo
```

The cards JSON root must include:

- `cards`

Each card must include:

- `asset_id`
- `player`
- `sport`
- `year`
- `brand`
- `set`
- `card_number`
- `grader`
- `grade`
- `parallel`
- `serial_number`
- `currency`
- `quantity`
- `purchase_price`
- `purchase_date`
- `notes`

The demo command validates missing fields, invalid JSON, invalid grades, and
invalid quantities. Output includes player, card, grade, quantity, and purchase
price.

## Project Structure

```text
.
├── examples
│   ├── cards_demo.json
│   ├── funds_demo.json
│   └── portfolio_demo.json
├── docs
│   ├── architecture.md
│   ├── coding-standard.md
│   ├── decision-records
│   ├── master-spec.md
│   └── roadmap.md
├── config
│   ├── settings.yaml
│   ├── user.yaml
│   └── secrets.example.yaml
├── migrations
├── onecool_os
│   ├── assets
│   ├── core
│   ├── market
│   ├── portfolio
│   └── plugins
├── logs
├── tests
├── CHANGELOG.md
├── CONTRIBUTING.md
├── README.md
├── pyproject.toml
└── requirements.txt
```

## Architecture

Milestone 1 keeps the architecture intentionally small and modular:

- `onecool_os.core.engine`: Starts and stops the Core Engine.
- `onecool_os.core.database`: Manages SQLite connections and schema migrations.
- `onecool_os.core.plugins`: Loads built-in and external plugins.
- `onecool_os.core.events`: Publishes in-process events and persists them.
- `onecool_os.core.registry`: Registers shared services for plugins.

Future modules such as Market, Funds, Cards, House, Emergency, and Dashboard
should be added as plugins that depend on the public Core Engine interfaces.

## Plugin Contract

A plugin exposes a callable named `create_plugin` that returns an object with:

- `manifest`: a `PluginManifest`
- `activate(context)`: called when the engine starts
- `deactivate(context)`: called when the engine stops

External plugin directories may contain Python modules or packages. Plugin
packages can include a `plugin.json` file:

```json
{
  "module": "my_plugin",
  "enabled": true
}
```

The module still owns its runtime manifest through `create_plugin`.

## Documentation

- [Master Specification](docs/master-spec.md)
- [Architecture](docs/architecture.md)
- [Coding Standard](docs/coding-standard.md)
- [Core Engine ADR](docs/decision-records/ADR-001-Core-Engine.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## Product Roadmap

The roadmap is maintained in [docs/roadmap.md](docs/roadmap.md). Current
direction keeps Core Engine infrastructure independent from business modules and
adds future areas such as Market, Funds, Cards, House, Emergency, and Dashboard
as modular extensions.
