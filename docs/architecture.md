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

## Collectible Radar Beta

Collectible Radar Beta is the first product-level validation of the Onecool OS
architecture. The release review is documented in
`docs/releases/collectible-radar-beta-review.md`.

The official v0.3.0-beta release preparation is documented in
`docs/releases/v0.3.0-beta.md`.

The official v0.4.0-beta release preparation is documented in
`docs/releases/v0.4.0-beta.md`. It freezes the Investment Performance Beta
loop for deterministic unrealized performance.

Validated Beta pipeline:

```text
PSA Import / eBay Sold Import / Card Ladder Import / Manual Valuation Import
↓
Valuation Records
↓
Source Agreement
↓
Market Intelligence
↓
Collectible Intelligence
↓
Radar
↓
Timeline Analytics
↓
Dashboard
↓
Daily Radar Report
↓
Decision Queue
↓
OFAI Context
```

The Beta contract remains deterministic, local-file based, and read-only with
respect to source files and valuation history. Live APIs, scraping,
credentials, recommendations, market prediction, scheduling, and persistent
audit storage remain outside Beta scope.

## Investment Performance Beta

Investment Performance Beta extends Collectible Radar with the ADR-005
unrealized performance loop:

```text
Assets
↓
Valuation
↓
Investment Performance
↓
Dashboard
↓
Daily Report
↓
Decision Queue
↓
OFAI Context
```

The Performance Engine calculates only cost basis, market value, unrealized
gain/loss, unrealized gain percent, and holding days. Dashboard displays,
Daily Report assembles, Decision Queue prioritizes review work, and OFAI
prepares deterministic context. FX Engine, Lifecycle Engine, realized
gain/loss, IRR/XIRR, annualized return, prediction, and recommendation remain
outside v0.4.0-beta scope.

The real data trial plan is documented in
`docs/trials/collectible-radar-real-data-trial.md`. The trial validates the
same deterministic pipeline with the owner's private collection while keeping
real source files and generated private outputs outside Git.

The first trial result is documented in
`docs/trials/collectible-radar-real-data-results.md`. It records aggregate
findings only and confirms that private source files must remain outside Git.

The PSA Collection gap analysis is documented in
`docs/trials/psa-collection-gap-analysis.md`. It confirms that PSA import
should remain an ingestion layer and that future PSA fields should flow into
Assets, Inventory, Ledger, and Valuation through explicit contracts.

## Asset Master

Asset Master sits beside imported asset records as durable user-maintained
metadata. It does not call APIs, scrape websites, create valuation records, or
change Dashboard or Performance behavior. It joins imported PSA/BGS records by
cert number and returns enriched runtime assets without mutating imported
records. Imported collection identity remains authoritative, while Asset
Master may add research URLs, watch status, target price, notes, explicit cost
override metadata, and future custom fields.

Asset Master Builder is a local file builder for the user's private workbook.
It consumes the latest PSA/BGS Collection CSV as identity authority and updates
the existing workbook while preserving remaining formatting, worksheet
structure, native hyperlinks, and permanent metadata. It removes runtime
analytics columns such as current market value, gain/loss, ROI, annualized
return, REF, and recommendation fields. It appends missing cards, creates a
`Sync Report` worksheet, validates unique card counts, and writes through a
temporary workbook before replacing the private output. It is not a valuation,
sync-resolution, API, scraping, analytics, or recommendation layer.

## Collection Sync

Collection Sync sits between PSA/BGS import, Asset Master, and Runtime. It is
the deterministic data integrity layer that compares imported collectible
records with user-owned Asset Master metadata. It produces `SyncReport`
objects containing differences, warnings, matched counts, and collection
health. It never modifies imported files, automatically merges records, deletes
records, calculates valuation, calls AI, calls APIs, or changes Dashboard,
Report, Decision Queue, or OFAI behavior.

Runtime Session executes Collection Sync automatically whenever imported
records and Asset Master records are loaded into runtime. Runtime stores the
resulting sync report, collection health, generated timestamp, and helper
methods for future decision-priority support. Presentation layers remain
unchanged until dedicated integration sprints.

The launcher loads Asset Master into RuntimeSession immediately after a
successful PSA/BGS import. It prefers XLSX, falls back to CSV, and preserves the
collection import if Asset Master is missing or fails validation. No source
files are mutated, and presentation layers consume the existing RuntimeSession
instead of loading files directly.

