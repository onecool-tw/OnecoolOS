# First Live Workflow: Kobe Bryant PSA 9 Research Validation

## 1. Purpose

This workflow validates the first real Onecool OS -> ChatGPT Work -> Onecool OS
closed loop.

It is a product validation exercise, not a new architecture feature. The goal is
to prove that Onecool OS can export one deterministic Work Request, receive one
contract-compliant Work Response from ChatGPT Work, and validate the returned
research through the existing Onecool Research Framework and eBay Sold Evidence
Validation layers.

The workflow stops at validated Evidence. It does not continue to Fair Value,
ValuationRecord, Portfolio NAV, Dashboard, Daily Report, or recommendations.

## 2. Target Asset Identity

The target asset is:

| Field | Value |
| --- | --- |
| Item | 2008 TOPPS #24 KOBE BRYANT |
| Cert Number | 111003720 |
| Year | 2008 |
| Set | TOPPS |
| Card Number | 24 |
| Subject | KOBE BRYANT |
| Grade Issuer | PSA |
| Grade | 9 |

Identity must be confirmed before export. The Work Request must preserve these
identity fields exactly enough for ChatGPT Work to research the correct asset.

## 3. Preconditions

Before executing the workflow, confirm:

- The current collection CSV exists locally.
- The current Asset Master exists locally.
- Cert number `111003720` is present exactly once.
- The target asset has an eBay Sold Search URL.
- The eBay Sold Search URL is valid and user-approved.
- The Research Queue item for cert `111003720` is `READY`.
- The Work Bridge commit is available locally.
- Local private work files under `imports/work/` are ignored by Git.
- Local validation output under `outputs/` is ignored by Git.

## 4. Workflow Steps

1. Import the current collection and Asset Master.
2. Build the Research Queue.
3. Export exactly one Work Request for cert `111003720`.
4. Inspect the exported request without modifying identity fields.
5. Provide the request JSON to ChatGPT Work.
6. ChatGPT Work researches only the supplied eBay Sold Search URL.
7. ChatGPT Work returns one Onecool Work Contract v1.0 response JSON.
8. Save the response locally.
9. Import the response through the existing Work Bridge.
10. Validate the response payload through ORF.
11. Validate returned observations through the existing eBay Sold Evidence layer.
12. Record final evidence counts and the workflow result.

## 5. Expected Local Paths

Suggested local paths:

| Artifact | Path |
| --- | --- |
| Work Request | `imports/work/kobe_111003720_request.json` |
| Work Response | `imports/work/kobe_111003720_response.json` |
| Validation Report | `outputs/workflows/kobe_111003720_validation_report.json` |

These are real workflow files and must remain local. They must not be committed.

## 6. ChatGPT Work Execution Instructions

Use this exact instruction when handing the request to ChatGPT Work:

```text
You are executing a Onecool Work Contract research request.

Use only the supplied eBay Sold Search URL.

Research the exact target asset only.

Do not use active listings.

Do not invent missing information.

For each verifiable sold comparable return:

- sold_item_url
- ebay_item_id
- title
- sold_price
- currency
- sold_date
- listing_type
- best_offer_used
- shipping_amount
- exact_match
- matched_fields
- mismatched_fields
- confidence
- warnings

The exact identity must match:

- 2008
- TOPPS
- card number 24
- KOBE BRYANT
- PSA
- grade 9

If the accepted Best Offer price cannot be verified, do not use the original
asking price as the sold price.

If no exact sold comparable can be verified, return NO_MATCH.

Return only the Onecool Work Contract v1.0 response JSON.

Do not calculate Fair Value, NAV, ROI, listing price, or buy/sell recommendations.
```

## 7. Request Acceptance Checks

Before sending the request to ChatGPT Work, verify:

- `schema_version` is supported.
- `request_id` is present.
- `request_type` is correct.
- `asset_id` is present.
- Cert number is `111003720`.
- Source URL is valid.
- Identity is complete.
- Requested fields are complete.
- No private notes are included.
- No Asset Master internals are exposed.

## 8. Response Acceptance Checks

Before importing the response, verify:

- `schema_version` is supported.
- `request_id` matches the exported request.
- `provider` identifies ChatGPT Work or the manual execution provider.
- `status` is present.
- `outputs` follows the Work Contract.
- The ORF payload is inside the structured `outputs` object.
- Unsupported fields are not silently trusted.
- No raw prose appears outside JSON.
- `warnings` are preserved.
- `errors` are preserved.

## 9. ORF Acceptance Checks

ORF validation must verify:

- Provider metadata is present.
- Provider version is valid.
- Evidence IDs are unique.
- Dates are valid.
- Prices are valid.
- URLs are valid.
- `PARTIAL` results include warnings.
- `FAILED` and `NO_MATCH` behavior is valid.
- No confidence upgrade occurs during import.

## 10. Evidence Acceptance Checks

For `VERIFIED` evidence, require:

