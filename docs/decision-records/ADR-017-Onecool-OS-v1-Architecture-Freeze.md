# ADR-017 Onecool OS v1.0 Architecture Freeze

## Status

Accepted

## Context

Since 2026-06-28, Onecool OS has evolved from a small Core Engine into a
deterministic knowledge platform for personal assets. The current collectible
stack includes Asset Master, Collection Sync, RuntimeSession, Research Queue,
Research Workbench, eBay Sold Evidence, Evidence Validation, Onecool Fair
Value, Fair Value to ValuationRecord, Portfolio NAV Runtime Integration,
Dashboard 2.0, and Portfolio History.

Earlier roadmap assumptions placed scheduling, automation, batch execution,
and report generation inside Onecool OS runtime code. After the introduction
of ChatGPT Work, those assumptions should be revised before more feature
development continues.

This ADR freezes the v1.0 architecture direction. It does not change runtime
behavior, earlier ADRs, public contracts, tests, or production code. It
reclassifies responsibilities across Onecool OS, ChatGPT Work, external
providers, Runtime, and Dashboard.

## Current Architecture

Onecool OS currently owns the durable deterministic asset knowledge chain.

```text
Asset Master
PSA/BGS Collection Import
Collection Sync
RuntimeSession
Research Queue
eBay Sold Evidence
Evidence Validation
Onecool Fair Value
ValuationRecord
Portfolio NAV
Dashboard Snapshot
Portfolio History
```

Current collectible data lifecycle:

```text
Imported collection identity
+ user-owned Asset Master metadata
-> Collection Sync integrity report
-> RuntimeSession
-> Research Queue and Evidence
-> Onecool Fair Value
-> ValuationRecord
-> Portfolio NAV
-> Dashboard Snapshot
-> Portfolio History Snapshot
```

The existing ADRs remain valid:

- ADR-004 keeps Collectible Radar evidence-first and provider-independent.
- ADR-005 separates performance from lifecycle and avoids mandatory historical
  transaction backfill.
- ADR-006 through ADR-011 define research interfaces and local workbench
  artifacts without live scraping.
- ADR-012 through ADR-014 define Fair Value, ValuationRecord, and Portfolio
  NAV as deterministic runtime knowledge.
- ADR-015 keeps Dashboard display-only.
- ADR-016 keeps Portfolio History append-only and immutable.

ADR-017 changes responsibility placement for workflows, not the meaning of
those domain objects.

## Core Principle

Onecool OS owns knowledge.

ChatGPT Work owns execution.

Providers own external information.

Dashboard owns presentation.

This principle keeps the permanent intellectual property inside Onecool OS
while moving long-running, scheduled, user-facing workflow orchestration to
ChatGPT Work.

## Responsibility Matrix

| Area | Owns | Must Not Own |
| --- | --- | --- |
| Onecool OS | Asset Master, Collection Sync, Evidence, Evidence Validation, Onecool Fair Value, ValuationRecord, Portfolio NAV, Decision Rules, Research Queue, RuntimeSession, Dashboard Snapshot, Portfolio History | Long-running scheduling, notification delivery, provider credentials, final AI recommendations |
| ChatGPT Work | Daily workflows, weekly workflows, monthly workflows, batch research execution, scheduling, notifications, report generation, long-running execution, user-facing orchestration | Canonical asset identity, valuation truth, evidence validation rules, history source of truth |
| External Providers | eBay, Card Ladder, PWCC, Goldin, Fanatics, future authorized APIs, source data and external observations | Onecool canonical valuation decisions, internal history, dashboard presentation |
| Runtime | In-memory deterministic assembly of imported records, Asset Master metadata, sync report, evidence, Fair Value, valuations, NAV, research queue, dashboard snapshot, history snapshot | Scheduling, provider calls, scraping, report delivery, AI reasoning |
| Dashboard | Read-only presentation of Dashboard Snapshot and related runtime outputs | Calculations, business logic, source mutation, recommendations |

## Permanent Domain Objects

The following objects must remain inside Onecool OS because they are the
user-owned knowledge base and deterministic intellectual property of the
system:

- Asset Master: permanent user-maintained metadata and research entry points.
- Collection Sync: deterministic integrity record between imports and Asset
  Master.
- Evidence: auditable observations from approved sources.
- Evidence Validation: rules that decide whether evidence can be trusted.
- Onecool Fair Value: canonical fair-value derivation from verified evidence.
- ValuationRecord: canonical valuation object consumed by Portfolio NAV.
- Portfolio NAV: deterministic portfolio value and coverage state.
- Decision Rules: future deterministic evaluation rules.
- Research Queue: structured list of research needs and readiness state.
- Dashboard Snapshot: stable presentation contract over runtime knowledge.
- Portfolio History: immutable local history of runtime portfolio state.

