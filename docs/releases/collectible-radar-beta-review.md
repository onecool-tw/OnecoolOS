# Collectible Radar Beta Release Review

Collectible Radar Beta is the first product workflow built on Onecool OS. It
proves that the platform can ingest user-approved collectible data, normalize
market observations, preserve valuation history, assess source agreement,
produce deterministic intelligence, and assemble user-facing review outputs
without live APIs, scraping, recommendations, or AI reasoning.

## Beta Release Summary

Collectible Radar Beta is ready for controlled beta use with synthetic fixtures
and user-provided local files. The release is deterministic, auditable, and
pipeline-oriented.

Beta scope:

- import PSA Collection CSV exports
- import eBay Sold manual CSV / JSON observations
- import Card Ladder manual CSV / JSON observations
- import Manual Valuation CSV / JSON observations
- preserve source records and valuation history
- evaluate Source Agreement
- produce Market Intelligence and Collectible Intelligence
- detect Radar changes
- summarize Timeline Analytics
- assemble Dashboard and Daily Radar Report payloads
- prioritize review work through Decision Queue
- prepare OFAI Context
- protect the end-to-end pipeline with a synthetic Golden Dataset

Beta does not provide live marketplace integration, credential storage,
recommendations, market prediction, scheduling, or persistent audit storage.

## Completed Capabilities

- `PSACollectionImporter` for read-only PSA Collection CSV ingestion
- `EbaySoldManualImporter` for Primary Market Price observations
- `CardLadderManualImporter` for Validation Source observations
- `ManualValuationImporter` for user-provided fallback / validation valuations
- reusable `ImportAudit` metadata for imports
- `CollectibleMarketRecord` as the normalized market observation contract
- `CollectibleValuationMapper` for mapping observations to valuation history
- `SourceAgreementResult` for deterministic agreement analysis
- `MarketIntelligence` with Source Agreement v2 integration
- `CollectibleIntelligenceEngine` for collectible-specific quality signals
- reusable Radar snapshots
- reusable Timeline Analytics snapshots
- Collectible Dashboard display models
- Daily Radar Report structured output
- Decision Queue review prioritization
- Collectible OFAI Context preparation
- Golden Dataset regression coverage

## Full Pipeline Review

### PSA Import

PSA Import is the first production-ready collection ingestion path. It reads
local user-provided PSA Collection CSV exports, validates cert numbers and
grades, preserves collection identifiers, emits normalized sports card asset
records, and creates `ImportSummary` plus `ImportAudit`.

It does not calculate valuation, mutate source files, mutate Ledger, mutate
valuation history, or make recommendations.

### eBay Sold Import

eBay Sold Manual Import accepts user-provided CSV / JSON observations. eBay
Sold remains the sports-card Primary Market Price because completed sales are
the closest executable market signal in the current strategy.

The importer emits `CollectibleMarketRecord` records and preserves external
IDs, URL/reference fields, source identity, sale price, currency, date, and raw
payload when allowed.

### Card Ladder Import

Card Ladder Manual Import accepts user-provided CSV / JSON observations as a
Validation Source. It does not replace eBay Sold, choose final valuation,
calculate confidence, or hide disagreement.

### Manual Valuation Import

Manual Valuation Import accepts user-provided CSV / JSON valuation observations
as independent valuation records. Manual valuations are fallback / validation
inputs. They never overwrite valuation history and never replace eBay Sold.

### Valuation Records

Valuation records are immutable historical observations. Multiple records can
exist for the same asset and date when they come from different sources.

### Source Agreement

Source Agreement compares eBay Sold Primary Market Price records with
Validation Sources such as Card Ladder, Manual, PWCC, Goldin, and Fanatics. It
produces agreement score, level, spread, max divergence, source count, missing
sources, warnings, and raw valuation IDs.

It does not choose final valuation.

### Market Intelligence

Market Intelligence v2 consumes optional `SourceAgreementResult`. When
provided, it uses the Source Agreement score, level, participating sources,
missing sources, and warnings without recalculating agreement.

Market Intelligence still owns market data quality summaries such as Primary
Market Price presence, freshness, coverage, liquidity, and confidence
breakdown.

### Collectible Intelligence

Collectible Intelligence consumes Market Intelligence and produces
collectible-specific deterministic quality signals. It does not recommend buy,
sell, hold, or target price actions.

### Radar

Radar compares current and previous collectible intelligence states. It
detects new, changed, resolved, and escalated signals without prediction.

### Timeline Analytics

Timeline Analytics summarizes historical Radar snapshots into deterministic
trend direction, trend strength, signal counts, and quality trend summaries.

### Dashboard

Dashboard is display-only. It assembles Business Logic, Radar, Timeline, and
Decision outputs into presentation models without recalculating confidence,
trend, valuation, quality, or recommendations.

