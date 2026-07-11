# ADR-006 Onecool Research Framework

## Status

Proposed

## Context

Onecool OS now supports PSA/BGS import, Asset Master, Collection Sync,
RuntimeSession, runtime valuation providers, eBay Sold Evidence, Dashboard,
Daily Report, Decision Queue, and OFAI Context. Future research sources may
include ChatGPT, Gemini, official eBay APIs, Card Ladder, authorized
third-party data providers, and manually supplied structured research.

Without a shared abstraction, provider output could bypass evidence
validation or couple external providers directly to RuntimeSession,
Valuation, Dashboard, Decision Queue, or OFAI. That would create duplicate
sources of truth and make provider-specific behavior hard to audit.

## Decision

Create the Onecool Research Framework as the universal external research
abstraction layer.

External providers must produce immutable `ResearchResult` and
`ResearchEvidence` records. ORF normalizes provider identity, provider
version, confidence, status, URLs, currency, dates, evidence identifiers,
warnings, and metadata. ORF validates provider metadata, supported provider
types, research types, capabilities, duplicate evidence IDs, malformed URLs,
malformed dates, malformed observed values, unsupported currencies,
status/evidence consistency, and warning requirements.

Provider output is untrusted by default. ORF never calculates final valuation,
selects the correct marketplace, recommends actions, mutates source data,
mutates RuntimeSession, or bypasses existing evidence validation.

## Architecture

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

For collectible sold comparable research, compatible `SOLD_COMPARABLES`
evidence may bridge into `EbaySoldEvidence`. The bridge preserves provider
name, provider version, source URL, item ID, observed value, currency,
observed date, confidence, warnings, match fields, mismatch fields, and
metadata. The existing eBay Sold Evidence layer remains responsible for
classifying evidence as verified, review-only, rejected, or no-match.

## Boundaries

ORF owns:

- Provider-independent research request and result models
- Provider registry
- Deterministic normalization
- Deterministic validation
- Local JSON loading
- Bridge into existing evidence layers

ORF does not own:

- Live API execution
- Browser automation
- Scraping
- Credential storage
- Final valuation
- Source agreement
- Market intelligence
- Dashboard presentation
- Decision recommendations
- OFAI reasoning

## Consequences

AI providers become replaceable adapters instead of system dependencies.
Provider output remains auditable and cannot directly influence valuation or
presentation without deterministic validation.

The tradeoff is an additional intermediate layer before valuation records are
created. This is intentional: research output and market evidence are related
but not the same source of truth.

## Future Work

- Research Result JSON Import CLI
- Provider-specific adapters for approved APIs or manual exports
- Persistent research audit store
- Provider credential review
- Additional bridges for future evidence types
