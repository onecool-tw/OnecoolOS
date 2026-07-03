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

Import a PSA Collection CSV into the local sports cards portfolio:

```bash
python -m onecool_os cards import-csv imports/psa/psa_collection.csv
```

Show sample real estate:

```bash
python -m onecool_os real-estate demo
```

Show sample cash balances:

```bash
python -m onecool_os cash demo
```

Show mocked valuation results:

```bash
python -m onecool_os valuation demo
```

Show mocked allocation results:

```bash
python -m onecool_os allocation demo
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

## Portfolio Aggregation Foundation

Onecool OS includes a lightweight Portfolio Aggregation foundation in
`onecool_os.portfolio`. Portfolio is not the owner of source data. It
aggregates information from Assets, Ledger, and Valuation so downstream
surfaces can read a current portfolio view.

Portfolio owns no transaction history, no valuation history, and no asset
identity. Those responsibilities stay with Ledger, Valuation, and Assets.

Current Portfolio components:

- `PortfolioEngine`: Coordinates portfolio status.
- `PortfolioRegistry`: Creates and retrieves portfolios.
- `Portfolio`: Aggregates holdings and summary values.
- `Asset`: Generic asset metadata.
- `Position`: Quantity, cost, optional current price, market value, and
  unrealized PnL.
- `Holding`: Aggregation reference to an asset with quantity, optional average
  cost, and optional market value.
- `PortfolioInputLayer`: Documents the consumed layers: Assets, Ledger, and
  Valuation.

Aggregation portfolio JSON uses this shape:

```json
{
  "portfolio_name": "Onecool Portfolio",
  "base_currency": "TWD",
  "holdings": []
}
```

A demo aggregation template is provided at
`data/portfolio/portfolio.example.json`. It contains only sample holdings and
no real user data.

Future Analytics Engine responsibilities:

- ROI
- IRR
- Allocation
- Risk
- Cash Flow

Portfolio itself should remain calculation-light.

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

### Preparing Your Real Portfolio

User-owned portfolio data belongs under `data/` and should not be committed to
GitHub. A template is provided at `data/portfolio/funds.example.json`.

Prepare a local real funds file:

```bash
cp data/portfolio/funds.example.json data/portfolio/funds.json
```

Then edit `data/portfolio/funds.json` locally and import it:

```bash
python -m onecool_os funds import data/portfolio/funds.json
```

You can also create or update the local file with the interactive wizard:

```bash
python -m onecool_os funds create
```

When `data/portfolio/funds.json` already exists, the wizard lets you append a
new fund, replace the portfolio, or cancel without changing the file.

If `data/portfolio/funds.json` does not exist, the CLI prints a friendly
message that points back to the example template. The real local file is ignored
by Git.

Real funds JSON must include:

- `portfolio_name`
- `positions`

Each position must include:

- `asset_id`
- `symbol`
- `name`
- `currency`
- `quantity`
- `average_cost`

Optional fields:

- `fund_house`
- `theme`
- `region`
- `notes`

`current_price` is not required for real fund imports. Current valuation will
come from the Valuation Engine later.

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

## Securities Module

Onecool OS includes a Securities asset module foundation in
`onecool_os.assets.securities`. The module supports listed securities such as
US stocks, US ETFs, Taiwan stocks, Taiwan ETFs, and other listed securities.
It does not fetch live stock prices, call Yahoo Finance, change valuation logic,
or write to database persistence.

Current Securities components:

- `SecurityAsset`: Listed security metadata.
- `SecurityPosition`: Quantity, average cost, optional purchase date, and notes.
- `SecurityLoader`: JSON loader for local securities portfolio files.
- `SecurityCreator`: Interactive CLI creator for local securities data.

Supported security asset types:

- `STOCK`
- `ETF`
- `OTHER`

Supported markets:

- `US`
- `TW`
- `OTHER`

A template is provided at `data/portfolio/securities.example.json`. Real user
holdings belong in `data/portfolio/securities.json` and are ignored by Git.

Import local securities:

```bash
python -m onecool_os securities import data/portfolio/securities.json
```

Create or update the local securities file interactively:

```bash
python -m onecool_os securities create
```

The import output includes security name, symbol, market, asset type, quantity,
average cost, and total cost.

## Connector Layer

Onecool OS uses a Connector Layer to import or sync data from external
platforms without putting vendor-specific parsing inside asset models,
transactions, valuation, or allocation logic.

Connector flow:

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
Transactions
↓
Valuation
↓
Allocation
```

