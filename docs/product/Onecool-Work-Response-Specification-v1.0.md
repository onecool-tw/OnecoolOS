# Onecool Work Response Specification v1.0

## 1. Purpose

This document defines the canonical response format produced by any Work
implementation that returns research evidence to Onecool OS.

The Work Response is the handoff from an Execution Platform back to the
Onecool OS Knowledge Platform. It may be produced by ChatGPT Work, Claude,
Gemini, OpenAI API agents, custom agents, manual research, or future approved
providers.

This specification narrows the general Onecool Work Contract v1.0 response
envelope for collectible sold-comparable research. It defines how comparable
records should be represented so the existing Onecool Research Framework and
eBay Sold Evidence Validation layers can consume them deterministically.

The Work Response is not Fair Value. It is not ValuationRecord. It is not NAV.
It is not a recommendation.

## 2. Principles

Responses must:

- Be deterministic.
- Return structured JSON only.
- Preserve uncertainty.
- Preserve warnings.
- Preserve errors.
- Never fabricate evidence.
- Never invent missing item IDs, prices, dates, URLs, or identities.
- Never calculate Onecool Fair Value.
- Never create ValuationRecord objects.
- Never calculate Portfolio NAV.
- Never recommend buy, sell, hold, or target prices.
- Never silently upgrade confidence.
- Never hide source disagreement or identity uncertainty.

If a provider cannot verify a field, it must leave the uncertainty visible
through `confidence`, `warnings`, `errors`, or `NO_MATCH`.

## 3. Response Envelope

Every Work Response must follow the Onecool Work Contract v1.0 envelope.

```json
{
  "schema_version": "1.0",
  "request_id": "work:ebay-url:PSA-111003720:SOLD_COMPARABLES",
  "provider": "ChatGPT Work",
  "status": "COMPLETED",
  "completed_at": "2026-07-14T09:30:00+08:00",
  "execution_time": {
    "started_at": "2026-07-14T09:25:00+08:00",
    "duration_seconds": 300
  },
  "outputs": {
    "orf_payload": {
      "batch_id": "batch-work-PSA-111003720",
      "provider_name": "ChatGPT Work",
      "results": []
    }
  },
  "warnings": [],
  "errors": []
}
```

### Required Envelope Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `schema_version` | Yes | Work Contract schema version. Current value: `1.0`. |
| `request_id` | Yes | Must exactly match the originating Work Request. |
| `provider` | Yes | Execution platform or provider that produced the response. |
| `status` | Yes | Work status, such as `COMPLETED`, `FAILED`, or `CANCELLED`. |
| `completed_at` | Yes for terminal states | ISO 8601 completion timestamp. |
| `execution_time` | No | Timing metadata for the execution. |
| `outputs` | Yes | Structured payloads returned by Work. |
| `warnings` | Yes | Non-fatal Work-level warnings. |
| `errors` | Yes | Fatal or blocking Work-level errors. |

### Output Payload

For collectible eBay Sold research, `outputs` must include an `orf_payload`
object. Onecool OS imports this object through the Onecool Research Framework.

The `orf_payload` may contain:

- A single ORF batch.
- A list of ORF batches.
- A single ORF result.

The preferred shape is one ORF batch with one ORF result for the originating
request.

## 4. Comparable Schema

Each sold comparable returned inside ORF evidence must include these fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `ebay_item_id` | Yes when available | eBay item identifier. Must not be invented. |
| `sold_item_url` | Yes when available | URL for the sold item evidence. |
| `title` | Yes | Listing title shown by the source. |
| `sold_price` | Yes for price evidence | Verified sold price. Do not use asking price when Best Offer price is unknown. |
| `currency` | Yes for price evidence | Currency of the sold price. |
| `sold_date` | Yes for sold evidence | Date the item sold. |
| `listing_type` | Yes when known | Example: `AUCTION`, `BUY_IT_NOW`, `BEST_OFFER`, `UNKNOWN`. |
| `best_offer_used` | Yes when known | Boolean or `null` if unknown. |
| `shipping_amount` | No | Shipping amount if visible and verified. |
| `exact_match` | Yes | Whether identity appears to match the target asset. |
| `matched_fields` | Yes | Identity fields that matched. |
| `mismatched_fields` | Yes | Identity fields that did not match or remain uncertain. |
| `confidence` | Yes | `HIGH`, `MEDIUM`, `LOW`, or `UNKNOWN`. |
| `warnings` | Yes | Comparable-level warnings. Empty list if none. |

### Canonical Comparable Example

