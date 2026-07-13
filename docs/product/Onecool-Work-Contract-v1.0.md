# Onecool Work Contract v1.0

## 1. Purpose

The Onecool Work Contract defines the execution boundary between Onecool OS and
external work platforms.

Onecool OS is the Knowledge Platform. It owns durable truth, validation,
evidence, Fair Value, ValuationRecord, history, decision rules, and dashboard
snapshots.

Work platforms are Execution Platforms. They run workflows, schedule tasks,
perform research, generate reports, coordinate review, and return structured
outputs.

This contract exists so ChatGPT Work, Claude, Gemini, OpenAI API agents,
custom agents, or future execution systems can interact with Onecool OS
without changing the Knowledge Platform.

## 2. Core Principle

Onecool OS owns:

- Knowledge
- Rules
- Validation
- Evidence
- Fair Value
- Decision logic
- Source-of-truth history

Work owns:

- Execution
- Scheduling
- Long-running tasks
- Research
- Reporting
- Notifications
- Human review orchestration

Onecool OS remembers. Work executes.

## 3. Request Contract

A Work Request is the standard envelope sent from Onecool OS or the owner to an
execution platform.

### Request Envelope

```json
{
  "schema_version": "1.0",
  "request_id": "work-request-2026-07-13-0001",
  "request_type": "COLLECTION_RESEARCH",
  "asset_id": "PSA-12345678",
  "portfolio_id": "onecool-collection",
  "reference_datetime": "2026-07-13T09:00:00+08:00",
  "priority": "HIGH",
  "requested_action": "Find verified eBay Sold evidence for this asset.",
  "context": {
    "asset_name": "2018 Topps Update Shohei Ohtani US1 PSA 10",
    "known_identity": {
      "cert_number": "12345678",
      "grade_company": "PSA",
      "grade": "10"
    }
  },
  "source_urls": [
    "https://www.ebay.com/sch/i.html?_nkw=example&LH_Sold=1&LH_Complete=1"
  ],
  "constraints": {
    "no_scraping": true,
    "no_recommendations": true,
    "return_evidence_only": true
  }
}
```

### Required Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `schema_version` | Yes | Work Contract schema version. |
| `request_id` | Yes | Stable idempotency key for the work request. |
| `request_type` | Yes | Type of work being requested. |
| `reference_datetime` | Yes | Time anchor for deterministic execution. |
| `priority` | Yes | Execution priority. |
| `requested_action` | Yes | Human-readable action statement. |
| `context` | Yes | Minimal structured context needed for execution. |
| `constraints` | Yes | Rules the provider must follow. |

### Optional Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `asset_id` | No | Asset targeted by the request. Required for asset-specific work. |
| `portfolio_id` | No | Portfolio targeted by the request. |
| `source_urls` | No | Owner-approved URLs or research entry points. |

### Request Types

Reserved request types:

- `COLLECTION_RESEARCH`
- `EVIDENCE_RESEARCH`
- `BATCH_RESEARCH`
- `MORNING_BRIEF`
- `HISTORY_SNAPSHOT_REVIEW`
- `REPORT_GENERATION`
- `HUMAN_REVIEW`
- `NOTIFICATION`

## 4. Response Contract

A Work Response is the standard envelope returned by an execution platform.

### Response Envelope

```json
{
  "schema_version": "1.0",
  "request_id": "work-request-2026-07-13-0001",
  "status": "COMPLETED",
  "provider": "ChatGPT Work",
  "completed_at": "2026-07-13T09:03:20+08:00",
  "execution_time": {
    "started_at": "2026-07-13T09:00:10+08:00",
    "duration_seconds": 190
  },
  "outputs": {
    "evidence_file": "imports/research/result.json",
    "records_found": 3
  },
  "warnings": [],
  "errors": []
}
```

### Required Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `schema_version` | Yes | Response schema version. |
| `request_id` | Yes | Must match the originating request. |
| `status` | Yes | Work status. |
| `provider` | Yes | Execution platform or provider name. |
| `completed_at` | Yes for terminal states | Completion timestamp. |
| `outputs` | Yes | Structured outputs. Empty object if no output. |
| `warnings` | Yes | Non-fatal execution warnings. |
| `errors` | Yes | Fatal or blocking errors. |

### Optional Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `execution_time` | No | Timing details. |

## 5. Work Status Model

| Status | Meaning |
| --- | --- |
| `CREATED` | Request has been created but not evaluated for readiness. |
| `READY` | Request is valid and ready for execution. |
| `RUNNING` | Execution is in progress. |
| `WAITING_INPUT` | Execution needs owner input or additional data. |
| `COMPLETED` | Execution finished and returned outputs. |
| `FAILED` | Execution failed and returned errors. |
| `CANCELLED` | Execution was cancelled before completion. |

