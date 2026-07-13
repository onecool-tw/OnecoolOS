# ADR-018 Collection Health Trust Model

## Status

Accepted

## Context

The first real-world collection trial imported 50 cards and matched all 50
cards, but the previous Collection Health model reported:

- Old score: 0
- Critical issues: 51
- Total differences: 109

Investigation showed that most critical issues were normalization differences,
metadata completeness gaps, or decision metadata gaps rather than true identity
failures. The old model treated Collection Health as a difference counter and
set the score to zero when any critical difference existed.

That behavior made the score misleading. A fully matched collection should not
look completely untrustworthy just because many fields require cleanup.

## Decision

Collection Health is now a trust indicator.

It measures whether the collection data can be trusted for runtime use. It is
not a raw difference counter.

Collection differences are classified into trust categories:

- Identity
- Normalization
- Metadata
- Decision
- Evidence

The health score is a weighted trust score:

| Component | Weight | Rationale |
| --- | ---: | --- |
| Identity Integrity | 50% | Identity determines whether records refer to the correct asset. |
| Metadata Completeness | 20% | Metadata improves usability but does not define identity. |
| Runtime Readiness | 20% | Runtime needs imports and Asset Master records to match cleanly. |
| Evidence Readiness | 10% | Evidence inputs prepare valuation research but do not define identity. |

## Difference Categories

### Identity

Identity issues directly affect trust.

Examples:

- duplicate cert number
- duplicate asset id
- missing imported record
- missing Asset Master record
- new imported card without Asset Master record
- year mismatch
- set mismatch
- card number mismatch
- player mismatch
- grade mismatch
- grade issuer mismatch

Identity issues may be `HIGH` or `CRITICAL` and can move Health State to
`CRITICAL` even when the numeric score is not zero.

### Normalization

Normalization differences are formatting or representation gaps.

Examples:

- variety formatting
- parallel spelling
- whitespace
- case
- known aliases
- display names
- importer formatting

Normalization differences should normally be `INFO` or `LOW`. They should not
heavily reduce Collection Health unless Onecool OS cannot confidently reconcile
the records.

### Metadata

Metadata completeness affects usability but not identity.

Examples:

- missing PSA URL
- missing durable reference metadata

Metadata issues should not be `CRITICAL` unless they make identity impossible
to verify.

### Decision

Decision metadata belongs to the Decision Layer and should not reduce
Collection Health.

Examples:

- target price
- decision notes
- personal tags
- watchlist
- priority
- explicit cost override metadata

These fields may still be reported, but they do not make the collection less
trustworthy as collection data.

### Evidence

Evidence readiness measures whether future valuation research can run.

Examples:

- missing eBay Sold search URL
- missing future marketplace identifier

Evidence readiness affects valuation workflow readiness, not identity trust.

## Health States

| State | Meaning |
| --- | --- |
| EXCELLENT | Collection data is highly trustworthy. |
| GOOD | Collection data is trustworthy with minor cleanup remaining. |
| FAIR | Collection data is usable, but review is recommended. |
| ATTENTION | Collection data needs review before full trust. |
| CRITICAL | Collection data has trust issues that must be resolved. |

Health State is not only a numeric label. If Identity Integrity falls below the
trust threshold, the state becomes `CRITICAL` even if metadata or evidence
components remain healthy.

## Health Report

Collection Sync now exposes grouped issue sections:

- Identity
- Normalization
- Metadata
- Decision
- Evidence

Each group includes:

- issue count
- highest severity
- recommended action

The grouped report helps the owner understand what kind of cleanup is needed.
It avoids mixing identity failures with low-risk metadata tasks.

## Boundaries

This ADR does not change:

- Asset Master ownership
- Runtime architecture
- Evidence
- Fair Value
- Valuation
- Dashboard layout
- Providers

Dashboard may continue to display existing Collection Health fields. The
underlying SyncReport now carries richer trust categories and grouped report
metadata.

## Real Data Trial Summary

The baseline trial reported:

- Imported cards: 50
- Matched cards: 50
- Old Health Score: 0
- Old Critical Issues: 51
- Old Total Differences: 109

Under the trust model, the same style of differences should be interpreted by
category:

- identity issues affect trust directly
- normalization issues are low-impact unless unreconciled
- metadata issues affect completeness
- decision metadata does not reduce health
- evidence readiness affects research readiness

Only aggregate counts should be printed in trial summaries. Private asset
names, notes, raw metadata, and personal file contents must not be printed.

## Consequences

Collection Health is now more useful as a daily trust signal.

Users can distinguish:

- real identity problems
- harmless normalization cleanup
- metadata completeness tasks
- decision-layer fields
- evidence-readiness gaps

This improves dashboard trust, runtime interpretation, and future ChatGPT Work
handoff without changing the source-of-truth boundaries.

