# Onecool Weekly Research Workflow v1.0

## 1. Purpose

The Onecool Weekly Research Workflow defines the official weekly operating
model for Onecool OS.

This workflow replaces ad-hoc research runs with one canonical weekly process.
It keeps responsibilities explicit:

- Onecool OS owns knowledge.
- ChatGPT Work owns execution.
- Providers supply market information.

Onecool OS remains the deterministic Knowledge Platform. It validates evidence,
calculates Onecool Fair Value, creates ValuationRecords, updates Portfolio NAV,
builds Dashboard snapshots, and preserves history.

ChatGPT Work remains the Execution Platform. It performs weekly research,
coordinates long-running tasks, gathers provider observations, and returns
structured evidence packages for Onecool OS to validate.

Providers do not own truth. They supply external market observations through
approved, user-authorized, or manually reviewed workflows.

## 2. Inputs

### Primary Input

Asset Master is the primary weekly input.

Asset Master provides:

- durable user-owned metadata
- eBay Sold search URLs
- PSA/BGS URLs
- target price metadata
- watch status
- notes
- research readiness context

The user should update Asset Master only when holdings or durable metadata
change.

### Optional Inputs

Optional weekly inputs:

- PSA Collection export
- BGS/PSA collection updates
- manual valuation files
- future provider exports
- future authorized API outputs
- prior Work results
- prior evidence packages

Optional inputs do not replace Asset Master as the weekly research control
surface.

## 3. Weekly Flow

Canonical weekly flow:

```text
Asset Master
↓
Weekly Research Package
↓
ChatGPT Work
↓
Evidence Package
↓
Evidence Validation
↓
Fair Value
↓
ValuationRecord
↓
Portfolio NAV
↓
Dashboard
↓
Weekly Collection Intelligence Report
```

Expanded responsibility flow:

1. User reviews and updates Asset Master when needed.
2. Onecool OS imports the current collection and Asset Master.
3. Onecool OS builds Collection Sync and Research Queue state.
4. Onecool OS exports a Weekly Research Package for eligible READY items.
5. ChatGPT Work executes the research package.
6. ChatGPT Work returns an Evidence Package as Work Response JSON.
7. Onecool OS imports the Evidence Package.
8. ORF validates the research payload.
9. eBay Sold Evidence Validation classifies each observation.
10. Onecool Fair Value runs only on verified evidence.
11. ValuationRecord is created only from valid Fair Value output.
12. Portfolio NAV consumes trusted ValuationRecords.
13. Dashboard presents the updated state.
14. ChatGPT Work prepares the Weekly Collection Intelligence Report from
    Onecool OS outputs.

## 4. Weekly Deliverables

Every week, the operating loop should produce:

- Portfolio Summary
- Evidence Coverage
- Research Coverage
- Fair Value Summary
- NAV Summary
- Missing Evidence
- Top Holdings
- Latest Verified Sold
- Warnings
- Action Items

### Portfolio Summary

Shows the current collection and portfolio state:

- total assets
- collection health
- collection coverage
- valued assets
- assets excluded from NAV
- runtime timestamp

### Evidence Coverage

Answers:

How much of the collection has verified market evidence?

It must show verified evidence separately from `NEEDS_REVIEW`, `REJECTED`, and
`NO_MATCH`.

### Research Coverage

Answers:

How much research has been completed?

It should separate:

- READY
- BLOCKED
- COMPLETED
- NEEDS_REVIEW
- NO_MATCH

### Fair Value Summary

Shows only deterministic Onecool Fair Value results created from verified
evidence.

It must not include guessed values, provider estimates, active listings, or
unverified Best Offer prices.

### NAV Summary

Shows Portfolio NAV based only on trusted ValuationRecords.

Missing valuation assets must be excluded from NAV, not treated as zero.

### Missing Evidence

Lists assets that still need market evidence.

Missing Evidence is a workflow issue, not an investment recommendation.

### Top Holdings

Shows top holdings by trusted market value when available.

If coverage is incomplete, the report must clearly state that top holdings only
include valued assets.

### Latest Verified Sold

Lists the newest verified sold evidence.

This section helps the owner understand what changed recently without implying
price prediction.

### Warnings

Warnings must preserve uncertainty:

- missing eBay URL
- provider unavailable
- partial research
- low confidence
- identity mismatch
- Best Offer price unknown
- missing item ID
- missing sold URL
- missing sold date
- NO_MATCH

### Action Items

Action Items are review tasks, not buy/sell recommendations.

Examples:

- add missing eBay Sold URL
- review ambiguous comparable
- rerun Work for NO_MATCH
- verify Best Offer price manually
- update Asset Master metadata

## 5. Responsibilities

### User

The user should:

- Update Asset Master only when holdings or durable metadata change.
- Confirm research URLs are user-approved.
- Review low-confidence or ambiguous evidence.
- Approve or reject uncertain evidence after validation.
- Avoid editing generated Work Response JSON unless correcting verified facts.

The user should not manually calculate NAV, Fair Value, or portfolio readiness.

### ChatGPT Work

ChatGPT Work should:

- Perform research.
- Use only approved research URLs and provider sources.
- Return Evidence Packages.
- Preserve warnings and uncertainty.
- Return `NO_MATCH` instead of guessing.
- Generate weekly report text from Onecool OS outputs.

ChatGPT Work must never:

- calculate NAV manually
- calculate Onecool Fair Value manually
- create ValuationRecords manually
- override Evidence Validation
- fabricate evidence
- recommend buy/sell actions as final truth

### Onecool OS

Onecool OS should:

- Validate evidence.
- Classify evidence deterministically.
- Calculate Onecool Fair Value.
- Create ValuationRecords.
- Update Portfolio NAV.
- Generate Dashboard state.
- Preserve history.
- Maintain metric definitions.

Onecool OS should not own scheduling, notification delivery, or long-running
provider execution.

## 6. Weekly Checklist

### Before Running Research

- [ ] Confirm latest PSA Collection export is present if collection changed.
- [ ] Confirm Asset Master is current.
- [ ] Confirm private import files remain local and ignored by Git.
- [ ] Confirm Collection Health is acceptable.
- [ ] Review Research Queue READY and BLOCKED items.
- [ ] Confirm READY items have valid eBay Sold search URLs.
- [ ] Confirm no private notes are included in Work Requests.
- [ ] Export the Weekly Research Package.

### After Import

- [ ] Import Evidence Package through Work Bridge.
- [ ] Confirm ORF validation passed.
- [ ] Confirm Evidence Validation completed.
- [ ] Review `VERIFIED`, `NEEDS_REVIEW`, `REJECTED`, and `NO_MATCH` counts.
- [ ] Confirm warnings are preserved.
- [ ] Confirm no fabricated values were accepted.
- [ ] Run Fair Value only after verified evidence exists.
- [ ] Create ValuationRecords only from valid Fair Value output.
- [ ] Update Portfolio NAV only from trusted ValuationRecords.

### Before Publishing Report

- [ ] Confirm Collection Health.
- [ ] Confirm Evidence Coverage.
- [ ] Confirm Research Coverage.
- [ ] Confirm Valuation Coverage.
- [ ] Confirm NAV Coverage.
- [ ] Confirm Portfolio Readiness.
- [ ] Confirm missing assets are excluded from NAV.
- [ ] Confirm warnings and NO_MATCH items are visible.
- [ ] Confirm action items are review tasks, not investment recommendations.
- [ ] Save or publish the weekly report through ChatGPT Work.

## 7. Failure Handling

### Missing eBay Evidence

If no evidence exists:

- keep Evidence Coverage unchanged
- do not create Fair Value
- do not create ValuationRecord
- do not update NAV for that asset
- add Missing Evidence to weekly action items

### Provider Unavailable

If a provider or source is unavailable:

- preserve the provider failure warning
- mark research as blocked or partial
- do not fabricate evidence
- retry through ChatGPT Work later

### Partial Research

If research is partial:

- import the structured response if valid
- preserve warnings
- classify evidence deterministically
- do not treat partial results as complete coverage

### NO_MATCH

If Work returns `NO_MATCH`:

- accept it as a valid workflow outcome
- preserve the reason
- do not invent comparable evidence
- decide whether the research URL or identity needs review

### Low Confidence

If evidence confidence is low:

- preserve low confidence
- classify through Evidence Validation
- route the item to review
- do not calculate Fair Value unless downstream rules allow it

## 8. Success Metrics

Weekly success should be measured using the official Metrics Framework.

### Collection Health

Question:

Can I trust my collection data?

Owner:

Collection Sync.

Weekly use:

Confirm the weekly process starts from trustworthy asset identity and metadata.

### Evidence Coverage

Question:

How much of my collection has verified market evidence?

Owner:

Evidence Validation.

Weekly use:

Measure how much research has produced trusted observations.

### Research Coverage

Question:

How much research has been completed?

Owner:

Research Queue.

Weekly use:

Track READY, BLOCKED, completed, and review-needed work.

### Valuation Coverage

Question:

How much of my portfolio has trusted Fair Values?

Owner:

Onecool Fair Value.

Weekly use:

Measure how much of the collection can produce trusted valuation records.

### NAV Coverage

Question:

How much of my portfolio contributes to trusted NAV?

Owner:

Portfolio NAV.

Weekly use:

Measure how complete the NAV picture is.

### Portfolio Readiness

Question:

How ready is this portfolio for investment decision making today?

Owner:

Decision and portfolio readiness layers.

Weekly use:

Assess whether enough research, evidence, valuation, and NAV coverage exists to
support next-step review.

## 9. Future Roadmap

### v1.0 Weekly Manual Execution

Scope:

- User updates Asset Master.
- Onecool OS exports research requests.
- ChatGPT Work executes manually.
- User imports Work Response JSON.
- Onecool OS validates evidence and updates deterministic knowledge.

### v1.1 ChatGPT Work Assisted

Scope:

- ChatGPT Work helps coordinate weekly research tasks.
- Work Response generation becomes easier.
- Weekly report drafting becomes more consistent.
- Human review remains explicit.

### v1.2 Scheduled Execution

Scope:

- ChatGPT Work owns scheduled weekly execution.
- Onecool OS continues to own validation and knowledge.
- Notifications and reminders remain Work-owned.

### v2.0 Multi-Provider Intelligence

Scope:

- Additional approved providers.
- Multi-provider evidence packages.
- Source agreement across provider evidence.
- Broader multi-asset intelligence.

Onecool OS should keep the same boundary even as the workflow grows:

```text
Providers supply observations.
ChatGPT Work executes.
Onecool OS validates, calculates, remembers, and presents trusted knowledge.
```

## Validation Notes

Terminology should remain consistent with:

- Onecool Product Vision v1.0.
- ADR-017 Architecture Freeze.
- Onecool Metrics Framework v1.0.
- Onecool Work Contract v1.0.
- Onecool Work Response Specification v1.0.

This document is a workflow specification only. It must not require production
code, Runtime, Dashboard, Research, Work Bridge, Evidence, Fair Value,
Valuation, NAV, tests, or CLI changes.