These objects encode how Onecool OS understands assets, truth, evidence,
valuation, and auditability. They should be deterministic, replayable,
testable, provider-independent, and safe to preserve over time.

## Workflow Objects

The following objects should move to ChatGPT Work or be treated as Work-owned
execution artifacts:

- Daily Collection Report
- Weekly Report
- Monthly Report
- Research Execution
- Batch Research
- Notification
- Scheduled Task
- Long-running provider workflow
- Human review loop orchestration

These are workflows rather than permanent truths. They sequence work, notify
the user, run batches, assemble outputs, and coordinate review. Keeping them
outside Onecool OS runtime code avoids turning the repository into a scheduler,
notification system, or long-running operations platform.

Onecool OS may still expose stable inputs for these workflows, such as
Dashboard Snapshot, Research Queue, Portfolio History, and Decision Rules.
ChatGPT Work should consume those inputs and execute the workflow.

## Architecture Layers

### Knowledge Layer

Owner: Onecool OS

Responsibilities:

- Maintain user-owned metadata.
- Preserve evidence and validation state.
- Build deterministic valuations.
- Build NAV and history snapshots.
- Define decision rules and domain contracts.

### Execution Layer

Owner: ChatGPT Work

Responsibilities:

- Run daily, weekly, and monthly workflows.
- Execute research batches.
- Generate and deliver reports.
- Schedule repeated work.
- Coordinate human review loops.

### Presentation Layer

Owner: Dashboard

Responsibilities:

- Display snapshots and summaries.
- Preserve read-only boundaries.
- Avoid calculations and recommendations.

### External Providers

Owner: provider systems

Responsibilities:

- Supply external information through approved APIs, exports, or manual
  evidence.
- Maintain their own source data and terms.
- Never become the canonical Onecool source of truth.

Layer diagram:

```text
External Providers
-> provider exports or authorized APIs
-> Onecool OS Knowledge Layer
   -> Asset Master
   -> Evidence
   -> Onecool Fair Value
   -> ValuationRecord
   -> Portfolio NAV
   -> Dashboard Snapshot
   -> Portfolio History
-> ChatGPT Work Execution Layer
   -> research workflows
   -> scheduled reports
   -> notifications
-> Dashboard Presentation Layer
```

## Version 1.0 Scope

### Included

- Asset Master
- Collection Sync
- RuntimeSession
- Evidence models and validation
- Research Queue contracts
- Onecool Fair Value
- ValuationRecord integration
- Portfolio NAV
- Dashboard Snapshot
- Portfolio History
- Decision Rules foundation if deterministic and local
- Provider-independent contracts

### Deferred

- Multi-source provider arbitration beyond current rules
- FX Engine
- Lifecycle Engine
- Realized gain/loss
- IRR/XIRR
- Persistent database-backed history
- Production credential management
- Multi-asset GA polish beyond collectible-first scope

### Moved to Work

- Daily Collection Report generation
- Weekly and monthly reporting
- Batch research execution
- Scheduling
- Notifications
- Long-running execution
- Human review workflow orchestration

### Removed from v1.0 Runtime Scope

- Built-in scheduler as core product dependency
- Built-in notification delivery
- Runtime-owned report generation pipeline
- Runtime-owned batch execution engine
- Any LLM recommendation loop inside Onecool OS

## Release Roadmap

### v1.0 Knowledge Platform

Freeze Onecool OS as the deterministic knowledge platform. Complete stable
domain contracts for Asset Master, Evidence, Fair Value, ValuationRecord,
Portfolio NAV, Dashboard Snapshot, Portfolio History, and Decision Rules.

### v1.1 Work Integration

Define how ChatGPT Work consumes Onecool OS snapshots and queues. Build safe
handoff formats for daily workflows, batch research, and report generation.

### v1.2 Automation

Move scheduling, notifications, repeated workflows, and human review loops into
ChatGPT Work execution patterns using Onecool OS as the trusted knowledge
source.

### v2.0 Multi-source Intelligence

Expand provider integrations, source agreement, cross-provider validation,
multi-currency support, and broader asset classes while preserving the v1.0
knowledge/execution split.

## Migration Strategy

No code migration is required for ADR-017.

Current Onecool OS objects stay where they are. The change is architectural:
workflow features that were previously candidates for runtime implementation
should now be evaluated for ChatGPT Work ownership.

