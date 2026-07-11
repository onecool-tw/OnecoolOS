# ADR-009 eBay URL Research PoC

Status: Accepted

## Context

Asset Master now stores durable eBay Sold search URLs for collectible assets.
Those URLs are stable research entry points, but they are not valuation
evidence by themselves. Onecool OS needs a safe way to package research work
for external providers while preserving deterministic validation boundaries.

## Decision

Onecool OS introduces an eBay Sold URL Research PoC under the Research
Workbench.

The PoC flow is:

```text
RuntimeSession
↓
Research Queue READY item
↓
Asset Master eBay Sold Search URL
↓
Research Request Export
↓
External Provider
↓
ORF-compatible JSON
↓
Research Result Import
↓
ORF Validation
↓
eBay Sold Evidence Validation
```

The workbench exports `EbayUrlResearchRequest` packages from READY Research
Queue items. Each package includes asset identity, the eBay Sold search URL,
required result fields, provider capability, reference time, and a provider
instruction template.

The workbench imports provider-returned JSON through the existing Onecool
Research Framework loader and validation. Compatible `SOLD_COMPARABLES`
evidence is then bridged into existing `EbaySoldEvidence` objects, where the
eBay evidence validator decides whether output is VERIFIED, NEEDS_REVIEW,
REJECTED, or NO_MATCH.

## Boundaries

The PoC does not:

- scrape eBay
- make HTTP requests
- call Gemini
- call ChatGPT
- call eBay APIs
- automate a browser
- fabricate sold records
- create ValuationRecord directly
- calculate NAV
- modify Asset Master
- commit private files

Provider output remains untrusted. Provider confidence cannot override ORF or
eBay evidence validation.

## Request Export Contract

Request export includes only READY Research Queue items with valid eBay Sold
Search URLs. BLOCKED items, missing URL items, and duplicate asset/research
type items are excluded. Export supports limit, asset-id, cert-number, and a
custom output path.

Suggested private output:

```text
imports/research/ebay_url_requests.json
```

## Result Import Contract

Provider result JSON must be ORF-compatible. It may contain one
`ResearchResult`, one `ResearchBatch`, or multiple batches. Result import must
never bypass ORF validation or eBay evidence validation. Missing sold URL,
missing item ID, missing price, or missing sold date cannot become VERIFIED.

Suggested private input:

```text
imports/research/ebay_url_results.json
```

## Consequences

This creates the smallest viable semi-automatic research loop without adding a
live provider. Full automatic retrieval requires a separately approved
provider adapter and legal ingestion review.