### Daily Radar Report

Daily Radar Report is the first end-user product output. It consumes Dashboard
payloads and assembles collection summary, market summary, today's changes,
timeline summary, review queue, and warnings.

### Decision Queue

Decision Queue prioritizes review work from deterministic warnings and report
items. It classifies review items into critical, high, medium, and low groups.
It does not recommend buy or sell decisions.

### OFAI Context

Collectible OFAI Context prepares structured deterministic context for future
OFAI workflows. It is not an AI model and does not call LLMs.

### Golden Dataset

The Golden Dataset contains synthetic fixture inputs and expected outputs for
the deterministic Collectible Radar pipeline. It protects regression coverage
without private user data, APIs, scraping, or live services.

### ImportAudit

ImportAudit records import metadata, source filename, reference time,
statistics, warnings, and checksum when available. It must not store private
raw payloads or mutate source files.

## Layer Responsibility Review

| Layer | Responsibility |
| --- | --- |
| Connector | Import user-approved local source files and preserve source identity |
| Normalize | Standardize connector output into canonical records |
| Assets | Describe collectible identity and inventory metadata |
| Valuation | Preserve immutable valuation history |
| Source Agreement | Evaluate agreement between Primary Market Price and Validation Sources |
| Market Intelligence | Evaluate market data quality and confidence context |
| Collectible Intelligence | Produce collectible-specific quality signals |
| Radar | Detect meaningful changes over time |
| Timeline Analytics | Summarize historical Radar snapshots |
| Dashboard | Present existing outputs only |
| Daily Report | Assemble user-facing report payloads |
| Decision Queue | Prioritize deterministic review work |
| OFAI Context | Prepare structured context for future OFAI workflows |
| Golden Dataset | Protect deterministic regression coverage |

## Public Contract Review

The following surfaces are stable enough for Beta integration and should remain
backward compatible unless a future release explicitly announces a breaking
change:

- `ImportAudit`
- `PSACollectionImporter`
- `EbaySoldManualImporter`
- `CardLadderManualImporter`
- `ManualValuationImporter`
- `CollectibleMarketRecord`
- `CollectibleValuationMapper`
- `SourceAgreementResult`
- `MarketIntelligence`
- `CollectibleIntelligenceEngine`
- `RadarSnapshot`
- `TimelineSnapshot`
- `CollectibleDashboard`
- `CollectibleDailyRadarReport`
- `DecisionQueue`
- `CollectibleOFAIContext`

## Known Limitations

- Multi-currency source agreement is not yet supported.
- Live API integration is not yet implemented.
- Credential storage is not yet reviewed.
- Official eBay and Card Ladder terms are not finalized.
- Scheduling is not yet implemented.
- Persistent audit store is not yet implemented.
- Dashboard is structured-data only; there is no web UI yet.
- Decision Queue prioritizes review work but does not recommend actions.
- OFAI Context prepares deterministic context but does not call LLMs.

## Technical Debt

- Market Intelligence still supports legacy internal agreement behavior when a
  `SourceAgreementResult` is not provided.
- Import summaries are similar across importers and may later deserve a shared
  base contract.
- ImportAudit exists as a model but is not persisted to a durable audit store.
- Golden Dataset coverage should expand as more source fixtures are added.
- Currency conversion policy should be designed before multi-currency source
  agreement.

## Beta Checklist

- [x] Source files remain local and user-approved.
- [x] No live APIs are called.
- [x] No scraping is implemented.
- [x] No credentials are stored.
- [x] Private user data is not committed.
- [x] Source identity is preserved.
- [x] Valuation history is append-only in design.
- [x] Source disagreement remains visible.
- [x] Decision Queue does not recommend actions.
- [x] OFAI Context does not call LLMs.
- [x] Golden Dataset is synthetic and safe to commit.
- [x] Full test suite passes.

## GA Readiness Checklist

- [ ] Review official eBay API/export terms.
- [ ] Review official Card Ladder API/export terms.
- [ ] Design credential storage before any live connector.
- [ ] Add persistent ImportAudit storage.
- [ ] Add scheduler-based import/report orchestration.
- [ ] Define multi-currency source agreement policy.
- [ ] Add user-facing Dashboard UI.
- [ ] Add operational error reporting for imports.
- [ ] Add versioned public contract documentation.
- [ ] Add release tag and artifact checklist.

## Recommended Next Steps

1. Prepare `v0.3.0-beta` release tag and release notes.
2. Freeze public contracts listed in this review for Beta consumers.
3. Add persistent audit storage design.
4. Add scheduler design for daily radar report generation.
5. Expand Golden Dataset with additional source disagreement examples.
6. Review official eBay and Card Ladder ingestion terms before live
   integration.