Dashboard Collection Health is the first presentation consumer of Runtime
Session sync status. It reads existing `SyncReport` and RuntimeSession helper
outputs only. It does not rerun sync, recalculate health, resolve
differences, mutate records, or convert integrity status into investment
quality.

## Source of Truth

| Layer | Source of Truth |
| --- | --- |
| Connector | Raw external input |
| Normalize | Standardized records |
| Assets | Asset identity |
| Asset Master | User-owned metadata augmentation |
| Collection Sync | Runtime readiness integrity report |
| Ledger | Transactions and lifecycle events |
| Valuation | Valuation history |
| Portfolio | Current holdings and aggregation |
| Business Logic | Deterministic calculations, policies, and signals |
| Research Queue | Deterministic research prioritization and readiness |
| Research Workbench | Provider-independent request export and result import |
| Analytics | Derived snapshots |
| Services | Read-only access interface |
| Dashboard | Display-only views |
| Scenario | Structured scenario objects |
| OFAI | Decisions and recommendations |
| Decision | Decision options, scores, readiness, and audit trails |

## Layer Responsibilities

| Layer | Responsibility |
| --- | --- |
| Asset Master | Augment imported assets without replacing source identity |
| Collection Sync | Compare imported records and Asset Master before runtime |
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

eBay Sold Manual Import is the first supported eBay Sold ingestion path. It
produces `CollectibleMarketRecord` observations with source `EBAY_SOLD` and
source role `PRIMARY_MARKET_PRICE`, plus `ImportSummary` and `ImportAudit`.
The importer is read-only: it does not call APIs, scrape, add credentials,
select final valuation, calculate confidence, recommend actions, mutate source
files, or overwrite valuation history.

eBay Sold Evidence sits between Asset Master research URLs, future research
providers, RuntimeSession, and Valuation Runtime. Providers return evidence,
not final prices. Evidence is untrusted until deterministic validation checks
sold URL, item ID, sold date, price, exact identity match, grade, grade issuer,
year, set, card number, subject, variety, and special designation. Active
listings, malformed prices or dates, identity mismatches, and Black Label
mismatches are rejected. Ambiguous titles, unknown shipping, unconfirmed Best
Offer prices, stale sold dates, incomplete identity matches, and single-comps
remain review evidence. Only `VERIFIED` evidence may automatically map to
`ValuationRecord`; review, rejected, and no-match evidence remain session-only
evidence.

## Onecool Research Framework

Onecool Research Framework sits between external research providers and
existing evidence layers:

```text
External Research Provider
↓
Onecool Research Framework
↓
Normalization
↓
Validation
↓
Research Evidence
↓
Existing Evidence Layer
↓
Valuation Runtime
↓
Dashboard / Report / Decision Queue / OFAI
```

External providers such as ChatGPT, Gemini, official APIs, Card Ladder,
authorized third-party providers, and manual structured research are
replaceable adapters. They must not write directly into RuntimeSession,
Valuation, Dashboard, Decision Queue, or OFAI. ORF preserves provider output
as immutable `ResearchResult` and `ResearchEvidence`, validates it, and keeps
provider metadata auditable. Provider output is untrusted by default.

ORF does not call providers in this foundation, does not scrape, does not
store credentials, does not calculate valuation, does not recommend actions,
and does not mutate source data. Compatible collectible `SOLD_COMPARABLES`
evidence may bridge into `EbaySoldEvidence`, but the existing eBay Sold
Evidence layer remains responsible for final evidence validation.

Research Queue is the deterministic planning layer for market research work.
It consumes RuntimeSession assets, Asset Master entry points, Collection Sync
differences, existing evidence, valuation records, and Portfolio NAV coverage.
It produces `ResearchQueueSnapshot` and `ResearchQueueItem` records with
priority, readiness, reasons, blockers, evidence counts, and valuation
coverage status. It does not call providers, create evidence, create
valuation records, calculate NAV, recommend actions, predict prices, mutate
RuntimeSession, mutate Asset Master, or change Dashboard, Daily Report, or
Decision Queue output.

Research Workbench is the provider-independent handoff layer for research
packages. The eBay Sold URL Research PoC exports READY Research Queue items
into JSON request packages and imports provider-returned ORF-compatible JSON.
Import always uses ORF validation, then the existing ORF-to-eBay Sold Evidence
bridge, then eBay Sold Evidence validation. Workbench does not call providers,
scrape, fabricate sold records, create valuation records directly, calculate
NAV, mutate Asset Master, or bypass validation.