```json
{
  "ebay_item_id": "123456789012",
  "sold_item_url": "https://www.ebay.com/itm/123456789012",
  "title": "2008 Topps Kobe Bryant #24 PSA 9",
  "sold_price": "125.00",
  "currency": "USD",
  "sold_date": "2026-07-01",
  "listing_type": "BUY_IT_NOW",
  "best_offer_used": false,
  "shipping_amount": "5.00",
  "exact_match": true,
  "matched_fields": [
    "YEAR",
    "BRAND",
    "CARD_NUMBER",
    "PLAYER",
    "GRADE_ISSUER",
    "GRADE"
  ],
  "mismatched_fields": [],
  "confidence": "HIGH",
  "warnings": []
}
```

## 5. Identity Rules

Exact match requires all of:

- Year.
- Brand.
- Card Number.
- Player.
- Grade Issuer.
- Grade.

For the Kobe PSA 9 first live workflow, an exact match requires:

- `2008`
- `TOPPS`
- card number `24`
- `KOBE BRYANT`
- `PSA`
- grade `9`

The provider must preserve identity uncertainty. It must not force an exact
match when title, image, cert, grade, parallel, brand, or card number are
ambiguous.

The following differences must be preserved in `mismatched_fields` and/or
`warnings`:

- Parallel mismatch.
- Chrome mismatch.
- Bowman mismatch.
- Refractor mismatch.
- Grade mismatch.
- Raw card vs graded card mismatch.
- PSA vs BGS/SGC/CGC mismatch.
- Card number mismatch.
- Player mismatch.
- Team-only or set-only ambiguity.
- Missing card number.
- Missing grade.

Identity uncertainty affects evidence classification. Confidence never upgrades
identity.

## 6. Confidence Rules

Allowed comparable confidence values:

| Confidence | Meaning |
| --- | --- |
| `HIGH` | The comparable appears to match all required identity fields and has verified source data. |
| `MEDIUM` | Most identity fields match, but one non-critical field or source detail remains uncertain. |
| `LOW` | Identity is plausible but materially incomplete or ambiguous. |
| `UNKNOWN` | Confidence cannot be determined from available evidence. |

Rules:

- Confidence is a statement about evidence reliability, not investment quality.
- Confidence must not hide warnings.
- Confidence must not upgrade identity.
- A `HIGH` confidence record can still be rejected by Evidence Validation if a
  required field is missing.
- A `LOW` or `UNKNOWN` record can still be useful as `NEEDS_REVIEW`.
- Best Offer listings with unknown accepted price should not be marked `HIGH`
  for price evidence.

## 7. Warning Rules

Warnings preserve uncertainty without blocking the entire response.

Recommended warning codes:

| Warning | Meaning |
| --- | --- |
| `BEST_OFFER_PRICE_UNKNOWN` | Listing shows Best Offer, but accepted price is not verified. |
| `TITLE_AMBIGUOUS` | Title does not fully prove identity. |
| `GRADE_MISSING` | Grade is missing from the listing evidence. |
| `CARD_NUMBER_MISSING` | Card number is missing from the listing evidence. |
| `IDENTITY_PARTIAL` | Some required identity fields are incomplete or uncertain. |
| `NO_ITEM_ID` | eBay item ID is missing or cannot be verified. |
| `NO_SOLD_URL` | Sold item URL is missing or cannot be verified. |
| `NO_SOLD_DATE` | Sold date is missing or cannot be verified. |
| `PRICE_UNVERIFIED` | Price cannot be verified as the accepted sold price. |
| `PARALLEL_MISMATCH` | Listing appears to be a different parallel or variety. |
| `BRAND_MISMATCH` | Listing appears to be a different brand, such as Bowman instead of Topps. |
| `CHROME_MISMATCH` | Listing appears to be Chrome when target is not Chrome, or vice versa. |

Warnings must be preserved into the ORF payload and must remain visible to
Evidence Validation.

## 8. Error Rules

Errors describe response-level failure conditions.

Recommended error codes:

| Error | Meaning |
| --- | --- |
| `NO_MATCH` | No exact or usable comparable could be verified. |
| `PROVIDER_FAILURE` | The Work provider failed unexpectedly. |
| `RATE_LIMIT` | Provider or research platform blocked execution due to rate limits. |
| `INVALID_RESPONSE` | Response shape does not follow this specification. |
| `MALFORMED_JSON` | Response is not valid JSON. |
| `REQUEST_ID_MISMATCH` | Response does not match the originating request. |
| `UNSUPPORTED_SOURCE` | Provider used a source outside the approved request scope. |

Errors must not be converted into fabricated comparable records. A failed
response should fail loudly and be corrected or rerun.

## 9. NO_MATCH Rules

A provider should return `NO_MATCH` instead of guessing when:

- No sold comparable can be verified.
- Only active listings are found.
- Only asking prices are found.
- Best Offer accepted prices cannot be verified.
- Identity cannot be confirmed.
- Player, grade, card number, brand, or year do not match.
- Listings are for a different parallel, Chrome version, Bowman card, or raw
  card.