Raw exported files belong under `imports/`. Onecool OS normalized local data
belongs under `data/portfolio/`.

Recommended raw import directories:

- `imports/psa/`
- `imports/bgs/`
- `imports/ebay/`
- `imports/cardladder/`
- `imports/comc/`

Recommended normalized portfolio files:

- `data/portfolio/funds.json`
- `data/portfolio/securities.json`
- `data/portfolio/sports_cards.json`
- `data/portfolio/cash.json`
- `data/portfolio/real_estate.json`

Connectors translate external files, APIs, or account exports into Onecool OS
schemas. Asset modules describe what the user owns, Transactions record what
happened, Valuation estimates worth, and Allocation analyzes distribution.

### Normalize Layer

The Canonical Normalize Layer lives under
`onecool_os.connectors.normalize`. It sits between Connectors and downstream
business layers and defines:

- `NormalizedRecord`: Canonical connector output with external source,
  external ID, record type, payload, optional raw payload, and normalization
  time.
- `BaseNormalizer`: Interface for `source_name()`, `normalize()`, and
  `validate()`.

The Normalize Layer validates connector output shape. It does not change
existing connector behavior, own asset business logic, or write portfolio data
by itself.

Current connector:

- PSA Collection CSV Connector

Planned connectors:

- eBay Orders Connector
- Card Ladder Connector
- BGS Connector
- COMC Connector

Recommended PSA workflow:

```text
1. Export PSA Collection
↓
2. Save the raw CSV under imports/psa/
↓
3. Run python -m onecool_os cards import-csv imports/psa/<file>.csv
↓
4. data/portfolio/sports_cards.json is updated
```

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
- `PsaCsvImporter`: PSA Collection CSV Connector for local PSA exports.

Run the cards demo:

```bash
python -m onecool_os cards demo
```

Import the local live sports cards portfolio:

```bash
python -m onecool_os cards import data/portfolio/sports_cards.json
```

Import a PSA Collection CSV without overwriting existing cards:

```bash
python -m onecool_os cards import-csv imports/psa/psa_collection.csv
```

The PSA Collection CSV Connector maps `Item`, `Subject`, `Year`, `Set`,
`Card Number`, `Grade Issuer`, `Grade`, `Cert Number`, `My Cost`,
`Date Acquired`, `Source`, and `My Notes` into the Sports Cards live portfolio
schema. Duplicate cards are detected by `Cert Number`.

Sports Cards are inventory-style assets: each card is an individual asset.
Cards are not aggregated simply because they share the same player, set, or
card number. Future valuation, transactions, grading, and sales workflows will
operate on individual card records.

### Sports Cards Inventory Layer

The Sports Cards Inventory Layer extends the Sports Cards asset module without
redesigning Portfolio. Each inventory item represents one physical graded card.

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

Inventory records can track:

- `inventory_id`
- `cert_number`
- `owned_quantity`
- `available_quantity`
- `listed_quantity`
- `sold_quantity`
- `location`
- `cabinet`
- `box`
- `row`
- `slot`
- `last_inventory_update`

Supported inventory statuses:

- `Owned`
- `Listed`
- `Reserved`
- `Grading`
- `Shipping`
- `Sold`

Storage metadata is optional. Use `cabinet`, `box`, `row`, and `slot` only when
the card has a known storage location.

The live sports cards portfolio supports common fields shared with Funds and
Securities:

- `account`
- `asset_class`
- `status`
- `currency`
- `base_currency`
- `cost`

Supported card statuses:

- `Owned`
- `Listed`
- `Sold`
- `Grading`
- `Shipping`
- `Reserved`

Supported collection types:

- `Core`
- `Investment`
- `Trading`
- `PC`

Default sports card valuation source priority:

1. `eBay Sold`
2. `Card Ladder`
3. `PWCC`
4. `Goldin`
5. `Fanatics`
6. `Manual`

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

## Real Estate Module

Onecool OS includes a Real Estate asset module foundation in
`onecool_os.assets.real_estate`. The module is model-first and does not
implement live real estate APIs, valuation engine, mortgage calculator, or
database persistence.

Current Real Estate components:

- `RealEstateAsset`: Property identity, location, property type, area, building
  age, floor information, parking flag, and currency.
- `RealEstatePosition`: Quantity, purchase price, purchase date, optional
  current estimated value, and notes.
- `RealEstateLoader`: JSON loader for sample property holdings.

Run the real estate demo:

```bash
python -m onecool_os real-estate demo
```

The real estate JSON root must include:

- `properties`

Each property must include:

