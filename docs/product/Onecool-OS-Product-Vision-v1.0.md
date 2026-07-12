# Onecool OS Product Vision v1.0

## Product Mission

Onecool OS helps the owner understand, preserve, and act on personal asset
knowledge with deterministic, auditable, and reusable systems.

The product mission is not to replace judgment. The mission is to make the
right facts visible quickly, keep personal asset knowledge organized, and give
ChatGPT Work trusted inputs for execution.

## Product Vision

Onecool OS v1.0 is a personal knowledge operating system for assets.

It owns the durable truth layer:

- what the owner has
- what the owner knows
- what evidence supports that knowledge
- what value has been calculated deterministically
- what requires review
- what changed over time

ChatGPT Work owns the execution layer:

- what should be checked today
- what report should be generated
- what research workflow should run
- what reminder or notification should be sent
- what batch should execute next

Together, Onecool OS and ChatGPT Work form a daily operating loop:

```text
Onecool OS Knowledge
-> ChatGPT Work Execution
-> Owner Review
-> Updated Knowledge
```

## Daily User Journey

The daily Onecool OS user journey should feel calm and fast.

1. The owner opens the daily operating view.
2. Onecool OS shows the current trusted state of the collection or portfolio.
3. The owner sees what changed, what is missing, and what requires review.
4. ChatGPT Work runs or coordinates the next execution steps.
5. The owner approves, rejects, or updates knowledge.
6. Onecool OS preserves the resulting state in history.

The product should reduce mental clutter. The owner should not need to inspect
raw spreadsheets, provider pages, old notes, or scattered conversations before
understanding the current state.

## Product Principles

- Knowledge first.
- Evidence before valuation.
- Deterministic before intelligent.
- User-owned metadata stays user-owned.
- Providers supply observations, not final truth.
- Dashboard presents, never calculates.
- Runtime assembles, never schedules.
- History is immutable.
- ChatGPT Work executes, Onecool OS remembers.
- Recommendations must be explainable through underlying evidence and rules.

## Three Minute Rule

Within three minutes, Onecool OS should help the owner answer:

- What do I own?
- What is trusted?
- What is missing?
- What changed?
- What needs review?
- What is the current value based on verified evidence?
- What can ChatGPT Work execute next?

If a workflow cannot produce one of these answers within three minutes, it
should either be simplified, moved to ChatGPT Work, or clearly marked as a
long-running workflow.

## Core User Questions

Onecool OS v1.0 should be optimized around a small set of recurring questions.

### Collection and Portfolio State

- What assets are currently known?
- Which assets are enriched by Asset Master?
- Which assets are missing metadata?
- Which assets have sync conflicts?

### Evidence and Valuation

- Which assets have verified evidence?
- Which assets have no usable evidence?
- Which assets have Onecool Fair Value?
- Which valuation records are trusted?
- Which assets are excluded from NAV because valuation is missing?

### Review and Decision Readiness

- Which assets are ready for review?
- Which assets are blocked?
- Which issues are critical?
- Which issues are only metadata cleanup?
- Which decisions need more evidence before any action?

### History and Change

- What changed since the last snapshot?
- What was the portfolio state on a prior date?
- Which values were known at that time?
- Which warnings persisted across snapshots?

### Execution

- What should ChatGPT Work do today?
- Which research requests should be executed?
- Which report should be generated?
- Which reminders should be scheduled?

## Onecool OS vs ChatGPT Work Responsibilities

| Responsibility | Onecool OS | ChatGPT Work |
| --- | --- | --- |
| Asset identity | Owns | Consumes |
| Asset Master | Owns | Consumes |
| Collection Sync | Owns | Consumes |
| Evidence records | Owns | May help collect through approved workflows |
| Evidence validation | Owns | Consumes validation result |
| Onecool Fair Value | Owns | Consumes |
| ValuationRecord | Owns | Consumes |
| Portfolio NAV | Owns | Consumes |
| Dashboard Snapshot | Owns | Consumes or displays |
| Portfolio History | Owns | Consumes |
| Research Queue | Owns | Executes queued work |
| Batch research | Defines inputs | Executes |
| Daily report generation | Provides source snapshots | Executes |
| Scheduling | Does not own | Owns |
| Notifications | Does not own | Owns |
| Provider credentials | Does not own by default | Handles per workflow when authorized |
| LLM reasoning | Provides context | Executes outside source of truth |

Rule of thumb:

If the object is permanent truth, it belongs in Onecool OS.

If the object is a workflow, schedule, notification, or long-running action, it
belongs in ChatGPT Work.

## Product Roadmap After Architecture Freeze

### v1.0 Knowledge Platform

Goal: Make Onecool OS the trusted source of personal asset knowledge.

Scope:

- Asset Master
- Collection Sync
- Evidence
- Evidence Validation
- Onecool Fair Value
- ValuationRecord
- Portfolio NAV
- Dashboard Snapshot
- Portfolio History
- Research Queue
- Decision Rules foundation

Success means the owner can trust the data model, reproduce calculations, and
inspect history without relying on external conversations or raw files.

### v1.1 Work Integration

Goal: Define clean handoff between Onecool OS and ChatGPT Work.

Scope:

- Work-ready research queue export
- Work-ready daily context export
- Work-ready report inputs
- Human review loop contracts
- Safe execution boundaries

Success means ChatGPT Work can run workflows using Onecool OS as the trusted
knowledge base without duplicating business logic.

### v1.2 Automation

Goal: Move daily/weekly/monthly execution into repeatable Work patterns.

Scope:

- Scheduled review workflows
- Report generation workflows
- Research batch workflows
- Notification workflows
- Owner approval checkpoints

Success means Onecool OS does not become a scheduler, while the owner still
gets reliable automated execution.

### v2.0 Multi-source Intelligence

Goal: Expand from collectible-first knowledge to multi-source personal asset
intelligence.

Scope:

- More provider integrations
- Multi-currency support
- Additional validation sources
- Broader asset classes
- Cross-asset intelligence
- More advanced decision rules

Success means Onecool OS can support the owner's wider asset world without
losing deterministic boundaries.

## Success Metrics for v1.0

### Trust Metrics

- 100% of committed calculations are deterministic and replayable.
- 100% of trusted valuations trace back to evidence or explicit source input.
- 0 hidden provider calls inside Dashboard or Runtime.
- 0 private user data committed to Git.

### Coverage Metrics

- Asset Master coverage is visible.
- Collection Sync health is visible.
- Evidence coverage is visible.
- Valuation coverage is visible.
- NAV coverage is visible.
- History snapshot coverage is visible.

### Speed Metrics

- The daily state can be understood within three minutes.
- Missing valuation assets can be identified within three minutes.
- Critical review items can be identified within three minutes.
- Work handoff targets can be identified within three minutes.

### Boundary Metrics

- Dashboard performs no calculations.
- Runtime performs no scheduling.
- Onecool OS does not own notification delivery.
- ChatGPT Work does not become the source of valuation truth.

### Product Quality Metrics

- The owner can explain why an asset has or does not have a trusted value.
- The owner can identify which assets need review today.
- The owner can compare current state against historical snapshots.
- The owner can hand execution to ChatGPT Work without losing source-of-truth
  integrity.

## Product Definition

Onecool OS v1.0 is successful when it becomes the owner's trusted asset memory:
structured enough for machines, clear enough for humans, and durable enough to
support daily decision workflows without becoming the execution system itself.

