# ADR-008 Research Queue

Status: Accepted

## Context

Collectible Radar now has PSA/BGS import, Asset Master, Collection Sync,
RuntimeSession, eBay Sold Evidence, Valuation Runtime, Portfolio NAV, and the
Onecool Research Framework. The next step is deciding which assets should be
sent to future research providers and why.

Without a deterministic queue, provider execution would be tempted to decide
priority, evidence readiness, and valuation gaps on its own. That would mix
planning, provider behavior, evidence creation, valuation creation, and
presentation concerns.

## Decision

Onecool OS introduces Research Queue as a deterministic planning layer between
RuntimeSession and future provider execution.

Research Queue consumes:

- RuntimeSession enriched collectible assets
- Asset Master research entry points
- Collection Sync differences
- Existing eBay Sold evidence status
- Existing ValuationRecord history
- Portfolio NAV valuation coverage when supplied

Research Queue produces:

- ResearchQueueSnapshot
- ResearchQueueItem
- Priority
- Status
- Reasons
- Blocking reasons
- Evidence counts
- Valuation coverage status

Research Queue does not:

- call providers
- scrape websites
- create evidence
- create valuation records
- calculate NAV
- recommend buy/sell actions
- predict prices
- mutate RuntimeSession
- mutate Asset Master
- change Dashboard, Daily Report, Decision Queue, or OFAI behavior

## Priority Rules

CRITICAL is reserved for blockers such as ambiguous identity, duplicate cert
or duplicate asset conflicts, critical Collection Sync identity conflicts, and
invalid source URLs that block required research.

HIGH is used for no verified valuation on core holdings, review or rejected
evidence with no trusted alternative, no-match evidence, supporting-estimate
only coverage, and multiple eligible valuation records requiring human source
review.

MEDIUM is used for missing eBay research URL, watchlist or target-price review,
manual research request, and metadata-oriented Collection Sync issues.

LOW is used for non-core assets that lack verified valuation but still have a
usable research entry point and no blocking identity issue.

INFORMATIONAL is used when verified valuation coverage already exists and no
immediate research action is needed.

## Blocking Rules

A queue item is BLOCKED when it has no usable identity, an ambiguous match, an
invalid source URL, no search entry point and no query-generation identity, or
a critical Collection Sync identity conflict.

A queue item is READY when it has a known research type, usable identity, at
least one research entry point or enough identity to form a query later, and
no critical blocker.

A queue item is COMPLETED when it is informational and no immediate research
action is needed.

## Grouping Rules

For each reference period, Research Queue should produce one open item per
asset and research type. Duplicate reasons are merged deterministically.
Ordering is deterministic by priority, blocked state, asset name, cert number,
and queue item id.

## Runtime Impact

RuntimeSession exposes helper methods to build research queue snapshots and
filter open, ready, blocked, and critical research items. These helpers
delegate to ResearchQueueEngine and do not store or mutate queue output.

## Privacy

Research Queue may carry asset IDs, cert numbers, asset names, URLs, counts,
status, and warnings. It must not print private notes, raw rows, complete
metadata dictionaries, provider credentials, or source file contents.

## Consequences

Research providers can later consume queue items without re-deciding what
needs research. Evidence and valuation remain independent layers. Dashboard,
Daily Report, Decision Queue, and OFAI can later display or consume Research
Queue output through explicit integration sprints.

## Alternatives Considered

Provider-driven prioritization was rejected because it would couple provider
behavior to portfolio state.

Dashboard-driven prioritization was rejected because Dashboard is
presentation-only.

Decision Queue reuse was rejected because Decision Queue prioritizes review
work after reports, while Research Queue prioritizes market research before
provider execution.