- `asset_id`
- `asset_type`
- `name`
- `country`
- `city`
- `district`
- `address_label`
- `property_type`
- `currency`
- `area_ping`
- `building_age_years`
- `floor`
- `total_floors`
- `has_parking`
- `quantity`
- `purchase_price`
- `purchase_date`
- `current_estimated_value`
- `notes`

The demo command validates missing fields, invalid JSON, invalid area, and
invalid price. Output includes property name, city/district, property type,
area, purchase price, current estimated value, and unrealized PnL.

## Cash / FX Module

Onecool OS includes a Cash / FX asset module foundation in
`onecool_os.assets.cash`. The module is model-first and does not implement live
FX APIs, valuation engine, or database persistence.

Current Cash / FX components:

- `CashAsset`: Cash account identity, currency, account type, optional
  institution, and optional country.
- `CashPosition`: Amount, currency, optional FX rate to base currency, base
  currency, and notes.
- `CashLoader`: JSON loader for sample cash balances.

Run the cash demo:

```bash
python -m onecool_os cash demo
```

The cash JSON root must include:

- `cash_accounts`

Each cash account must include:

- `asset_id`
- `asset_type`
- `name`
- `currency`
- `account_type`
- `amount`
- `fx_rate_to_base`
- `base_currency`
- `notes`

Optional cash account metadata:

- `institution`
- `country`

The demo command validates missing fields, invalid JSON, invalid amount,
invalid currency, and invalid FX rate. Output includes cash account, currency,
amount, FX rate to base, and base currency value.

## Asset Standard

Onecool OS defines shared asset base models in `onecool_os.assets.base`.
`BaseAsset` establishes the minimum fields all asset modules should expose:

- `asset_id`
- `asset_type`
- `name`
- `currency`
- `created_at`
- `updated_at`

`BasePosition` establishes the minimum position contract:

- `asset`
- `notes`

Specific modules keep their own position structures because Funds, Sports
Cards, Real Estate, and Cash do not share identical quantity, cost, or valuation
fields yet. This keeps the model layer flexible before the Valuation Engine is
introduced.

## Universal Valuation Platform

Onecool OS includes a universal valuation record layer in
`onecool_os.valuation`. Valuation is the source of truth for historical
valuation records across asset classes. Records are append-style history and
should not overwrite previous records.

Multiple valuation records can exist for the same asset on the same date when
they come from different sources. Portfolio and Dashboard consume valuation
records, but they do not own valuation history.

Current universal valuation components:

- `ValuationRecord`: Immutable valuation history record.
- `ValuationSource`: Supported valuation source enum.
- `ValuationConfidence`: Confidence enum.
- `ValuationLoader`: Loads validated valuation book JSON.
- `ValuationImportResult`: Loaded valuation book metadata and records.

Valuation JSON files use this shape:

```json
{
  "valuation_book_name": "Onecool Valuation Book",
  "base_currency": "TWD",
  "valuations": []
}
```

A demo template is provided at `data/valuation/valuation.example.json`. It
contains only sample valuation records. Real valuation files belong under
`data/valuation/` and should not be committed.

Source priority rules:

- Sports Cards: eBay Sold, Card Ladder, PWCC, Goldin, Fanatics, PSA Estimate,
  Manual.
- Securities: Yahoo, Polygon, Broker, Manual.
- Funds: Fund NAV, Morningstar, Broker, Manual.
- Real Estate: Real Estate Transaction, Bank Valuation, Manual.
- Cash: Broker, Manual.

Source of Truth:

| Layer | Owns |
| --- | --- |
| Connector | Raw external input |
| Normalize | Standardized records |
| Assets | Asset identity |
| Ledger | Transactions and lifecycle events |
| Valuation | Valuation history |
| Portfolio | Current holdings and calculated summaries |
| Dashboard | No data, display only |
| OFAI | Decisions and recommendations |

Connector imports raw data. Normalize standardizes it. Valuation stores
valuation records for later Portfolio, Dashboard, and OFAI consumption.

## Valuation Engine

Onecool OS includes a Valuation Engine foundation in
`onecool_os.intelligence.valuation`. The framework coordinates valuation
providers through a registry and returns normalized valuation results.

Current Valuation Engine components:

- `ValuationEngine`: Coordinates valuation providers.
- `BaseValuator`: Abstract provider interface.
- `ValuationResult`: Normalized valuation output.
- `ValuationRegistry`: Registers and retrieves valuators.
- `DemoValuator`: Built-in mock valuator for framework verification.

