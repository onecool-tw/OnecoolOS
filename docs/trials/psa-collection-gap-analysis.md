# PSA Collection Gap Analysis

Analysis date: 2026-07-09

This document reviews the current PSA Collection integration against a real
owner-provided PSA Collection CSV export. It contains aggregate findings only.
No private card identities, cert numbers, row values, or source file contents
are included.

## Scope

Reviewed implementations:

- `onecool_os.connectors.collectibles.PSACollectionImporter`
- `onecool_os.assets.sports_cards.psa_csv.PsaCsvImporter`

Reviewed local source:

- PSA Collection CSV under ignored `imports/psa/`
- 33 columns
- 49 rows
- Private CSV remains ignored by `.gitignore`

Read-only connector import summary:

- Total rows: 49
- Imported rows: 44
- Skipped rows: 4
- Duplicate rows: 0
- Invalid rows: 1
- Warning categories: unsupported grader 4, invalid PSA grade 1
- Matching status: 44 new records
- ImportAudit checksum: present

## Current Mapping

The current read-only connector requires:

- `Item`
- `Subject`
- `Year`
- `Set`
- `Card Number`
- `Grade Issuer`
- `Grade`
- `Cert Number`
- `My Cost`
- `Date Acquired`
- `Source`
- `My Notes`

Current normalized output includes:

- `asset_id`: `PSA-{Cert Number}`
- `inventory_id`: `INV-PSA-{Cert Number}`
- `cert_number`: `Cert Number`
- `collection_identifier`: `Cert Number`
- `player`: `Subject`
- `year`: `Year`
- `brand`: `Set`
- `set`: `Set`
- `card_number`: `Card Number`
- `grade_company`: `Grade Issuer`
- `grade`: `Grade`
- `cost`: `My Cost`
- `purchase_date`: `Date Acquired`
- `last_inventory_update`: `Date Acquired`
- `purchase_platform`: `Source`
- `notes`: `My Notes` plus PSA item reference
- `source`: `PSA Collection CSV`
- `source_row_number`: source CSV row number
- `matching`: deterministic matching metadata

Current defaults:

- `account`: `PSA Collection`
- `asset_class`: `Sports Card`
- `status`: `Owned`
- `currency`: `USD`
- `base_currency`: `TWD`
- `owned_quantity`: `1`
- `available_quantity`: `1`
- `listed_quantity`: `0`
- `sold_quantity`: `0`
- `sport`: `Unknown`
- `collection_type`: `Investment`
- `valuation_source`: `eBay Sold`

## Field Support Classification

| PSA Field | Status | Current Behavior | Gap |
| --- | --- | --- | --- |
| `Item Status` | Not Yet Supported | Not mapped | Could drive lifecycle or inventory status |
| `Item` | Partially Supported | Preserved inside notes as PSA item reference | Not first-class source item ID |
| `Cert Number` | Fully Supported | Used for cert, asset ID, inventory ID, matching | None for MVP |
| `Grade Issuer` | Fully Supported | Required and mapped to grade company | Non-PSA rows are skipped |
| `Grade` | Partially Supported | Required numeric grade 1-10 | Non-numeric grading labels need review |
| `Autograph Grade` | Intentionally Ignored | Not mapped | Future autograph metadata if needed |
| `Year` | Fully Supported | Required and mapped to card year | None for MVP |
| `Set` | Partially Supported | Mapped to set and brand | Brand and set are not separated |
| `Card Number` | Fully Supported | Required and mapped | None for MVP |
| `Subject` | Fully Supported | Required and mapped to player | None for MVP |
| `Variety` | Not Yet Supported | Not mapped | Should map to parallel or variant |
| `Serial` | Not Yet Supported | Not mapped | Should map to card serial number, not PSA cert |
| `Category` | Not Yet Supported | Not mapped | Could map to sport/category |
| `My Cost` | Partially Supported | Required and mapped to cost | Not represented as Ledger transaction |
| `PSA Estimate` | Not Yet Supported | Not mapped | Should become PSA Estimate valuation input |
| `Gain/Loss` | Intentionally Ignored | Not mapped | Derived metric; should not be source of truth |
| `My Value` | Not Yet Supported | Not mapped | Could become manual/current owner value |
| `Date Acquired` | Partially Supported | Required as purchase date and inventory update date | Not validated as typed date; no Ledger event |
| `Source` | Partially Supported | Mapped to purchase platform | Not normalized as platform/source taxonomy |
| `My Notes` | Partially Supported | Preserved in notes with PSA item reference | Not structured |
| `Vault Status` | Not Yet Supported | Not mapped | Should become inventory custody metadata |
| `Vaulted Date` | Not Yet Supported | Not mapped | Should become inventory lifecycle event |
| `Days Vaulted` | Intentionally Ignored | Not mapped | Derived from vaulted date and reference date |
| `Listing Status` | Not Yet Supported | Not mapped | Should become listing lifecycle metadata |
| `Listing Date` | Not Yet Supported | Not mapped | Should become lifecycle event |
| `Listing Price` | Not Yet Supported | Not mapped | Should become listing price observation |
| `Sold Status` | Not Yet Supported | Not mapped | Should become sale lifecycle metadata |
| `Sold On` | Not Yet Supported | Not mapped | Should become sale platform/source |
| `Sold Date` | Not Yet Supported | Not mapped | Should become sale transaction date |
| `Sold Price` | Not Yet Supported | Not mapped | Should become sale transaction value |
| `Sold Fees` | Not Yet Supported | Not mapped | Should become transaction fee |
| `Sold Proceeds` | Not Yet Supported | Not mapped | Should become net proceeds |
| `Payment Date` | Not Yet Supported | Not mapped | Should become settlement/payment date |

