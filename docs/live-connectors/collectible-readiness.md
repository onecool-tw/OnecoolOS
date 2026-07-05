# Collectible Radar Live Connector Readiness

This document reviews planned Collectible Radar data sources and defines the
safest ingestion path for real-world data.

Collectible Radar must prefer safe, user-approved, export-based or API-based
ingestion. Unauthorized scraping is not part of the MVP.

## Readiness Statuses

- `READY`: Safe enough for MVP implementation using local files or explicit
  user-provided exports.
- `NEEDS_REVIEW`: Viable only after API terms, export availability,
  authentication, and usage limits are reviewed.
- `DEFER`: Useful later, but not required for MVP.
- `NOT_RECOMMENDED`: Should not be implemented due to safety, legal, or data
  quality concerns.

## Source Review

### PSA Collection CSV

| Field | Review |
| --- | --- |
| Source name | PSA Collection CSV |
| Current status | Local CSV connector exists for user-exported PSA collection files. |
| Preferred ingestion method | Manual export CSV import. |
| Fallback ingestion method | User-maintained CSV template that follows the PSA export columns. |
| Authentication requirement | None for local file import. User authenticates directly with PSA outside Onecool OS. |
| API availability assumption | No API dependency for MVP. |
| Scraping risk | Low. No scraping required. |
| Data freshness expectation | User-controlled; freshness depends on latest manual export. |
| Legal / terms risk | Low when the user exports their own collection data and imports it locally. |
| Implementation complexity | Low. |
| MVP readiness | READY |
| Next step | Harden real PSA CSV import validation and document user export workflow. |

### eBay Sold

| Field | Review |
| --- | --- |
| Source name | eBay Sold |
| Current status | Local fixture connector exists for normalized eBay Sold-style records. |
| Preferred ingestion method | Approved API or manual export / fixture import. Avoid scraping. |
| Fallback ingestion method | User-provided CSV or JSON import from approved/exported sold-comps data. |
| Authentication requirement | Required for official API access; none for local user-provided exports. |
| API availability assumption | API access may be possible but requires developer account, scopes, rate limits, and terms review. |
| Scraping risk | High if implemented through unauthorized scraping; not part of MVP. |
| Data freshness expectation | High if API-backed; manual/export freshness depends on user update cadence. |
| Legal / terms risk | Medium to high until approved API/export terms are verified. |
| Implementation complexity | Medium. |
| MVP readiness | NEEDS_REVIEW |
| Next step | Review approved eBay data access options and define a local import schema before any live integration. |

### Card Ladder

| Field | Review |
| --- | --- |
| Source name | Card Ladder |
| Current status | Local fixture connector exists for Card Ladder-style records. |
| Preferred ingestion method | Official export or manual export if available. Avoid unauthorized scraping. |
| Fallback ingestion method | User-provided CSV or JSON import when allowed by user subscription/export terms. |
| Authentication requirement | Likely required for platform access; local exports require no Onecool OS credential storage. |
| API availability assumption | Unknown for MVP; must be reviewed before implementation. |
| Scraping risk | High if export/API is unavailable; unauthorized scraping is not allowed. |
| Data freshness expectation | Good if official export/API exists; otherwise user-controlled. |
| Legal / terms risk | Medium to high until platform terms and export rights are reviewed. |
| Implementation complexity | Medium. |
| MVP readiness | NEEDS_REVIEW |
| Next step | Confirm whether official export/API access exists and document allowed fields. |

### PWCC

| Field | Review |
| --- | --- |
| Source name | PWCC |
| Current status | Local fixture connector exists for PWCC-style records. |
| Preferred ingestion method | Manual export / approved API if available. |
| Fallback ingestion method | User-provided CSV or JSON import from approved account/export data. |
| Authentication requirement | Required for official account/API workflows; none for local user-provided files. |
| API availability assumption | Unknown for MVP; requires review. |
| Scraping risk | High if implemented through unauthorized scraping; not part of MVP. |
| Data freshness expectation | Moderate to high if official export/API is available; otherwise user-controlled. |
| Legal / terms risk | Medium until terms and export rights are verified. |
| Implementation complexity | Medium. |
| MVP readiness | NEEDS_REVIEW |
| Next step | Review export/API options and build only local import support first. |

### Goldin

| Field | Review |
| --- | --- |
| Source name | Goldin |
| Current status | Local fixture connector exists for Goldin-style records. |
| Preferred ingestion method | Manual export / approved API if available. |
| Fallback ingestion method | User-provided CSV or JSON import from approved account/export data. |
| Authentication requirement | Required for official account/API workflows; none for local user-provided files. |
| API availability assumption | Unknown for MVP; requires review. |
| Scraping risk | High if implemented through unauthorized scraping; not part of MVP. |
| Data freshness expectation | Moderate to high if official export/API is available; otherwise user-controlled. |
| Legal / terms risk | Medium until terms and export rights are verified. |
| Implementation complexity | Medium. |
| MVP readiness | NEEDS_REVIEW |
| Next step | Review export/API options and define a local validation-source import schema. |

### Fanatics Collect

| Field | Review |
| --- | --- |
| Source name | Fanatics Collect |
| Current status | Local fixture connector exists for Fanatics Collect-style records. |
| Preferred ingestion method | Manual export / approved API if available. |
| Fallback ingestion method | User-provided CSV or JSON import from approved account/export data. |
| Authentication requirement | Required for official account/API workflows; none for local user-provided files. |
| API availability assumption | Unknown for MVP; requires review. |
| Scraping risk | High if implemented through unauthorized scraping; not part of MVP. |
| Data freshness expectation | Moderate to high if official export/API is available; otherwise user-controlled. |
| Legal / terms risk | Medium until terms and export rights are verified. |
| Implementation complexity | Medium. |
| MVP readiness | NEEDS_REVIEW |
| Next step | Review export/API options and define a local validation-source import schema. |

### Manual Import

| Field | Review |
| --- | --- |
| Source name | Manual import |
| Current status | Golden Dataset and local fixture patterns are available for CSV / JSON inputs. |
| Preferred ingestion method | CSV / JSON fixture import. |
| Fallback ingestion method | User-maintained spreadsheet exported to CSV. |
| Authentication requirement | None. |
| API availability assumption | No API dependency. |
| Scraping risk | Low. No scraping required. |
| Data freshness expectation | User-controlled. |
| Legal / terms risk | Low when users enter or export their own data. |
| Implementation complexity | Low. |
| MVP readiness | READY |
| Next step | Define manual valuation import templates for primary market and validation-source records. |

## Implementation Order Recommendation

1. PSA Collection CSV real import
2. Manual valuation import
3. eBay Sold approved/manual import
4. Card Ladder approved/manual import
5. PWCC / Goldin / Fanatics as validation sources

## MVP Rules

- Prefer user-approved exports, local files, or approved APIs.
- Preserve source identity and raw payloads when allowed.
- Store source records independently; do not overwrite valuation history.
- Keep eBay Sold as Primary Market Price for sports cards when data is safely
  available.
- Treat Card Ladder, PWCC, Goldin, Fanatics Collect, and Manual records as
  validation sources unless a future ADR changes that role.
- Avoid unauthorized scraping.
- Do not store private platform credentials until a dedicated credential and
  security review is complete.
- Do not call live APIs from tests.