Single Asset Research Pipeline is the first end-to-end proof for one real
collectible. It locates one RuntimeSession asset by cert number, validates its
identity, requires one READY SOLD_COMPARABLES Research Queue item, exports one
eBay URL research request, imports externally supplied ORF JSON when present,
attaches validated evidence to a new RuntimeSession, and reports counts. It
does not retrieve data, create valuation records, update NAV, calculate fair
value, or recommend actions.

Card Ladder readiness is documented in
`docs/live-connectors/card-ladder-readiness.md`. Card Ladder is a Validation
Source that should enter through approved API access if allowed and available,
official export if available, user-provided CSV / JSON export, or manual
fixture import. It does not replace eBay Sold as Primary Market Price, choose
final market value, calculate confidence, hide source disagreement, or mutate
valuation history.

Card Ladder Manual Import is the first supported Card Ladder ingestion path.
It produces `CollectibleMarketRecord` observations with source `CARD_LADDER`
and source role `VALIDATION_SOURCE`, plus `ImportSummary` and `ImportAudit`.
The importer is read-only: it does not call APIs, scrape, add credentials,
replace eBay Sold, overwrite valuation history, select final valuation,
calculate confidence or source agreement, recommend actions, predict prices,
or mutate source files.

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

Existing holdings do not require historical transaction backfill. Imported
cost basis is treated as opening position cost, and future transactions are
recorded prospectively. Investment performance and asset lifecycle policy is
defined in
`docs/decision-records/ADR-005-Investment-Performance-and-Asset-Lifecycle.md`.

### Valuation

Valuation owns valuation history. Valuation records are historical and should
not overwrite previous records.

The Collectible Valuation Mapper sits between collectible market records and
Valuation. It converts each market observation into a `ValuationRecord` plus
metadata for source role, external ID, raw market record ID, and raw payload.
It does not choose final market value, calculate confidence, resolve source
agreement, or mutate raw imports.

Runtime valuation providers sit at the Valuation boundary. They abstract future
authorized sources such as Gemini Research Agent, ChatGPT Research Agent,
official eBay APIs, or manual runtime input into existing `ValuationRecord`
objects. Providers may search, normalize, validate, and expose metadata. They
must not select final valuation, mutate imports or valuation history, perform
unauthorized scraping, or change Dashboard, Performance, Importer, or Business
Logic behavior.

Source Agreement sits after valuation records and before Market Intelligence.
It compares eBay Sold Primary Market Price records with Card Ladder, Manual,
PWCC, Goldin, and Fanatics Validation Sources. It produces deterministic
agreement score, level, spread, divergence, missing sources, and warnings. It
does not choose final valuation, replace eBay Sold, overwrite valuation
history, predict prices, recommend actions, call APIs, scrape websites, mutate
source data, or hide disagreement.

Market Intelligence sits after valuation mapping and before Business Logic. It
evaluates market data quality only: Primary Market Price presence, Validation
Source coverage, source agreement, freshness, liquidity, warnings, and
explainable confidence components. It does not determine final valuation,
predict prices, recommend buying or selling, call live APIs, mutate source
data, or modify valuation history. Market Intelligence should consume
`SourceAgreementResult` rather than independently reimplement source agreement.
Market Intelligence v2 accepts optional Source Agreement input and, when
provided, uses its agreement score, level, participating sources, missing
sources, and warnings while preserving backward-compatible behavior without it.

`reference_datetime` is injected into Market Intelligence builders so replay,
backtesting, and historical reconstruction remain deterministic.

### Fair Value

Onecool Fair Value is the deterministic collectible market price layer between
verified eBay Sold Evidence and future ValuationRecord creation. It consumes
only `VERIFIED` evidence, rejects review or mismatched evidence, deduplicates
sold items, applies the latest-10-within-180-days sample window by default,
and produces `OnecoolFairValueSnapshot` records.

Fair Value calculates Decimal-only comparable statistics, liquidity, freshness,
confidence, Evidence Quality Score, and warnings. It does not call providers,
scrape websites, create NAV, update Dashboard, recommend actions, calculate
portfolio ROI, mutate evidence, or create ValuationRecord objects in this
foundation sprint. RuntimeSession may expose Fair Value snapshots through
delegation, but RuntimeSession does not calculate fair value internally.

Fair Value to ValuationRecord Integration is the canonical runtime handoff for
collectibles. Trusted `ONECOOL_FAIR_VALUE` snapshots become one
`ValuationRecord` per asset/source. `INSUFFICIENT_DATA` snapshots become
runtime placeholder statuses and do not enter trusted valuation history.
Portfolio NAV consumes `ValuationRecord` objects only.