- Source pages are unavailable or too ambiguous.

`NO_MATCH` is a valid workflow outcome. It preserves truth by refusing to
invent market evidence.

A `NO_MATCH` response should still include:

- Matching `request_id`.
- Provider name.
- Completion status.
- ORF result status of `NO_MATCH` when represented as ORF.
- Warnings explaining why no match was accepted.

## 10. Examples

### VERIFIED Example

```json
{
  "schema_version": "1.0",
  "request_id": "work:ebay-url:PSA-111003720:SOLD_COMPARABLES",
  "provider": "ChatGPT Work",
  "status": "COMPLETED",
  "completed_at": "2026-07-14T09:30:00+08:00",
  "execution_time": {
    "started_at": "2026-07-14T09:25:00+08:00",
    "duration_seconds": 300
  },
  "outputs": {
    "orf_payload": {
      "batch_id": "batch-work-PSA-111003720",
      "provider_name": "ChatGPT Work",
      "results": [
        {
          "result_id": "result-PSA-111003720",
          "request_id": "ebay-url:PSA-111003720:SOLD_COMPARABLES",
          "provider_name": "ChatGPT Work",
          "provider_type": "MANUAL",
          "provider_version": "v1",
          "capabilities": ["SOLD_COMPARABLES"],
          "research_type": "SOLD_COMPARABLES",
          "asset_id": "PSA-111003720",
          "cert_number": "111003720",
          "status": "COMPLETED",
          "confidence": "HIGH",
          "evidence": [
            {
              "evidence_id": "evidence-123456789012",
              "evidence_type": "SOLD_COMPARABLES",
              "source_name": "eBay Sold",
              "source_url": "https://www.ebay.com/itm/123456789012",
              "item_id": "123456789012",
              "observed_value": "125.00",
              "currency": "USD",
              "observed_date": "2026-07-01",
              "title": "2008 Topps Kobe Bryant #24 PSA 9",
              "exact_match": true,
              "matched_fields": [
                "YEAR",
                "BRAND",
                "CARD_NUMBER",
                "PLAYER",
                "GRADE_ISSUER",
                "GRADE"
              ],
              "mismatched_fields": [],
              "confidence": "HIGH",
              "status": "COMPLETED",
              "warnings": [],
              "raw_metadata": {
                "listing_type": "BUY_IT_NOW",
                "best_offer_used": false,
                "shipping_amount": "5.00"
              },
              "created_at": "2026-07-14T09:30:00+08:00"
            }
          ],
          "normalized_payload": {},
          "warnings": [],
          "provider_metadata": {
            "search_url": "https://www.ebay.com/sch/i.html?_nkw=2008+TOPPS+24+KOBE+BRYANT++PSA+9&LH_Sold=1&LH_Complete=1",
            "search_queries": ["2008 Topps 24 Kobe Bryant PSA 9"]
          },
          "generated_at": "2026-07-14T09:30:00+08:00",
          "reference_datetime": "2026-07-14T09:25:00+08:00"
        }
      ],
      "warnings": [],
      "generated_at": "2026-07-14T09:30:00+08:00",
      "reference_datetime": "2026-07-14T09:25:00+08:00"
    }
  },
  "warnings": [],
  "errors": []
}
```

### NEEDS_REVIEW Example

```json
{
  "schema_version": "1.0",
  "request_id": "work:ebay-url:PSA-111003720:SOLD_COMPARABLES",
  "provider": "ChatGPT Work",
  "status": "COMPLETED",
  "completed_at": "2026-07-14T09:40:00+08:00",
  "execution_time": {
    "duration_seconds": 240
  },
  "outputs": {
    "orf_payload": {
      "batch_id": "batch-work-PSA-111003720-review",
      "provider_name": "ChatGPT Work",
      "results": [
        {
          "result_id": "result-PSA-111003720-review",
          "request_id": "ebay-url:PSA-111003720:SOLD_COMPARABLES",
          "provider_name": "ChatGPT Work",
          "provider_type": "MANUAL",
          "provider_version": "v1",
          "capabilities": ["SOLD_COMPARABLES"],
          "research_type": "SOLD_COMPARABLES",
          "asset_id": "PSA-111003720",
          "cert_number": "111003720",
          "status": "COMPLETED",
          "confidence": "MEDIUM",
          "evidence": [
            {
              "evidence_id": "evidence-review-123",
              "evidence_type": "SOLD_COMPARABLES",
              "source_name": "eBay Sold",
              "source_url": "https://www.ebay.com/itm/123",
              "item_id": "123",
              "observed_value": "110.00",
              "currency": "USD",
              "observed_date": "2026-06-20",
              "title": "2008 Topps Kobe Bryant PSA 9",
              "exact_match": false,
              "matched_fields": ["YEAR", "BRAND", "PLAYER", "GRADE_ISSUER", "GRADE"],
              "mismatched_fields": ["CARD_NUMBER"],
              "confidence": "MEDIUM",
              "status": "NEEDS_REVIEW",
              "warnings": ["CARD_NUMBER_MISSING", "IDENTITY_PARTIAL"],
              "raw_metadata": {
                "listing_type": "AUCTION",
                "best_offer_used": false
              },
              "created_at": "2026-07-14T09:40:00+08:00"
            }
          ],
          "normalized_payload": {},
          "warnings": ["Comparable requires manual identity review."],
          "provider_metadata": {},
          "generated_at": "2026-07-14T09:40:00+08:00",
          "reference_datetime": "2026-07-14T09:35:00+08:00"
        }
      ],
      "warnings": ["Some evidence requires manual review."],
      "generated_at": "2026-07-14T09:40:00+08:00",
      "reference_datetime": "2026-07-14T09:35:00+08:00"
    }
  },
  "warnings": ["Some returned evidence requires review."],
  "errors": []
}
```

