# ADR-004 Collectible Radar MVP

## Status

Proposed, Revised

## Context

Onecool OS now has the core layers needed for a product-specific workflow:
Connectors, Normalize, Assets, Ledger, Valuation, Portfolio, Business Logic,
Analytics, Dashboard, Scenario, OFAI, and Decision.

Sports Cards already exist as an asset module and inventory-style asset class.
The first real product should prove that Onecool OS can turn raw external data
into trusted decision context without relying on LLMs, predictions, or
theoretical valuations.

The valuation philosophy of Onecool OS is to reflect the closest executable
market price, not a theoretical estimated value.

## Decision

Build Collectible Radar MVP as the first product on Onecool OS.

The MVP will focus on sports card inventory and valuation intelligence. It will
consume data from PSA Collection CSV, eBay Sold, Card Ladder, PWCC, Goldin,
Fanatics Collect, and Manual inputs through connector layers.

It will normalize records, preserve valuation history, expose primary market
price and validation signals, calculate deterministic metrics, display dashboard
views, create scenarios, prepare OFAI context, and generate decision-readiness
outputs.

## Primary Market Price

Primary Market Price represents the most realistic price at which the asset
could likely be sold today.

For Collectible Radar MVP:

1. eBay Sold

eBay Sold is the default Primary Market Price for sports cards because it most
closely reflects broad, executable market-clearing transactions.

## Validation Sources

Validation Sources do not replace the Primary Market Price. They verify
confidence, detect anomalies, and increase valuation reliability.

Validation Sources:

- Card Ladder
- PWCC
- Goldin
- Fanatics Collect
- Manual

These sources should be preserved as independent valuation records and used to
assess agreement, disagreement, confidence, and review readiness.

## Valuation Strategy

```text
Market Value
↓
Primary Market Price
↓
Validation Sources
↓
Confidence
↓
Decision
```

The system should preserve all valuation records.

Valuation history must never be overwritten. Each source observation should
remain traceable with:

- source
- source type
- external id
- valuation date
- market value
- confidence
- URL or reference
- raw payload when available

Market Value should be derived from the Primary Market Price when available,
with Validation Sources used to evaluate reliability.

## Valuation Consensus

When the Primary Market Price and Validation Sources are close, confidence
increases.

When the Primary Market Price and Validation Sources diverge significantly,
confidence decreases.

The system must not silently choose one source and hide disagreement. If
material divergence exists, the Decision Engine should generate review-oriented
outputs such as:

- Requires Source Verification
- Valuation Confidence Low
- Multiple Market Sources Disagree

This keeps the user aware of uncertainty instead of presenting false precision.

## Connector Architecture

Recommended connectors:

- PSACollectionCSVConnector
- EbaySoldConnector
- CardLadderConnector
- PWCCConnector
- GoldinConnector
- FanaticsCollectConnector

Each connector should:

- read raw input
- preserve external source identity
- emit normalized records
- avoid business logic
- avoid valuation decisions
- never mutate source files
- never decide which marketplace is correct

Recommended package shape:

```text
onecool_os/connectors/collectibles/
  __init__.py
  psa.py
  ebay.py
  cardladder.py
  pwcc.py
  goldin.py
  fanatics.py
  normalization.py
```

## Business Logic

Business Logic never decides which marketplace is correct.

Business Logic exposes deterministic signals:

- Primary Market Price
- Validation Results
- Confidence
- Source Agreement
- Source Divergence
- Missing valuation
- Stale valuation
- Concentration risk
- Liquidity risk

Decision Engine interprets these signals. Dashboard presents them. OFAI prepares
context around them.

## Dashboard

Collectible Radar Dashboard should show:

- Primary Market Source
- Primary Market Price
- Validation Sources
- Valuation Confidence
- Source Agreement
- Source Divergence
- Missing valuation
- Stale valuation
- Collection market value
- Cost basis
- Unrealized gain/loss
- Player, sport, brand, and grade exposure
- Decision readiness queue

Dashboard must not calculate or decide. It only presents Analytics, Business
Logic, Scenario, OFAI, and Decision outputs.

## Decision Outputs

Decision Engine should produce review-oriented outputs, not final advice.

Preferred outputs:

- Requires Source Verification
- Valuation Confidence Low
- Multiple Market Sources Disagree
- Missing Primary Market Price
- Missing Validation Sources
- Review High Concentration
- Review Stale Valuation
- Ready for Manual Review
- Blocked Due to Missing Data

