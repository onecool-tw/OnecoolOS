# Onecool OS Roadmap

## Vision

Onecool OS is a personal operating system for managing and optimizing all
assets, knowledge, decisions, and automation.

---

## Development Principles

- Architecture first
- Reusable modules
- Asset-agnostic design
- Connector -> Normalize -> Asset -> Ledger -> Valuation -> Portfolio pipeline
- Test-first development
- Backward compatibility

---

## Version Roadmap

### v0.1.0 Alpha Architecture Freeze (Completed)

Foundation:

- Core Engine
- Configuration
- Logging
- Scheduler
- Market foundation
- Asset module foundation
- Connector Layer
- Normalize Layer

Data Platform:

- Ledger
- Valuation
- Portfolio Aggregation
- Business Logic
- Analytics

Presentation Platform:

- Services
- Dashboard foundation
- Scenario Engine

v0.2 Beta Architecture Freeze:

- Business Intelligence Foundation
- Scenario Engine Foundation
- OFAI Foundation
- Decision Engine Architecture Proposal
- Decision Engine Foundation

Next:

- Collectible Connectors Foundation
- Collectible Valuation Mapping Foundation
- Decision Rules Foundation
- Decision Scoring Foundation
- Recommendation Engine Foundation
- Automation Foundation

### Product Track: Collectible Radar MVP

Goals:

- Preserve sports card market source identity
- Treat eBay Sold as Primary Market Price
- Treat Card Ladder, PWCC, Goldin, and Fanatics Collect as Validation Sources
- Normalize local fixture/export records without live API calls
- Map collectible market records into valuation history records
- Preserve all source observations for future valuation confidence and source
  agreement
- Keep eBay Sold and Validation Sources as independent valuation records
- Evaluate market data quality through reusable Market Intelligence
- Expose explainable confidence, source agreement, coverage, freshness, and
  liquidity components
- Produce collectible-specific Business Logic quality signals without
  recommendations
- Detect new, resolved, changed, and escalated signals through reusable Radar
  snapshots
- Summarize historical Radar snapshots through reusable Timeline Analytics
- Assemble Collectible Radar outputs through presentation-only Dashboard views
- Produce Daily Radar Report as the first structured end-user product output
- Prioritize review work through Decision Queue without recommendations
- Prepare deterministic Collectible OFAI Context without AI reasoning
- Protect the full Collectible Radar pipeline with a synthetic Golden Dataset
- Review live connector readiness and prefer safe export/API ingestion
- Integrate real PSA Collection CSV exports through read-only connector import
  and reusable ImportAudit
- Import manual valuation observations as auditable fallback / validation
  records without replacing Primary Market Price
- Prepare eBay Sold Primary Market Price ingestion through approved API,
  user-provided export, or manual fixture paths
- Support eBay Sold manual CSV / JSON import as the first Primary Market Price
  ingestion path
- Prepare Card Ladder Validation Source ingestion through approved API,
  official export, user-provided export, or manual fixture paths
- Support Card Ladder manual CSV / JSON import as the first Validation Source
  ingestion path
- Evaluate eBay Sold and Validation Source agreement through reusable Source
  Agreement results without choosing final valuation
- Integrate Source Agreement into Market Intelligence v2 without duplicating
  agreement logic
- Complete Collectible Radar Beta release review and public contract checklist
- Feed Dashboard and Decision readiness without hiding source disagreement

Beta Review:

- `docs/releases/collectible-radar-beta-review.md`
- `docs/releases/v0.3.0-beta.md`
- `docs/trials/collectible-radar-real-data-trial.md`

### v0.3 Foundation (Completed)

- Core Engine
- Asset Models
- Portfolio
- Connector Layer
- Normalize Layer
- Inventory Foundation

### v0.4 Transaction Layer

Goals:

- Transaction model
- Ledger model
- Lifecycle events
- Buy
- Sell
- Transfer
- Dividend
- Fee
- Split

Deliverables:

- Transaction schema
- Shared transaction model
- Shared lifecycle event model
- JSON ledger loader
- Asset-specific adapters

### v0.5 Valuation Engine

Goals:

- Unified valuation API
- Universal valuation record history
- Source priority rules
- Card Ladder valuation input
- eBay Sold valuation input
- PSA valuation input
- Yahoo Finance valuation input
- Real Estate valuation interface

### v0.6 Portfolio Aggregation and Analytics

Goals:

- Portfolio summary
- Portfolio aggregation
- Assets, Ledger, and Valuation consumption
- Analytics snapshots
- Allocation
- ROI
- IRR
- Cash Flow
- Risk

### v0.7 Business Logic Engine

Goals:

- Business Logic Context
- Metric results
- Rule-based signals
- Calculator contracts
- Evaluator contracts
- Policy configuration
- Calculator and evaluator registry
- Business Logic Pipeline Runner
- Analytics Integration
- Cash Flow Engine
- Allocation Engine
- Risk Engine
- Performance Engine

### v0.6 Dashboard Foundation

Goals:

- Service Layer
- Display-only Dashboard views
- Dashboard-ready portfolio view
- Dashboard Analytics views
- Analytics display
- Charts
- Daily summary

### v0.7 Asset Modules

- Real Estate
- Sports Cards
- Funds
- Stocks
- Cash
- Gold
- Collectibles

### v0.8 Automation

- Daily reports
- Scheduled updates
- Connector synchronization
- Import validation

### v0.9 OFAI Beta

- Scenario Planning
- OFAI context
- OFAI planner
- Decision Engine
- Risk Engine
- Allocation suggestions
- AI assistant

### v1.0 Onecool OS

- Commercial-ready architecture
- Stable APIs
- Dashboard
- Automation
- OFAI

---

## Current Sprint

Sprint 20

Status: Completed

Next Sprint:
Decision Rules Foundation