Portfolio NAV Runtime Integration wires canonical runtime valuation into NAV
through `RuntimeSession.build_live_portfolio_nav()`. Runtime delegates to
engines and stores no duplicated calculation state. Live NAV uses
`ONECOOL_FAIR_VALUE` records only in this phase; supporting estimates remain
outside trusted live NAV. Partial coverage is a trust indicator, not an
investment recommendation, and Dashboard presents the resulting
`PortfolioNavSnapshot` without recalculation.

### Portfolio

Portfolio aggregates current holdings and summary values. It consumes Assets,
Ledger, and Valuation, but owns no source history.

Portfolio NAV Engine is a deterministic derived layer inside Portfolio. It
consumes RuntimeSession assets, existing valuation records, and upstream
evidence status to produce `PortfolioNavSnapshot` outputs. It does not create
market prices, estimate missing values, parse notes, call providers, perform
FX conversion, mutate RuntimeSession, mutate Asset Master, or recommend
actions. NAV snapshots aggregate one currency only; mixed-currency data must
produce separate snapshots or explicit currency mismatch warnings.

Verified coverage and estimated coverage remain separate. Missing market
values are never treated as zero. Evidence validation remains upstream, and
unverified eBay evidence cannot enter trusted NAV.

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

The reusable Investment Performance Engine in `onecool_os.performance`
implements ADR-005 at the asset level. It consumes asset facts and valuation
records, then produces `InvestmentPerformanceSnapshot` output for opening cost
basis, market value, unrealized gain/loss, unrealized gain percent, and holding
days. It does not perform FX conversion, annualization, IRR/XIRR, source
agreement, confidence scoring, recommendations, API calls, or source mutation.

Collectible Performance Integration maps PSA/BGS-style sports card asset
records into the reusable engine. `My Cost` or normalized `cost` is treated as
opening cost basis, cost currency is preserved, acquisition date is used only
for holding days, and market value must come from caller-prepared valuation
records. Notes are not parsed for local currency cost. Realized gain/loss and
FX gain/loss remain future Lifecycle and FX Engine concerns.

Performance and lifecycle are separate concerns. Performance calculates
returns. Lifecycle tracks states such as `OWNED`, `LISTED`, `SOLD`, `PAID`,
and `ARCHIVED`. Importers preserve source facts but do not calculate
performance.

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

Performance Dashboard views consume `InvestmentPerformanceSnapshot` records and
render portfolio performance, asset performance tables, summaries, and
warnings. Dashboard may aggregate display totals from existing snapshot fields,
but it does not recalculate investment performance, FX, IRR/XIRR, source
agreement, confidence, valuation, or recommendations.

Portfolio NAV Dashboard views consume `PortfolioNavSnapshot` records and
render NAV status, totals, coverage, and concise asset review rows. Dashboard
does not select valuation records, recalculate NAV or ROI, combine currencies,
estimate missing values, call providers, or recommend actions. Missing NAV
values display as `N/A`, not zero.

Performance Daily Report views consume existing Dashboard performance sections.
The report displays performance summary, top movers, and warnings, but it does
not recalculate performance, realized gain/loss, FX, IRR/XIRR, valuation,
confidence, or recommendations.

Performance Decision Queue integration consumes performance warnings and
summary fields from the Daily Report. It classifies review priority only:
Critical for missing cost basis or market value, High for insufficient data or
currency mismatch, Medium for missing holding dates, and Low for review-only
performance availability. It does not calculate or recommend.

Performance OFAI Context consumes the Performance Daily Report and Decision
Queue priorities to prepare deterministic investment context. It exposes
performance overview, top movers, warnings, and performance review priorities
for future AI reasoning. It does not call LLMs, recalculate performance,
predict prices, or recommend actions.

The Performance Closed-Loop Review verifies this path as v0.4 beta-ready for
deterministic unrealized performance. The loop is documented in
`docs/releases/performance-closed-loop-review.md`.

### CLI

The Onecool Launcher is the first Beta dogfooding entry point. It starts with
`python -m onecool_os` or `python -m onecool_os.cli`, displays the
v0.4.0-beta menu, and routes users toward PSA import, Dashboard, Daily Report,
Decision Queue, and OFAI Context workflows.

The launcher is orchestration-only. It does not own source data, calculate
metrics, call APIs, scrape websites, mutate private imports, or bypass lower
layer boundaries. Local import files remain under `imports/` and are ignored
by Git.

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