Decision Engine must not output:

- Sell now
- Buy now
- This will go up
- Guaranteed undervalued
- Final financial advice

## Scenario Usage

Scenario Engine should create A/B/C/D market context:

- A: Base Case
  Primary Market Price remains stable and validation sources generally agree.
- B: Upside Case
  Primary Market Price strengthens and validation sources confirm.
- C: Downside Case
  Primary Market Price weakens or validation sources show lower comps.
- D: Stress Case
  Primary Market Price disappears, liquidity drops, or sources diverge sharply.

Scenario outputs should feed OFAI and Decision Engine as structured
possibilities, not predictions.

## OFAI Usage

OFAI should prepare decision context:

- summarize valuation confidence
- include Primary Market Price
- include Validation Source agreement
- include Business Logic signals
- include ScenarioSet
- include Decision candidates

OFAI should not call an LLM in MVP. It should produce deterministic context that
future AI can consume safely.

## Consequences

Positive:

- Prioritizes executable market prices over theoretical estimates.
- Keeps eBay Sold as the default sellable-market anchor for sports cards.
- Preserves every valuation record for auditability.
- Makes disagreement visible instead of hiding uncertainty.
- Gives Decision Engine better inputs for review readiness.
- Keeps Dashboard honest about confidence and source agreement.

Trade-offs:

- Requires careful source normalization.
- Requires explicit source agreement logic.
- Some premium cards may have sparse eBay Sold data.
- Validation sources may disagree due to venue, timing, grade, or card rarity.
- Decision language must stay review-oriented, not advisory.

## Boundaries

Collectible Radar must not:

- predict markets
- call LLMs
- recommend final buy/sell decisions
- execute trades
- mutate raw imports
- overwrite valuation history
- silently hide source disagreement
- provide legal, tax, or financial advice as final truth

## Implementation Guidance

Start with connector and normalization foundations before live APIs. Use local
fixture files and mocked responses.

The first implementation should focus on:

- Collectible connector contracts
- eBay Sold as Primary Market Price source
- Validation Source records
- Valuation confidence and source agreement model
- Dashboard display fields
- Decision outputs for source verification

Every sprint must remain executable and fully tested.

## Product Sprint 1 Alignment

The first implementation sprint establishes local collectible connector
contracts only. eBay Sold, Card Ladder, PWCC, Goldin, and Fanatics Collect
connectors accept local records or fixtures and emit shared market records.
They do not call live APIs, scrape websites, decide final valuation, calculate
confidence, or mutate raw imports.

## Product Sprint 2 Alignment

The second implementation sprint maps collectible market records into
ValuationRecord-compatible history plus collectible metadata. The mapper
preserves source role, external ID, sale price, currency, sale date, URL, raw
payload, and raw market record ID.

The mapper records eBay Sold as a Primary Market Price input. Card Ladder,
PWCC, Goldin, Fanatics Collect, and Manual remain independent Validation Source
inputs. The mapper does not select a final market value, calculate confidence,
resolve source agreement, or overwrite valuation history.

## Product Sprint 3 Alignment

The third implementation sprint introduces reusable Market Intelligence.
Collectible Radar is the first implementation, but the framework must remain
asset-agnostic for House Radar, Fund Radar, Stock Radar, Business Radar, and
future products.

Market Intelligence evaluates market data quality only. It checks Primary
Market Price, Validation Source coverage, source agreement, freshness,
liquidity, warnings, and explainable confidence components. It never predicts
prices, recommends buying or selling, calls live APIs, mutates source data,
chooses final valuation, or modifies valuation history.

`reference_datetime` is injectable and must be used instead of the system clock
so replay, backtesting, deterministic tests, and historical reconstruction can
use the same market observations consistently.

## Source Agreement Alignment

Source Agreement is the deterministic layer that evaluates how closely eBay
Sold Primary Market Price records agree with Card Ladder, Manual, PWCC,
Goldin, and Fanatics Validation Source records. It produces agreement score,
agreement level, agreement spread, max divergence, missing sources, source
count, warnings, and raw valuation IDs.

Source Agreement does not choose final valuation, replace eBay Sold as Primary
Market Price, predict prices, recommend buying or selling, overwrite valuation
history, mutate source data, call APIs, scrape websites, or hide disagreement.
Market Intelligence should consume `SourceAgreementResult` instead of
reimplementing agreement rules independently.