The demo valuator supports Funds, Sports Cards, Real Estate, and Cash using
mocked values only. It does not call Card Ladder, Yahoo pricing, real estate
pricing services, fund NAV providers, FX APIs, or persistence.

Run the valuation demo:

```bash
python -m onecool_os valuation demo
```

The demo output includes asset name, provider, estimated value, and confidence.

## Allocation Engine

Onecool OS includes an Allocation Engine foundation in
`onecool_os.intelligence.allocation`. The engine takes normalized
`ValuationResult` records and calculates portfolio market value allocation.

Current Allocation Engine components:

- `AllocationEngine`: Calculates portfolio totals and allocation percentages.
- `AllocationResult`: Normalized allocation output.

The allocation demo uses mocked valuation results only. It does not implement
rebalancing, buy/sell recommendations, risk analysis, scenario analysis, or
persistence.

Run the allocation demo:

```bash
python -m onecool_os allocation demo
```

The demo output includes asset, asset type, market value, allocation percent,
and portfolio total.

## Transaction & Ledger Foundation

Onecool OS includes a shared Transaction & Ledger foundation in
`onecool_os.transactions`. The ledger is the source of truth for asset history
across Funds, Securities, Sports Cards, Real Estate, Cash, Gold, Crypto, and
future asset modules.

Transactions record financial changes such as buys, sells, dividends,
deposits, fees, taxes, and transfers. Events record lifecycle changes such as
listing, reserving, shipping, grading, renovations, valuation updates, and
adjustments. Asset modules describe identity and ownership metadata; they
should not own transaction history.

Current Transaction & Ledger components:

- `Transaction`: Immutable shared financial transaction record.
- `Event`: Immutable shared asset lifecycle event record.
- `TransactionType`: Shared transaction type enum.
- `TransactionStatus`: Shared transaction status enum.
- `EventType`: Shared lifecycle event enum.
- `TransactionRegistry`: Backward-compatible registry for existing base
  transactions.
- `TransactionLoader`: Loads validated ledger records from JSON.
- `LedgerImportResult`: Loaded ledger name, base currency, transactions, and
  events.

Supported transaction types:

- `BUY`
- `SELL`
- `DIVIDEND`
- `INTEREST`
- `DEPOSIT`
- `WITHDRAW`
- `TRANSFER_IN`
- `TRANSFER_OUT`
- `SPLIT`
- `MERGE`
- `FEE`
- `TAX`
- `ADJUSTMENT`

Supported transaction statuses:

- `PENDING`
- `COMPLETED`
- `CANCELLED`

Supported lifecycle event types include purchase, sale, listing, reservation,
shipping, grading, dividends, splits, merges, loan and refinance events,
renovations, valuation updates, and adjustments.

Ledger JSON files use this shape:

```json
{
  "ledger_name": "Onecool Ledger",
  "base_currency": "TWD",
  "transactions": [],
  "events": []
}
```

A demo template is provided at `data/transactions/ledger.example.json`. It
contains only sample transactions and events. Real ledger files belong under
`data/transactions/` and should not be committed.

Architecture relationship:

- Assets describe identity.
- Transactions are immutable records.
- Events are immutable lifecycle records.
- Portfolio state will be derived from ledger data.
- Valuation estimates worth.
- Portfolio summarizes positions and totals.
- Allocation analyzes distribution.

This sprint does not implement performance calculations, IRR, realized PnL,
unrealized PnL, database persistence, or changes to Portfolio calculations.

## Project Structure

```text
.
├── examples
│   ├── cards_demo.json
│   ├── cash_demo.json
│   ├── funds_demo.json
│   ├── portfolio_demo.json
│   └── real_estate_demo.json
├── imports
│   ├── bgs
│   ├── cardladder
│   ├── comc
│   ├── ebay
│   └── psa
├── data
│   ├── portfolio
│   └── transactions
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
│   │   ├── base.py
│   ├── cli
│   ├── core
│   ├── intelligence
│   │   ├── allocation
│   │   └── valuation
│   ├── market
│   ├── portfolio
│   ├── transactions
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
- [Roadmap](docs/roadmap.md)
- [Coding Standard](docs/coding-standard.md)
- [Core Engine ADR](docs/decision-records/ADR-001-Core-Engine.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## Project Roadmap

The official project roadmap is maintained in
[docs/roadmap.md](docs/roadmap.md). It defines version planning from the
foundation through Transaction Layer, Valuation Engine, Dashboard, Automation,
OFAI Beta, and Onecool OS v1.0.
