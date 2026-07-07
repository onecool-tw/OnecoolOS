# Collectible Radar Real Data Trial

This document prepares the first real-world Collectible Radar Beta trial using
the owner's actual collection.

The trial moves Collectible Radar from architecture validation to product
validation. It must remain local-file based, deterministic, and private-data
safe.

## Trial Objectives

The first trial should validate:

- [ ] PSA Collection Import
- [ ] Manual Valuation Import
- [ ] eBay Sold Manual Import
- [ ] Card Ladder Manual Import
- [ ] Source Agreement
- [ ] Market Intelligence
- [ ] Dashboard
- [ ] Daily Report
- [ ] Decision Queue
- [ ] OFAI Context

## Trial Dataset

Recommended trial dataset:

- Minimum: 10 cards
- Recommended: 30-50 cards
- Ideal: user's complete PSA Collection

Dataset guidance:

- Use real owner collection data only in local ignored files.
- Store raw source exports under `imports/`.
- Store normalized private portfolio data under `data/portfolio/`.
- Do not commit real PSA exports, eBay exports, Card Ladder exports, manual
  valuations, or generated private reports.
- Include a mix of high-confidence cards, low-confidence cards, stale
  valuation examples, and source-disagreement examples.

## Trial Inputs

Expected local inputs:

- PSA Collection CSV export
- Manual valuation CSV or JSON
- eBay Sold manual CSV or JSON
- Card Ladder manual CSV or JSON

All trial inputs should be user-approved exports or manually prepared files.
The trial must not call live APIs, scrape websites, or store credentials.

## Trial Metrics

### Import Accuracy

Measures whether imported rows match the source files.

Suggested calculation:

- imported rows / valid source rows
- skipped rows reviewed manually
- invalid rows explained by deterministic warnings

### Matching Accuracy

Measures whether source observations match the intended card records.

Suggested review:

- PSA cert number match
- external ID or URL/reference preservation
- asset hint completeness
- manual review rate for uncertain matches

### Missing Valuation Rate

Measures cards without usable valuation observations.

Suggested calculation:

- cards missing eBay Sold Primary Market Price
- cards missing Validation Sources
- cards missing all valuation records

### Source Agreement Rate

Measures how often Primary Market Price and Validation Sources are close.

Suggested buckets:

- Strong / Good agreement
- Fair agreement
- Weak agreement
- Conflict
- Unknown due to missing source data

### Dashboard Accuracy

Measures whether Dashboard sections reflect the underlying deterministic
outputs.

Manual review should confirm:

- collection summary
- market intelligence summary
- radar changes
- timeline summary
- warnings
- review queue counts

### Report Accuracy

Measures whether the Daily Radar Report matches manual review.

Manual review should confirm:

- today's changes
- ready / needs review / blocked groups
- warning summary
- source conflict visibility

### Decision Queue Accuracy

Measures whether review items are prioritized correctly.

Manual review should confirm:

- Critical: missing primary market or source conflict
- High: low confidence or stale valuation
- Medium: low liquidity or missing validation source
- Low: coverage improvement or low-priority review items

### User Satisfaction

Measures whether the owner can understand and act on review outputs.

Suggested questions:

- Are the flagged cards the right cards to review?
- Are source disagreements visible enough?
- Is the Daily Radar Report useful for a daily workflow?
- Are warnings clear and non-alarming?
- Is any important source context missing?

## Acceptance Criteria

The trial passes when:

- imports succeed
- valuation history is preserved
- eBay remains Primary Market Price
- Card Ladder remains Validation Source
- disagreement remains visible
- Dashboard matches expected values
- Daily Report matches manual review

The trial should not pass if:

- source records are overwritten silently
- valuation history is replaced instead of preserved
- eBay Sold is replaced by a Validation Source
- source disagreement is hidden
- private data is committed
- any trial step requires live APIs or scraping

## Known Out Of Scope

- Live APIs
- OCR
- Scheduling
- PWCC
- Goldin
- Fanatics
- LLM recommendations
- Credential storage
- Persistent audit store
- Automated buy / sell recommendations

## Trial Procedure

1. Export PSA Collection CSV.
2. Place raw source files under the ignored `imports/` directory.
3. Prepare manual valuation, eBay Sold, and Card Ladder files locally.
4. Run importers with injected reference datetimes when possible.
5. Preserve ImportAudit output for trial review.
6. Generate valuation records and Source Agreement outputs.
7. Run Market Intelligence and Collectible Intelligence.
8. Generate Radar, Timeline, Dashboard, Daily Report, Decision Queue, and OFAI
   Context outputs.
9. Compare outputs against manual review.
10. Record trial notes outside committed source files unless anonymized.

## Trial Review Template

```text
Trial Date:
Reference Datetime:
Card Count:
PSA Import Result:
Manual Valuation Import Result:
eBay Sold Import Result:
Card Ladder Import Result:
Missing Valuation Rate:
Source Agreement Rate:
Dashboard Accuracy:
Report Accuracy:
Decision Queue Accuracy:
User Satisfaction:
Blocking Issues:
Follow-up Actions:
```

## Privacy Rules

- Do not commit real collection data.
- Do not commit raw source exports.
- Do not commit private valuation files.
- Do not commit generated private trial reports.
- Keep trial artifacts local unless anonymized.
- Use synthetic fixtures for committed regression tests.