Market Intelligence v2 accepts optional `SourceAgreementResult`. When provided,
it uses the Source Agreement score, level, participating sources, missing
sources, and warnings without recalculating agreement. When not provided, the
legacy Market Intelligence path remains available for backward compatibility.

## Product Sprint 4 Alignment

The fourth implementation sprint introduces the Collectible Intelligence
Engine. It consumes Market Intelligence and produces collectible-specific
deterministic quality signals for market quality, valuation quality, liquidity
quality, source quality, review status, and warnings.

Collectible Intelligence prepares data for Analytics, Dashboard, Decision, and
OFAI. It does not choose final valuation, predict prices, recommend buying or
selling, call APIs, mutate source data, mutate valuation history, set target
prices, or perform OFAI reasoning.

## Product Sprint 5 Alignment

The fifth implementation sprint introduces the reusable Radar Engine.
Collectible Radar is the first implementation, but the same Radar architecture
should support House Radar, Fund Radar, Stock Radar, Business Radar, Emergency
Radar, and future products.

Radar consumes deterministic intelligence output and detects meaningful changes
over time. It produces snapshots containing current signals, previous signals,
new signals, resolved signals, changed signals, escalated signals, summaries,
warnings, and source snapshot IDs.

Radar never calculates valuation, modifies historical data, predicts markets,
recommends buying or selling, calls APIs, mutates source data, or performs LLM
reasoning. Analytics stores Radar output, Dashboard displays Radar output, and
Decision consumes Radar output.

## Product Sprint 6 Alignment

The sixth implementation sprint introduces reusable Timeline Analytics.
Collectible Radar is the first implementation, but the same timeline
architecture should support House Radar, Fund Radar, Stock Radar, Business
Radar, Emergency Radar, and future products.

Timeline Analytics summarizes historical Radar snapshots across time. It
produces trend direction, trend strength, trend summaries, signal statistics,
quality trends, warnings, and radar snapshot IDs.

Timeline Analytics never calculates valuation, modifies history, predicts
future performance, recommends buying or selling, mutates source data, or calls
APIs. Dashboard displays Timeline Analytics. Decision and OFAI consume Timeline
Analytics.

## Product Sprint 7 Alignment

The seventh implementation sprint introduces the Collectible Dashboard
foundation. Dashboard is a presentation layer that assembles existing Business
Logic, Market Intelligence, Radar, Timeline Analytics, and optional Decision
outputs into display sections.

Dashboard never recalculates confidence, trend, valuation, quality, or business
rules. It never predicts markets, recommends buying or selling, mutates data,
or owns source data.

## Product Sprint 8 Alignment

The eighth implementation sprint introduces the Daily Radar Report foundation.
This is the first end-user product output built on Onecool OS.

Daily Radar Report consumes the Collectible Dashboard and assembles structured
sections for collection summary, market summary, today's changes, timeline
summary, review queue, and warnings. It returns structured models for future
CLI, HTML, PDF, and Web UI adapters.

Daily Radar Report never recalculates business logic, valuation, confidence,
trend, or quality. It never predicts markets, recommends buying or selling,
mutates source data, or calls APIs.

## Feature 1 Alignment

Decision Queue prioritizes Collectible Radar review work from deterministic
Daily Radar Report outputs. It groups queue items into critical, high, medium,
and low priority groups based on existing warnings, review counts, and radar
signals.

Decision Queue only classifies review work. It never calculates valuation,
predicts prices, recommends buying or selling, modifies source data, mutates
history, calls APIs, or invokes LLMs.

## Feature 2 Alignment

Collectible OFAI Context prepares deterministic context from the Daily Radar
Report and Decision Queue. It summarizes collection state, market quality,
radar changes, timeline trend, review priorities, and warnings for future OFAI
workflows.

Collectible OFAI Context is not an AI model. It never recommends buying or
selling, predicts prices, executes actions, calls LLMs, mutates source data,
modifies history, or calculates valuation.

## Golden Dataset Alignment

The Collectible Golden Dataset protects the MVP pipeline from regression by
storing synthetic fixture inputs and expected outputs. It exercises connector
normalization, valuation mapping, Market Intelligence, Collectible
Intelligence, Radar, Timeline Analytics, Dashboard, Daily Radar Report,
Decision Queue, and OFAI Context as one deterministic product flow.

Golden Dataset records are demo-only and safe to commit. They must not include
real private holdings, call APIs, scrape websites, mutate production data,
predict prices, or recommend buying or selling.