## Missing Mapping

The largest gaps are:

1. PSA valuation fields
   - `PSA Estimate`
   - `My Value`

2. Inventory and custody fields
   - `Vault Status`
   - `Vaulted Date`
   - `Listing Status`
   - `Listing Date`
   - `Listing Price`

3. Sale lifecycle fields
   - `Sold Status`
   - `Sold On`
   - `Sold Date`
   - `Sold Price`
   - `Sold Fees`
   - `Sold Proceeds`
   - `Payment Date`

4. Card identity enrichment fields
   - `Variety`
   - `Serial`
   - `Category`
   - `Autograph Grade`

5. Ledger-grade acquisition fields
   - `My Cost`
   - `Date Acquired`
   - `Source`

These fields should not be stuffed into notes long term. They should flow into
Inventory, Ledger, Valuation, and lifecycle-event models through explicit
contracts.

## First-Class Metadata Evaluation

| Field | Should Become First-Class? | Reason |
| --- | --- | --- |
| `My Cost` | Yes | Acquisition cost belongs in Ledger and position cost basis |
| `PSA Estimate` | Yes | PSA Estimate is a valuation observation, likely `PSA_ESTIMATE` |
| `Date Acquired` | Yes | Acquisition date belongs in Ledger and lifecycle history |
| `Source` | Yes | Acquisition platform/source should be normalized |
| `Listing Status` | Yes | Listing state is inventory / lifecycle metadata |
| `Sold Status` | Yes | Sale state is lifecycle metadata |
| `Sold Price` | Yes | Sale price belongs in Ledger transaction history |
| `Sold Fees` | Yes | Fees belong in Ledger transaction cost fields |
| `Sold Proceeds` | Yes | Net proceeds are sale settlement data |
| `Vault Status` | Yes | Vault custody belongs in inventory metadata |

## Recommended Future Mapping

### Asset Identity

- `Cert Number` -> `cert_number`, `collection_identifier`
- `Subject` -> `player`
- `Year` -> `year`
- `Set` -> `set`
- `Card Number` -> `card_number`
- `Variety` -> `parallel` or `variant`
- `Serial` -> card `serial_number`
- `Category` -> `sport` or collectible category
- `Autograph Grade` -> autograph metadata

### Inventory

- `Item Status` -> inventory status
- `Vault Status` -> custody status
- `Vaulted Date` -> custody lifecycle event
- `Listing Status` -> listing status
- `Listing Date` -> listing lifecycle event
- `Listing Price` -> listing price observation

### Ledger

- `My Cost` -> BUY transaction amount or cost basis
- `Date Acquired` -> trade/acquisition date
- `Source` -> platform/source
- `Sold Status` -> sale lifecycle status
- `Sold On` -> sale platform/source
- `Sold Date` -> sale transaction date
- `Sold Price` -> SELL transaction amount
- `Sold Fees` -> fee
- `Sold Proceeds` -> net proceeds
- `Payment Date` -> settlement/payment date

### Valuation

- `PSA Estimate` -> valuation record with source `PSA_ESTIMATE`
- `My Value` -> manual valuation or owner value observation
- `Gain/Loss` -> intentionally not imported as source truth

### Audit

- Preserve source filename, checksum, imported row count, skipped row count,
  invalid row count, warning categories, and reference datetime through
  `ImportAudit`.

## MVP Decision

Keep current runtime behavior for MVP:

- Do not change importer behavior in this sprint.
- Keep PSA Collection import read-only in connector layer.
- Keep current required fields and validation behavior.
- Continue mapping `My Cost`, `Date Acquired`, and `Source` into existing
  normalized fields.
- Treat `PSA Estimate`, sale fields, listing fields, and vault fields as
  documented gaps.
- Do not import derived `Gain/Loss`.
- Do not commit private CSV data.

MVP priority:

1. Document gaps.
2. Preserve privacy and ImportAudit behavior.
3. Avoid broad schema changes before the real data trial has enough records.

## GA Decision

Before GA, the PSA integration should support first-class mapping for:

1. PSA Estimate as a valuation source.
2. Vault and listing statuses as inventory lifecycle metadata.
3. Sold price, fees, proceeds, and payment date as Ledger events.
4. Variety, Serial, Category, and Autograph Grade as card identity enrichment.
5. Normalized acquisition Source taxonomy.
6. Typed date validation for Date Acquired, Vaulted Date, Listing Date, Sold
   Date, and Payment Date.

GA should preserve backward compatibility by adding optional fields rather than
breaking the current normalized record shape.

## Recommended Priority

1. Add PSA Estimate valuation mapping.
2. Add Variety and Serial card identity mapping.
3. Add Vault Status inventory metadata.
4. Add Listing Status and Listing Price metadata.
5. Add Sold Status, Sold Price, Sold Fees, Sold Proceeds, and Payment Date as
   Ledger events.
6. Add typed date validation and source taxonomy.

## Architecture Impact

No runtime architecture changes were made in this sprint.

Future changes should preserve the current pipeline:

```text
PSA Collection CSV
↓
Connector
↓
Normalize
↓
Assets / Inventory
↓
Ledger
↓
Valuation
↓
Source Agreement
↓
Market Intelligence
```

PSA import should remain an ingestion layer. It should not calculate
confidence, source agreement, recommendations, or final valuation.