### NO_MATCH Example

```json
{
  "schema_version": "1.0",
  "request_id": "work:ebay-url:PSA-111003720:SOLD_COMPARABLES",
  "provider": "ChatGPT Work",
  "status": "COMPLETED",
  "completed_at": "2026-07-14T09:45:00+08:00",
  "execution_time": {
    "duration_seconds": 180
  },
  "outputs": {
    "orf_payload": {
      "batch_id": "batch-work-PSA-111003720-no-match",
      "provider_name": "ChatGPT Work",
      "results": [
        {
          "result_id": "result-PSA-111003720-no-match",
          "request_id": "ebay-url:PSA-111003720:SOLD_COMPARABLES",
          "provider_name": "ChatGPT Work",
          "provider_type": "MANUAL",
          "provider_version": "v1",
          "capabilities": ["SOLD_COMPARABLES"],
          "research_type": "SOLD_COMPARABLES",
          "asset_id": "PSA-111003720",
          "cert_number": "111003720",
          "status": "NO_MATCH",
          "confidence": "UNVERIFIED",
          "evidence": [],
          "normalized_payload": {},
          "warnings": [
            "No exact sold comparable could be verified.",
            "Best Offer prices were not visible."
          ],
          "provider_metadata": {
            "search_url": "https://www.ebay.com/sch/i.html?_nkw=2008+TOPPS+24+KOBE+BRYANT++PSA+9&LH_Sold=1&LH_Complete=1"
          },
          "generated_at": "2026-07-14T09:45:00+08:00",
          "reference_datetime": "2026-07-14T09:42:00+08:00"
        }
      ],
      "warnings": ["NO_MATCH"],
      "generated_at": "2026-07-14T09:45:00+08:00",
      "reference_datetime": "2026-07-14T09:42:00+08:00"
    }
  },
  "warnings": ["NO_MATCH"],
  "errors": []
}
```

## 11. Import Expectations

Onecool OS imports Work Responses in layers:

```text
Work Response JSON
-> Work Bridge
-> ORF payload extraction
-> Onecool Research Framework validation
-> eBay Sold Evidence Validation
-> Evidence classification
```

Import expectations:

- Work Bridge validates the Work Contract envelope.
- Work Bridge requires matching `request_id` when an expected request id is
  supplied.
- Work Bridge extracts `outputs.orf_payload`.
- ORF validates provider metadata, provider version, evidence IDs, dates,
  prices, URLs, statuses, confidence, and warnings.
- Evidence Validation classifies records as `VERIFIED`, `NEEDS_REVIEW`,
  `REJECTED`, or `NO_MATCH`.
- Import must preserve warnings.
- Import must preserve errors.
- Import must not call providers.
- Import must not calculate Fair Value.
- Import must not create ValuationRecord.
- Import must not update Portfolio NAV.
- Import must not update Dashboard.
- Import must not generate recommendations.

If a response fails validation, the correct recovery is to correct the Work
response or rerun Work. Onecool OS should not silently repair evidence.

## 12. Future Compatibility

Future providers should produce the same canonical response shape whenever they
return comparable evidence.

Future compatible providers may include:

- Card Ladder.
- PWCC.
- Goldin.
- Fanatics Collect.
- Manual research workflows.
- Official eBay APIs if allowed and available.
- Other legally authorized providers.

Provider-specific fields may be stored in `raw_metadata` or provider metadata,
but canonical fields must remain stable. Onecool OS should not require a new
Knowledge Platform architecture when a new execution provider is added.

Future provider responses must preserve the same boundaries:

- Providers supply observations.
- ORF validates research shape.
- Evidence Validation classifies trust.
- Onecool Fair Value calculates only after verified evidence exists.
- Dashboard presents only downstream Knowledge Platform outputs.