## Live Connector Readiness Alignment

Collectible Radar live ingestion must prefer safe, user-approved, export-based
or API-based workflows. Unauthorized scraping is not part of the MVP.

PSA Collection CSV and Manual import are `READY` because they can operate on
local user-provided files without Onecool OS storing platform credentials.
eBay Sold, Card Ladder, PWCC, Goldin, and Fanatics Collect are
`NEEDS_REVIEW` until approved APIs, export availability, authentication
requirements, data freshness, and legal / terms risks are reviewed.

The recommended implementation order is PSA Collection CSV real import, Manual
valuation import, eBay Sold approved/manual import, Card Ladder approved/manual
import, then PWCC / Goldin / Fanatics as validation sources.

## PSA Collection Integration Alignment

PSA Collection Integration is the first production-ready ingestion path for
Collectible Radar. The connector-layer importer reads real PSA Collection CSV
exports, validates required columns, detects duplicate and missing certificate
numbers, validates grades, preserves collection identifiers, and produces
normalized sports card asset records with `ImportSummary` and reusable
`ImportAudit`.

The importer only imports. It does not calculate valuation, confidence,
Business Logic, Radar, Timeline, Dashboard, Decision Queue, OFAI Context, or
recommendations. It does not call APIs, scrape websites, mutate source CSV
files, mutate Ledger, or mutate valuation history.

## Manual Valuation Import Alignment

Manual Valuation Import provides a safe, auditable fallback / validation input
for user-provided valuation observations. It accepts CSV or JSON, validates
required fields, emits independent `ValuationRecord` objects with source
`MANUAL`, and records `ImportSummary` plus reusable `ImportAudit`.

Manual valuations are preserved as valuation history. They never overwrite
existing valuation records, replace eBay Sold as Primary Market Price,
calculate confidence, calculate source agreement, predict prices, recommend
buying or selling, call APIs, scrape websites, or mutate source files.

## eBay Sold Integration Readiness Alignment

eBay Sold remains the sports card Primary Market Price source for Collectible
Radar. It should enter the system through approved API access when allowed and
available, user-provided CSV / JSON exports, or manual fixture imports.
Unauthorized scraping, browser automation for scraping, credential sharing, and
hidden source disagreement are rejected for MVP.

eBay Sold imports must preserve sale price, currency, sale date, source
identity, external ID or URL/reference, and optional shipping separately from
item price. eBay Sold observations create independent valuation records and do
not overwrite valuation history. Validation sources compare against eBay Sold,
and disagreement must remain visible to Market Intelligence, Dashboard,
Decision Queue, and OFAI Context.

The eBay Sold Manual Import foundation is the first supported eBay Sold
ingestion path. It accepts user-provided CSV / JSON only, emits
`CollectibleMarketRecord` observations with source `EBAY_SOLD`, records
`ImportSummary` and reusable `ImportAudit`, and preserves source references for
future review. It does not call APIs, scrape websites, add credentials, select
final valuation, calculate confidence, recommend actions, mutate source files,
or overwrite valuation history.

## Card Ladder Integration Readiness Alignment

Card Ladder is a Validation Source for Collectible Radar. It does not replace
eBay Sold as the sports card Primary Market Price source and must not decide
which marketplace is correct.

Approved Card Ladder ingestion options are, in order: official API if allowed
and available, official export if available, user-provided CSV / JSON export,
and manual fixture import. Unauthorized scraping, browser automation for
scraping, credential sharing, and hidden source disagreement are rejected for
MVP.

Card Ladder imports must preserve asset identity or hint, valuation value or
market value, currency, valuation date, source identity, external ID or
URL/reference, and optional market context such as population or sales count.
Card Ladder observations create independent valuation records. They help
evaluate confidence, source agreement, and source divergence later, but they do
not overwrite valuation history, select final market value, calculate
confidence, recommend actions, or mutate source files.

The Card Ladder Manual Import foundation is the first supported Card Ladder
ingestion path. It accepts user-provided CSV / JSON only, emits
`CollectibleMarketRecord` observations with source `CARD_LADDER` and source
role `VALIDATION_SOURCE`, records `ImportSummary` and reusable `ImportAudit`,
and preserves source references for future review. It does not call APIs,
scrape websites, add credentials, replace eBay Sold as Primary Market Price,
overwrite valuation history, select final valuation, calculate confidence or
source agreement, recommend actions, predict prices, or mutate source files.
