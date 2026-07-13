# Onecool Metrics Framework v1.0

## Purpose

The Onecool Metrics Framework defines one consistent language for every score,
coverage, health indicator, readiness metric, and performance metric used
across Onecool OS.

The goal is simple: every metric must tell the owner exactly what question it
answers and what it does not answer.

## Design Philosophy

Every metric must answer exactly one question.

Metrics must never overlap.

Metrics must never mix data quality with investment quality.

A metric should have:

- one question
- one calculation owner
- one presentation owner
- one update frequency
- explicit dependencies
- explicit exclusions

If a number tries to answer more than one question, split it into multiple
metrics.

## Naming Rules

Health = trust.

Coverage = completeness.

Readiness = usability.

Performance = investment result.

These terms must not be mixed.

Examples:

- Collection Health asks whether collection data can be trusted.
- Evidence Coverage asks how much verified evidence exists.
- Portfolio Readiness asks whether the portfolio can support decisions today.
- Investment Performance asks what investment result has occurred.

## Collection Health

Question answered:

Can I trust my collection data?

Measures only:

- identity integrity
- metadata integrity
- synchronization integrity

Must not include:

- evidence
- valuation
- NAV
- investment performance
- market quality
- decision recommendations

Calculation owner:

Collection Sync.

Presentation owner:

Dashboard.

Update frequency:

Whenever collection import or Asset Master changes.

Dependencies:

- imported collection records
- Asset Master records
- deterministic sync rules

Collection Health is a trust signal. It should tell the owner whether the
system is looking at the right assets with sufficiently consistent metadata.
It should not become a proxy for valuation quality.

## Collection Coverage

Question answered:

How complete is my collection database?

Measures:

- imported assets
- Asset Master completeness
- matching completeness

Does not measure:

- evidence coverage
- valuation coverage
- NAV coverage
- investment performance

Calculation owner:

Collection Sync.

Presentation owner:

Dashboard.

Update frequency:

Whenever collection import or Asset Master changes.

Dependencies:

- imported collection records
- Asset Master records
- matching rules

Collection Coverage is a completeness metric. A collection can have high
coverage and still have low valuation coverage.

## Evidence Coverage

Question answered:

How much of my collection has verified market evidence?

Measures:

- assets with verified evidence
- verified evidence only

Does not measure:

- valuation
- NAV
- research queue
- provider availability
- unverified evidence
- rejected evidence
- needs-review evidence

Calculation owner:

Evidence Validation.

Presentation owner:

Dashboard.

Update frequency:

Whenever evidence is imported, validated, or attached to runtime.

Dependencies:

- evidence records
- evidence validation rules
- asset identity

Evidence Coverage is not Valuation Coverage. Evidence may exist before a
trusted Fair Value is created.

## Research Coverage

Question answered:

How much research has been completed?

Measures:

- completed research
- ready queue
- blocked queue

Does not measure:

- verified evidence
- valuation
- NAV
- investment quality

Calculation owner:

Research Queue.

Presentation owner:

Dashboard and ChatGPT Work handoff views.

Update frequency:

Whenever Research Queue is rebuilt or research results are imported.

Dependencies:

- Asset Master
- Collection Sync
- evidence state
- valuation state
- research readiness rules

Research Coverage tracks workflow progress. It does not prove that verified
market evidence exists.

## Valuation Coverage

Question answered:

How much of my portfolio has trusted Fair Values?

Measures:

- Onecool Fair Value availability
- trusted Fair Value outputs only

Does not measure:

- raw evidence availability
- untrusted estimates
- NAV contribution
- collection metadata completeness

Calculation owner:

Onecool Fair Value Engine.

Presentation owner:

Dashboard.

Update frequency:

Whenever verified evidence changes or Fair Value is rebuilt.

Dependencies:

- verified evidence
- comparable selection
- fair-value rules
- evidence quality score

Valuation Coverage exists after Evidence Coverage. Verified evidence is the
input; trusted Fair Value is the valuation output.

## NAV Coverage

Question answered:

How much of my portfolio contributes to trusted NAV?

Measures:

- assets with trusted ValuationRecord
- assets included in Portfolio NAV

Does not measure:

- collection completeness
- evidence completeness
- Fair Value availability before ValuationRecord creation
- investment performance

Calculation owner:

Portfolio NAV Engine.

Presentation owner:

Dashboard.

Update frequency:

Whenever trusted ValuationRecords or runtime assets change.

Dependencies:

- RuntimeSession
- ValuationRecord
- NAV rules

NAV Coverage is downstream from Valuation Coverage. Missing assets are excluded
from trusted NAV, not treated as zero.

## Portfolio Readiness

Question answered:

How ready is this portfolio for investment decision making today?

Uses:

- Research Coverage
- Evidence Coverage
- Valuation Coverage
- NAV Coverage

Does not use:

- Collection Health

Calculation owner:

Future Decision Rules or Portfolio Readiness layer.

Presentation owner:

Dashboard and ChatGPT Work handoff views.

Update frequency:

Whenever research, evidence, valuation, or NAV changes.

Dependencies:

- Research Queue
- Evidence Validation
- Onecool Fair Value
- ValuationRecord
- Portfolio NAV

Portfolio Readiness is a usability metric. It should answer whether the owner
has enough downstream information to make an investment decision today.

Collection Health is excluded because it answers a different question: whether
the collection data itself can be trusted. A collection may be trustworthy but
not ready for investment decisions because it lacks evidence or valuation.

## Dashboard Principles

Every dashboard metric must state:

- Question
- Calculation owner
- Presentation owner
- Update frequency
- Dependency

Dashboard must not calculate metrics. Dashboard presents metrics calculated by
their owning layer.

Dashboard should display related metrics side by side without merging them.

Example:

| Metric | Question | Calculation Owner | Presentation Owner | Update Frequency | Dependency |
| --- | --- | --- | --- | --- | --- |
| Collection Health | Can I trust my collection data? | Collection Sync | Dashboard | Import or Asset Master change | Import + Asset Master |
| Evidence Coverage | How much has verified evidence? | Evidence Validation | Dashboard | Evidence import or validation | Evidence records |
| Valuation Coverage | How much has trusted Fair Value? | Fair Value Engine | Dashboard | Fair Value rebuild | Verified evidence |
| NAV Coverage | How much contributes to trusted NAV? | Portfolio NAV Engine | Dashboard | ValuationRecord or runtime change | ValuationRecord |
| Portfolio Readiness | Is it decision-ready today? | Future Readiness layer | Dashboard / Work | Downstream state change | Research + Evidence + Valuation + NAV |

## Metric Relationships

The metric relationship follows the data lifecycle:

```text
Collection
↓
Evidence
↓
Valuation
↓
NAV
↓
Decision
```

Each layer depends on the previous layer:

- Collection establishes asset identity and metadata trust.
- Evidence attaches verified market observations.
- Valuation converts verified evidence into trusted Fair Value.
- NAV converts trusted ValuationRecords into portfolio value.
- Decision uses downstream readiness to support review and action planning.

The layers should not collapse into one score. A single score hides the reason
the portfolio is or is not usable today.

## Future Metrics

Reserved metric names:

- Decision Readiness
- Market Coverage
- Provider Coverage
- Automation Coverage
- Work Coverage
- Historical Coverage
- Lifecycle Coverage
- FX Coverage
- Source Agreement Coverage
- Report Readiness

These names are reserved to avoid future overlap.

Future metrics must define their question before implementation.

## Product Examples

Current real portfolio example:

| Metric | Example Value | Meaning |
| --- | ---: | --- |
| Collection Health | 98 | The collection database is trustworthy with minor cleanup remaining. |
| Collection Coverage | 100% | The imported collection and Asset Master are fully matched. |
| Evidence Coverage | 0% | No assets currently have verified market evidence. |
| Valuation Coverage | 0% | No assets currently have trusted Onecool Fair Value. |
| NAV Coverage | 0% | No assets currently contribute to trusted NAV. |
| Portfolio Readiness | 5% | The portfolio is structurally organized but not ready for investment decisions. |

These values are all simultaneously correct.

Why:

- The collection can be complete and trustworthy.
- The collection can still have no verified evidence.
- Without verified evidence, there is no trusted Fair Value.
- Without trusted ValuationRecords, there is no trusted NAV.
- Without evidence, valuation, and NAV, investment decision readiness remains
  low.

This is the core reason metrics must not overlap.

## Future Dashboard Concept

Conceptual dashboard:

```text
Onecool Portfolio Metrics
-------------------------

Trust
  Collection Health: 98
  Health State: GOOD

Completeness
  Collection Coverage: 100%
  Evidence Coverage: 0%
  Valuation Coverage: 0%
  NAV Coverage: 0%

Usability
  Research Coverage: 0%
  Portfolio Readiness: 5%

Investment Result
  NAV: N/A
  Performance: N/A

Execution Handoff
  Work Coverage: Future
  Next ChatGPT Work Action: Research verified market evidence
```

No UI implementation is implied by this concept.

## Architecture Alignment

This framework aligns with Product Vision v1.0:

- Onecool OS owns knowledge.
- ChatGPT Work owns execution.
- Dashboard presents, never calculates.
- Runtime assembles, never schedules.
- Evidence before valuation.
- History is immutable.

This framework also aligns with ADR-017:

- permanent domain metrics remain in Onecool OS
- workflow and automation metrics move toward ChatGPT Work
- Dashboard remains the presentation layer
- providers supply external information, not Onecool truth

## Final Rule

If a metric cannot be explained in one sentence, it is not ready.

If a metric mixes trust, completeness, usability, and investment result, it
must be split.