Status changes belong to the execution platform. Onecool OS may record or
validate returned status but should not pretend to have executed work it did
not run.

## 6. Error Model

Standard error categories:

| Error Category | Meaning |
| --- | --- |
| `INVALID_REQUEST` | Request envelope is malformed or missing required fields. |
| `PROVIDER_TIMEOUT` | Provider did not complete within expected time. |
| `NO_MATCH` | Provider could not find matching data or evidence. |
| `RATE_LIMIT` | Provider or platform rate limit blocked execution. |
| `VALIDATION_FAILED` | Returned output failed Onecool validation rules. |
| `UNSUPPORTED_PROVIDER` | Requested provider is not supported for this task. |
| `INTERNAL_ERROR` | Execution platform failed unexpectedly. |

Errors must be explicit. Work must not silently fabricate outputs to avoid an
error.

## 7. Idempotency

`request_id` is the idempotency key.

Duplicate requests should be detected by:

- exact `request_id`
- compatible `schema_version`
- same `request_type`
- same target asset or portfolio
- same `reference_datetime`
- same `requested_action`

Request IDs must be reusable safely. Re-running the same request should either:

- return the same response
- return a clear duplicate response
- resume the existing execution
- fail with an explicit idempotency conflict

Work must not create duplicate evidence, duplicate files, duplicate reports, or
duplicate side effects without an explicit new request id.

## 8. Versioning

The Work Contract uses semantic schema versions.

Version rules:

- Patch-compatible changes may add optional fields.
- Minor-compatible changes may add new request types, statuses, or error
  categories.
- Major changes may rename required fields or change envelope semantics.

Backward compatibility:

- Providers should accept older compatible schema versions when possible.
- Onecool OS should validate `schema_version` before importing Work outputs.
- Unknown optional fields should be preserved or ignored safely.
- Unknown required behavior should fail with `UNSUPPORTED_PROVIDER` or
  `INVALID_REQUEST`.

## 9. Provider Independence

ChatGPT Work is only one implementation of the Work Contract.

Future execution providers should not require changes to Onecool OS knowledge
models. They should adapt to the request and response envelopes.

Provider-specific details belong in:

- provider metadata
- execution configuration
- Work-owned adapters
- owner-approved workflows

Provider-specific details must not leak into:

- Asset Master identity
- Evidence validation rules
- Onecool Fair Value
- ValuationRecord
- Portfolio NAV
- Portfolio History

## 10. Example Workflows

### Collection Research

```text
Research Queue
↓
Work Request
↓
Execution Platform
↓
Evidence JSON
↓
Onecool OS Evidence Validation
↓
Onecool OS Knowledge
```

Work finds or prepares evidence. Onecool OS validates it.

### Morning Brief

```text
Portfolio History Snapshot
↓
Dashboard Snapshot
↓
Work Request
↓
Morning Brief Execution
↓
Owner-facing report
```

Work generates the brief. Onecool OS remains the source of truth.

### Batch Research

```text
Research Queue
↓
Batch Work Requests
↓
Parallel or sequential execution
↓
Provider outputs
↓
Onecool validation
↓
Evidence records
```

Work executes the batch. Onecool OS validates and imports accepted outputs.

## 11. Security

Work requests must expose only the minimum necessary context.

Never expose:

- private notes
- Asset Master internals
- hidden runtime metadata
- secrets
- credentials
- raw private files
- personal spreadsheet contents
- unrelated portfolio data

Allowed context should be explicit, scoped, and auditable.

Source URLs should be owner-approved research entry points. A source URL is not
itself evidence until Onecool OS receives and validates a returned evidence
record.

## 12. Success Criteria

A Work implementation is compliant if it:

- accepts the request contract
- returns the response contract
- preserves `request_id`
- reports status explicitly
- does not invent evidence
- does not bypass validation
- does not modify Onecool OS data directly
- respects constraints
- returns warnings and errors clearly
- keeps provider-specific execution outside Onecool OS knowledge models

## 13. Future Extensions

Reserved extension areas:

- multi-provider execution
- parallel execution
- human review
- approval workflows
- scheduling
- notification delivery
- provider capability discovery
- execution audit logs
- retry policy
- cancellation policy
- Work-to-History links

Future extensions must preserve the Knowledge Platform boundary.

## Contract Summary

Onecool OS sends structured requests.

Work executes.

Work returns structured responses.

Onecool OS validates outputs before they become knowledge.

