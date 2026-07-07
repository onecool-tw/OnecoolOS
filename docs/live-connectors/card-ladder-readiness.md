# Card Ladder Integration Readiness

This document defines the safest ingestion strategy for Card Ladder data in
Collectible Radar Beta.

Card Ladder is a Validation Source. It does not replace eBay Sold as the
sports-card Primary Market Price source, and it must not decide which market
source is correct.

## Role In Collectible Radar

Card Ladder provides market context for collectible sports cards. In Onecool OS
it should be used to validate, compare, and explain valuation confidence rather
than to overwrite or supersede Primary Market Price observations.

Card Ladder data should enter Onecool OS as independent source observations.
Those observations can later be mapped into valuation records and consumed by
Market Intelligence, Collectible Intelligence, Dashboard, Decision Queue, and
OFAI Context.

## Validation Source Definition

Validation Sources verify confidence, detect anomalies, and increase valuation
reliability. They are not final-value selectors.

For Collectible Radar:

1. eBay Sold remains the default Primary Market Price for sports cards.
2. Card Ladder is a Validation Source.
3. Card Ladder observations remain independent valuation records.
4. Card Ladder can improve source agreement analysis when close to eBay Sold.
5. Card Ladder can trigger review when it diverges from eBay Sold.

## Relationship With eBay Sold

eBay Sold represents the closest executable market price when safe data is
available. Card Ladder compares against that primary market observation.

Card Ladder must not:

- replace eBay Sold as Primary Market Price
- choose the final market value
- hide source disagreement
- overwrite valuation history
- downgrade or upgrade confidence by itself

Future confidence and source agreement layers may use Card Ladder as evidence,
but those layers must keep the original source records visible.

## Approved Ingestion Options

Approved ingestion options, in preferred order:

1. Official API if allowed and available
2. Official export if available
3. User-provided CSV / JSON export
4. Manual fixture import

Official API work must happen only after review of Card Ladder terms,
authentication, allowed endpoints, data retention rules, rate limits, and
production credential handling.

Official exports and user-provided files are preferred for Beta because they
avoid credential storage and keep ingestion user-approved.

Manual fixture import is acceptable for development, deterministic tests, and
review workflows, but it must not be confused with live source integration.

## Rejected Ingestion Options

- Unauthorized scraping of Card Ladder pages
- Browser automation that simulates scraping
- Credential sharing or storing user Card Ladder passwords
- Circumventing rate limits, robots controls, or platform access rules
- Treating screenshots or copied page text as authoritative machine data
- Any integration that hides source uncertainty from the user

Unauthorized scraping is not part of the MVP.

## Required Fields

Each Card Ladder observation must provide:

- `asset_id` or `asset_hint`
- `valuation_value` or `market_value`
- `currency`
- `valuation_date`
- `source`
- `external_id` or URL/reference

`asset_hint` should include enough information for future deterministic review:
player, year, brand, set, card number, grader, grade, or title when available.

## Optional Fields

- `title`
- `player`
- `year`
- `brand`
- `card_number`
- `grade_company`
- `grade`
- `card_ladder_value`
- `population`
- `sales_count`
- `raw_payload`

Optional fields should be preserved when available, but missing optional fields
must not be fabricated.

## Currency Handling

The source currency must be preserved exactly as reported by Card Ladder or by
the user-provided export. The importer should normalize currency codes to
uppercase ISO-style strings when possible.

Currency conversion is out of scope for Card Ladder ingestion. Future valuation
or analytics layers may handle conversion explicitly.

## Valuation Date Handling

`valuation_date` is required and should represent the date attached to the
Card Ladder observation. If the source provides multiple timestamps, the
importer should preserve the most relevant valuation timestamp as
`valuation_date` and store the others in metadata.

The importer must not use system time as a substitute for missing
`valuation_date`.

## Duplicate Detection

Duplicate detection should use deterministic priority:

1. `external_id`
2. source URL/reference
3. asset identity plus value, currency, and `valuation_date`

When duplicate certainty is low, the record should be marked `NEEDS_REVIEW`
rather than discarded silently.

## Source URL And Reference Handling

Every Card Ladder record should preserve either:

- official `external_id`
- source URL
- user-provided reference

This reference should flow into valuation metadata and audit context so users
can verify the source later.

## ImportAudit Usage

Card Ladder imports must create `ImportAudit` records with:

- source: `CARD_LADDER`
- source filename or API batch identifier
- injected `reference_datetime`
- total rows
- imported rows
- skipped rows
- duplicate rows
- invalid rows
- warnings
- checksum when importing files

`ImportAudit` must not store private raw source payloads. Raw payloads may be
preserved only in normalized source records or valuation metadata when allowed
by the ingestion method and user consent.

## Privacy And Security Notes

- Do not store Card Ladder credentials in MVP.
- Do not request user passwords.
- Prefer official exports, local user-provided files, or official API flows
  after security review.
- Keep raw source files under user-controlled import directories.
- Do not commit private imports.
- Preserve only the metadata required for reproducibility, audit, and user
  review.

## Legal And Terms Risk

Risk level: `NEEDS_REVIEW`.

Official API or export integration requires review of Card Ladder terms,
allowed use cases, endpoint or export availability, data retention limits, and
display restrictions.

User-provided exports require clear instructions that the user is responsible
for providing data they are allowed to use.

Unauthorized scraping has high legal and terms risk and is rejected for MVP.

## Implementation Complexity

Complexity: `MEDIUM`.

Local CSV / JSON import is moderate because field mapping, duplicate detection,
and source preservation are straightforward.

Official API integration is higher complexity because it may require
authentication, credential storage, rate limits, paging, retries, error
handling, and legal review.

## MVP Recommendation

MVP readiness: `NEEDS_REVIEW`.

Recommended Beta path:

1. Verify whether an official API or export path is allowed and available.
2. If not, support user-provided CSV / JSON export or manual fixture import.
3. Preserve source identity and raw payloads when allowed.
4. Map records into independent `ValuationRecord` entries.
5. Keep Card Ladder as a Validation Source.
6. Keep eBay Sold as the Primary Market Price source for sports cards.
7. Keep source disagreement visible in Market Intelligence, Dashboard,
   Decision Queue, and OFAI Context.
8. Defer live integration until terms, authentication, credentials, and
   security design are reviewed.

## Valuation Policy

Card Ladder observations create independent valuation records. They never
overwrite valuation history, replace eBay Sold as Primary Market Price,
calculate confidence, calculate source agreement, select final market value,
predict prices, recommend actions, call APIs without approval, scrape websites,
or mutate source files.

## Manual Import Foundation

`CardLadderManualImporter` is the supported Beta foundation for Card Ladder
manual files. It loads user-provided CSV / JSON only, validates required
valuation, source identity, and asset identity fields, emits
`CollectibleMarketRecord` objects with source `CARD_LADDER`, and records
`ImportSummary` plus reusable `ImportAudit`.

Manual import does not call APIs, scrape websites, add credentials, overwrite
valuation history, replace eBay Sold as Primary Market Price, select final
valuation, calculate confidence or source agreement, recommend buying or
selling, predict prices, or mutate source files.
