# ADR-016 Portfolio History and Snapshots

Status: Accepted

## Context

Onecool OS can now build deterministic runtime outputs for collectible assets:
Research Queue, Fair Value, ValuationRecord, Portfolio NAV, and Dashboard
Snapshot. Those outputs are useful during a session, but they need a durable
history layer so the owner can compare portfolio state across days and release
baselines without recalculating old views or committing private data.

## Decision

Introduce Portfolio History as an append-only local snapshot layer.

Portfolio History consumes existing `RuntimeSession` outputs and records an
immutable `PortfolioHistorySnapshot`. The snapshot includes portfolio summary,
NAV summary, coverage, research queue counts, evidence counts, valuation
counts, warnings, per-asset history lines, a deterministic fingerprint, schema
version, checksum, and reference datetime.

History files are written under:

```text
data/history/portfolio/YYYY/YYYY-MM-DD/
data/history/portfolio/index.jsonl
```

Real history files are private runtime data and remain ignored by Git.

## Boundaries

Portfolio History does not calculate Fair Value, NAV, ROI, source agreement,
valuation confidence, recommendations, or FX conversion. It delegates to
existing runtime outputs and persists the resulting state.

Portfolio History does not mutate Asset Master, imported PSA/BGS records,
evidence, valuation history, or runtime session state. It is replayable and
checksum-validated.

## Snapshot Types

- `PORTFOLIO_DAILY`
- `PORTFOLIO_MANUAL`
- `RELEASE_BASELINE`
- `IMPORT_BASELINE`

## Append-Only Rules

Exact duplicates are detected by snapshot id and checksum.

Materially different snapshots on the same date are preserved as separate
records through deterministic fingerprints.

If the same snapshot id appears with a different checksum, the write is
rejected unless the caller explicitly requests a new record.

## CLI

The CLI command:

```bash
python -m onecool_os record-portfolio-snapshot
```

loads the local runtime session, builds a history snapshot, writes it to the
append-only store, and prints an aggregate summary only. It does not print
private notes, raw rows, or full asset metadata.

## Consequences

Onecool OS now has a durable daily history foundation for future Daily Report
history, trend analytics, release baselines, and audit review.

The history store is intentionally local JSON for Beta dogfooding. Persistent
database storage, cloud sync, scheduled snapshot creation, and history
retention policies are future work.