- Sold URL.
- eBay item ID.
- Sold date.
- Sold price.
- Currency.
- Exact identity match.
- PSA grade 9 match.
- Card number 24 match.
- Kobe Bryant match.
- No parallel or variety mismatch.

Each record must be classified deterministically as one of:

- `VERIFIED`
- `NEEDS_REVIEW`
- `REJECTED`
- `NO_MATCH`

## 11. Success Criteria

The workflow is successful when:

- One Work Request is exported.
- ChatGPT Work returns a contract-compliant response.
- The Work Bridge accepts the response.
- ORF validation passes.
- eBay Sold Evidence validation completes.
- At least one evidence record is classified deterministically.
- No provider call occurs inside Onecool OS.
- No private file is committed.
- No Fair Value is created.
- No ValuationRecord is created.
- No Portfolio NAV is updated.
- No recommendation is generated.
- The same response produces the same validation result on replay.

Evidence PASS does not require every comparable to be `VERIFIED`. A result
containing `NEEDS_REVIEW`, `REJECTED`, or `NO_MATCH` is still a valid workflow
outcome if classification is correct and deterministic.

## 12. Failure Points and Recovery

| Failure Point | Recovery |
| --- | --- |
| Target asset missing | Stop. Re-import collection and confirm cert number. |
| Duplicate cert | Stop. Resolve source data or Asset Master duplicate before export. |
| Research Queue `BLOCKED` | Stop. Fix the blocking metadata, usually missing or invalid eBay URL. |
| Missing eBay URL | Add a user-approved eBay Sold Search URL to Asset Master, then rerun queue generation. |
| Malformed request JSON | Regenerate the Work Request from Onecool OS. Do not manually repair identity fields. |
| Work returns prose instead of JSON | Reject the response and rerun Work with the exact JSON-only instruction. |
| Mismatched request ID | Reject the response. Match it to the correct request or rerun Work. |
| Missing Item ID | Allow Evidence Validation to classify the record. Correct the Work response or rerun Work. |
| Missing sold URL | Allow Evidence Validation to classify the record. Correct the Work response or rerun Work. |
| Missing sold date | Allow Evidence Validation to classify the record. Correct the Work response or rerun Work. |
| Best Offer price unverified | Do not use the original asking price. Mark the comparable `NEEDS_REVIEW` or exclude it. |
| Wrong card number | Reject or mark the evidence according to Evidence Validation. |
| Wrong grade | Reject or mark the evidence according to Evidence Validation. |
| Wrong player | Reject or mark the evidence according to Evidence Validation. |
| Duplicate sold comps | Preserve evidence identity, but flag duplicates for validation/review. |
| ORF validation failure | Reject the response and correct the structured ORF payload. |
| Evidence validation failure | Do not repair silently. Correct the Work response or rerun Work. |

Do not repair evidence silently. The recovery path is to correct the Work
response or rerun ChatGPT Work with the same request.

## 13. Acceptance Checklist

- [ ] Request exported.
- [ ] Correct asset identity confirmed.
- [ ] Correct eBay URL confirmed.
- [ ] Work response saved locally.
- [ ] Request ID matches.
- [ ] ORF validation passed.
- [ ] Evidence classified.
- [ ] No fabricated values accepted.
- [ ] Replay is deterministic.
- [ ] Private files are ignored.
- [ ] Workflow status recorded.

## 14. Workflow Coverage

Track each stage separately:

| Stage | Status | Notes |
| --- | --- | --- |
| Research Queue -> Work Request | `NOT_STARTED` | Export exactly one request for cert `111003720`. |
| Work Request -> ChatGPT Work | `NOT_STARTED` | Manual execution outside Onecool OS. |
| ChatGPT Work -> Work Response | `NOT_STARTED` | Response must be Work Contract v1.0 JSON. |
| Work Response -> Work Bridge | `NOT_STARTED` | Import through existing Work Bridge only. |
| Work Bridge -> ORF | `NOT_STARTED` | Existing ORF validation must pass. |
| ORF -> Evidence Validation | `NOT_STARTED` | Existing eBay Sold Evidence validation classifies records. |

Allowed status values:

- `NOT_STARTED`
- `IN_PROGRESS`
- `PASSED`
- `FAILED`
- `BLOCKED`

## 15. Out of Scope

This workflow explicitly excludes:

- Fair Value aggregation.
- EQS calculation.
- ValuationRecord creation.
- Portfolio NAV.
- Dashboard update.
- Batch research.
- Scheduling.
- Notifications.
- Daily Report.

## Validation Notes

Terminology should remain consistent with:

- Onecool Product Vision v1.0.
- ADR-017 Architecture Freeze.
- Onecool Metrics Framework v1.0.
- Onecool Work Contract v1.0.

This document is an execution and acceptance plan only. It must not require
production code, tests, Runtime, Dashboard, Work Bridge, ORF, Evidence,
Valuation, NAV, or ADR changes.
