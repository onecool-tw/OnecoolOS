# eBay Sold Integration Readiness

This document defines the safest ingestion strategy for eBay Sold data in
Collectible Radar Beta.

This sprint is documentation and design only. It does not implement a live
eBay connector, call eBay APIs, scrape websites, add credentials, modify
runtime behavior, or add private user data.

## Role In Collectible Radar

eBay Sold is the default `Primary Market Price` source for sports cards in
Collectible Radar because completed sales are usually the closest observable
market signal for the price at which a comparable card could likely be sold
today.

eBay Sold data should enter Onecool OS as source observations. It should then
be mapped into independent valuation records. It must remain inspectable by
Dashboard, Decision Queue, OFAI Context, and future review workflows.

## Primary Market Price Definition

Primary Market Price represents the most realistic price at which the asset
could likely be sold today.

For Collectible Radar MVP and Beta:

1. eBay Sold is the sports-card Primary Market Price source when data is safely
   available.
2. Validation Sources compare against eBay Sold.
3. Source disagreement remains visible.
4. eBay Sold records never overwrite valuation history.
5. eBay Sold records never decide a final market value by themselves.

## Approved Ingestion Options

Approved ingestion options, in preferred order:

1. Official eBay API if allowed and available
2. User-provided export CSV / JSON
3. Manual fixture import

Official API work must happen only after review of developer account terms,
allowed endpoints, scopes, rate limits, data retention rules, and production
credential handling.

User-provided exports and fixture imports must preserve raw source identity
without requiring Onecool OS to store eBay credentials.

## Rejected Ingestion Options

- Unauthorized scraping of eBay pages
- Browser automation that simulates user scraping
- Credential sharing or storing user eBay passwords
- Circumventing rate limits, robots controls, or platform access rules
- Treating screenshots or copied page text as authoritative machine data
- Any integration that hides source uncertainty from the user

Unauthorized scraping is not part of the MVP.

## Required Fields

Each eBay Sold observation must provide:

- `asset_id` or `asset_hint`
- `sale_price`
- `currency`
- `sale_date`
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
- `shipping`
- `buyer_country`
- `seller_country`
- `raw_payload`

Optional fields should be preserved when available, but missing optional fields
must not be fabricated.

## Currency Handling

The source currency must be preserved exactly as reported by eBay or by the
user-provided export. The importer should normalize currency codes to uppercase
ISO-style strings when possible.

Currency conversion is out of scope for the eBay Sold importer. Future
valuation or analytics layers may handle currency conversion explicitly.

## Shipping Handling

Shipping must be preserved as a separate optional field when available.

The importer must not silently add shipping to `sale_price` or subtract it from
the price. Future policy can decide whether market value uses:

- item price only
- item price plus shipping
- regional shipping-adjusted comparisons

Until then, eBay Sold import should preserve both `sale_price` and `shipping`
as source facts.

## Transaction Date Handling

`sale_date` is required and should represent the completed sale date or
transaction date from the source. If the official API distinguishes sold date,
paid date, and shipped date, the importer should preserve the most relevant
completed-sale date as `sale_date` and place the others in metadata.

The importer must not use system time as a substitute for missing `sale_date`.

## Duplicate Detection

Duplicate detection should use deterministic priority:

1. `external_id`
2. source URL/reference
3. asset identity plus `sale_price`, `currency`, and `sale_date`

When duplicate certainty is low, the record should be marked `NEEDS_REVIEW`
rather than discarded silently.

## Source URL And Reference Handling

Every eBay Sold record should preserve either:

- official `external_id`
- source URL
- user-provided reference

This reference should flow into valuation metadata and audit context so users
can verify the source later.

## ImportAudit Usage

eBay Sold imports must create `ImportAudit` records with:

- source: `EBAY_SOLD`
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

- Do not store eBay credentials in MVP.
- Do not request user passwords.
- Prefer local exports or official OAuth/API flows after security review.
- Keep raw source files under user-controlled import directories.
- Do not commit private imports.
- Preserve only the metadata required for reproducibility, audit, and user
  review.

## Legal And Terms Risk

Risk level: `NEEDS_REVIEW`.

Official API integration requires review of eBay developer terms, endpoint
permissions, data retention limits, and allowed display/use cases.

Manual exports require clear user instructions that the user is responsible for
exporting or providing data they are allowed to use.

Unauthorized scraping has high legal and terms risk and is rejected for MVP.

## Implementation Complexity

Complexity: `MEDIUM`.

Local CSV / JSON import is moderate because field mapping, duplicate detection,
and source preservation are straightforward.

Official API integration is higher complexity because it requires OAuth,
credential storage, rate limits, paging, retries, error handling, and legal
review.

## MVP Recommendation

MVP readiness: `NEEDS_REVIEW`.

Recommended Beta path:

1. Implement eBay Sold manual CSV / JSON import first.
2. Preserve source identity and raw payloads when allowed.
3. Map records into independent `ValuationRecord` entries.
4. Keep eBay Sold as Primary Market Price.
5. Use Card Ladder, PWCC, Goldin, Fanatics Collect, and Manual valuations as
   Validation Sources.
6. Keep source disagreement visible in Market Intelligence, Dashboard,
   Decision Queue, and OFAI Context.
7. Defer official eBay API until API terms, auth, credentials, and security
   design are reviewed.