Existing report and CLI foundations can remain as Beta dogfooding surfaces, but
new production workflow development should prefer ChatGPT Work when the feature
is primarily scheduling, orchestration, notification, or long-running
execution.

## Future Development Rules

Every future feature must first answer:

Should this belong to Onecool OS or ChatGPT Work?

Use these criteria:

| Question | If Yes, Prefer |
| --- | --- |
| Is this a permanent domain object or source of truth? | Onecool OS |
| Is this deterministic validation or calculation? | Onecool OS |
| Is this evidence, valuation, NAV, history, or decision-rule logic? | Onecool OS |
| Is this a scheduled or repeated workflow? | ChatGPT Work |
| Is this long-running execution or batch orchestration? | ChatGPT Work |
| Is this notification or report delivery? | ChatGPT Work |
| Is this provider-owned source information? | External Provider |
| Is this read-only display? | Dashboard |

If a feature mixes categories, split it. Keep durable knowledge in Onecool OS
and execute the workflow in ChatGPT Work.

## Architecture Principles

- Evidence First
- Deterministic
- Provider Independent
- Knowledge First
- Execution Separation
- Presentation Separation
- Immutable History
- Read-only Dashboard
- Single Source of Truth
- No hidden calculations in presentation
- No provider lock-in
- No runtime-owned AI recommendations

## Impact Assessment

| Subsystem | Status | Rationale |
| --- | --- | --- |
| Core Engine | Keep | Provides local platform foundation. |
| Asset Master | Keep | Permanent user-owned metadata. |
| PSA/BGS Import | Keep | Imports source identity into Onecool knowledge. |
| Collection Sync | Keep | Integrity layer before runtime. |
| RuntimeSession | Keep | Deterministic in-memory assembly. |
| Research Queue | Keep | Knowledge object describing research needs. |
| Research Workbench | Refactor Later | Keep formats, but execution may move to Work. |
| Single Asset Pipeline | Refactor Later | Useful proof; long-running execution should move to Work. |
| eBay Sold Evidence | Keep | Evidence is canonical knowledge input. |
| Evidence Validation | Keep | Trust rules belong inside Onecool OS. |
| Onecool Fair Value | Keep | Canonical valuation logic. |
| ValuationRecord | Keep | Canonical valuation object. |
| Portfolio NAV | Keep | Deterministic portfolio value and coverage. |
| Dashboard Snapshot | Keep | Stable presentation contract. |
| Dashboard Rendering | Keep | Read-only presentation remains valid. |
| Daily Report | Move to Work | Report generation is workflow execution. |
| Weekly/Monthly Reports | Move to Work | Scheduled reporting is workflow execution. |
| Decision Queue | Keep | Review-priority knowledge object. |
| Decision Rules | Keep | Deterministic rules are domain knowledge. |
| OFAI Context | Refactor Later | Context belongs in Onecool; execution/reasoning belongs in Work or future AI layer. |
| Scheduler | Move to Work | Scheduling is execution. |
| Notifications | Move to Work | Notification delivery is execution. |
| Live Provider Calls | Refactor Later | Provider contracts stay; execution should be Work-owned or explicitly authorized. |
| Scraping | Out of Scope | Unauthorized scraping is not part of Onecool OS. |
| LLM Recommendations | Out of Scope | Future LLM reasoning must consume Onecool context and remain outside canonical truth. |
| Portfolio History | Keep | Immutable source of historical truth. |

## Appendix: One-page Architecture Diagram

```text
ONECOOL OS KNOWLEDGE PLATFORM

Asset Master
  |
  v
Collection Sync
  |
  v
Evidence
  |
  v
Onecool Fair Value
  |
  v
ValuationRecord
  |
  v
Portfolio NAV
  |
  v
Dashboard Snapshot
  |
  v
Portfolio History


CHATGPT WORK EXECUTION PLATFORM

Dashboard Snapshot / Research Queue / Portfolio History
  |
  v
Research Workflows
  |
  v
Daily / Weekly / Monthly Reporting
  |
  v
Scheduling and Notifications


EXTERNAL PROVIDERS

eBay / Card Ladder / PWCC / Goldin / Fanatics / Future APIs
  |
  v
Approved exports, manual evidence, or authorized API responses
```

## Validation

ADR-017 was reviewed against the current ADR set through ADR-016. It does not
contradict previous decisions about evidence-first valuation, provider
independence, read-only Dashboard behavior, immutable history, or deterministic
runtime outputs.

The directional change is explicit: execution-heavy workflows move to ChatGPT
Work, while permanent domain knowledge remains in Onecool OS.
