# ADR-011 Single Asset Research Pipeline

Status: Accepted

## Context

Onecool OS can import PSA/BGS collection data, load Asset Master URLs, build a
RuntimeSession, prioritize Research Queue work, export eBay Sold URL research
requests, import ORF-compatible provider JSON, and validate eBay Sold
evidence. The missing proof is a real asset moving through the complete
research and evidence attachment loop without scraping or provider automation.

The first target asset is:

- 2008 TOPPS #24 KOBE BRYANT
- Grade Issuer: PSA
- Grade: 9
- Cert Number: 111003720

## Decision

Onecool OS introduces a single-asset research pipeline for one collectible
asset. The pipeline starts from local RuntimeSession data and ends with
validated eBay Sold evidence attached to a new RuntimeSession instance.

Flow:

```text
Asset Master
↓
Research Queue
↓
Research Request JSON
↓
Externally supplied provider result JSON
↓
ORF Validation
↓
eBay Sold Evidence Validation
↓
RuntimeSession Evidence Attachment
↓
Evidence Review Output
```

## Boundaries

The pipeline does not:

- scrape eBay
- call Gemini
- call ChatGPT
- call external APIs
- automate a browser
- fabricate sold data
- calculate median or average
- calculate Onecool Fair Value
- create ValuationRecord directly
- update NAV
- calculate ROI
- recommend buy, hold, or sell
- modify Asset Master
- commit private input or output files

## Two-Stage Behavior

If provider result JSON is missing, the pipeline exports exactly one research
request and exits successfully with `PipelineStatus.PARTIAL`.

If provider result JSON exists, the pipeline imports it through the Research
Workbench, validates it through ORF, bridges it into eBay Sold Evidence, lets
the existing evidence validator classify each record, attaches the resulting
evidence batch to a new RuntimeSession, and reports evidence counts.

## Evidence Trust

Provider output remains untrusted. ORF validation and eBay Sold Evidence
validation are mandatory. Evidence attachment does not automatically create a
valuation record and does not update Portfolio NAV.

## Consequences

This one-asset pipeline becomes the template for future batch research
execution. Batch execution should reuse the same boundaries and should not
bypass Research Queue, Research Workbench, ORF validation, or evidence
validation.
