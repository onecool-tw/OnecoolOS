# Collectible Radar Real Data Trial Results

Trial date: 2026-07-07

This document records the first local real-data validation attempt for
Collectible Radar Beta. It contains aggregate statistics only and does not
include private collection details, card identities, source exports, valuation
records, or generated private reports.

## Trial Summary

Status: `PARTIAL / BLOCKED`

The local sports card portfolio file was present and importable. The available
dataset contained 1 card, which is below the trial minimum of 10 cards and
below the recommended 30-50 card dataset.

No local PSA Collection CSV, eBay Sold manual import file, Card Ladder manual
import file, or Manual Valuation import file was found under `imports/` or the
expected local trial paths during this run.

Because valuation source files were unavailable, the complete deterministic
pipeline could not be executed end to end.

## Local Data Found

Aggregate local data inventory:

- Sports cards portfolio JSON: present
- Sports cards imported count: 1
- Base currency: TWD
- Status counts: Owned 1
- PSA Collection export: not found
- Manual Valuation import file: not found
- eBay Sold manual import file: not found
- Card Ladder manual import file: not found

Private data handling:

- No private card identity was copied into this document.
- No private source export was committed.
- No private valuation data was committed.
- Private portfolio JSON remains ignored by `.gitignore`.

## Pipeline Validation

| Layer | Expected | Actual | Difference |
| --- | --- | --- | --- |
| PSA Collection Import | Import 10-20 real cards from PSA CSV | Not executed | PSA CSV not found |
| Normalize | Normalize imported records | Not executed | Source import unavailable |
| Assets | Load real sports card assets | Partial success | Local JSON loaded 1 card only |
| Valuation | Preserve valuation history | Not executed | Valuation files not found |
| Source Agreement | Compare eBay Sold with Validation Sources | Not executed | Required valuation records unavailable |
| Market Intelligence | Consume SourceAgreementResult | Not executed | Source Agreement unavailable |
| Collectible Intelligence | Produce quality signals | Not executed | Market Intelligence unavailable |
| Radar | Detect signal changes | Not executed | Intelligence outputs unavailable |
| Timeline | Summarize Radar history | Not executed | Radar snapshots unavailable |
| Dashboard | Present deterministic outputs | Not executed | Upstream outputs unavailable |
| Daily Report | Assemble user-facing report | Not executed | Dashboard output unavailable |
| Decision Queue | Prioritize review items | Not executed | Daily Report unavailable |
| OFAI Context | Prepare deterministic context | Not executed | Decision Queue unavailable |

## Trial Metrics

| Metric | Result |
| --- | --- |
| Import Accuracy | Partial: local cards JSON import succeeded |
| Matching Accuracy | Not measured |
| Missing Valuation Rate | Not measured |
| Source Agreement Rate | Not measured |
| Dashboard Accuracy | Not measured |
| Report Accuracy | Not measured |
| Decision Queue Accuracy | Not measured |
| User Satisfaction | Not measured |

## ImportAudit Review

ImportAudit could not be validated in this run because no connector source
file was available for PSA, eBay Sold, Card Ladder, or Manual Valuation import.

The local sports cards JSON loader validated that the private portfolio file is
readable, but that loader is not the same as the connector ImportAudit path.

## Issues Found

1. Trial dataset is too small.
   - Expected: 10-20 cards minimum
   - Actual: 1 card
   - Impact: cannot validate matching quality, source coverage, dashboard
     accuracy, report quality, or decision queue usefulness.

2. PSA Collection source export is missing.
   - Expected: local PSA Collection CSV under ignored `imports/` path
   - Actual: no source CSV found
   - Impact: PSA connector path and ImportAudit cannot be validated.

3. Valuation source files are missing.
   - Expected: eBay Sold manual import, Card Ladder manual import, and/or
     Manual Valuation import
   - Actual: no local valuation source files found
   - Impact: Valuation, Source Agreement, Market Intelligence, Dashboard,
     Daily Report, Decision Queue, and OFAI Context cannot be validated with
     real data.

## Strengths

- Private sports card portfolio JSON remains local and ignored.
- Local cards import succeeds on the available real-data file.
- Documentation and privacy boundaries are clear enough to avoid committing
  private collection data.
- The trial process correctly refused to infer or fabricate missing valuation
  sources.

## Improvement Opportunities

- Prepare a minimum 10-card PSA Collection CSV export under `imports/psa/`.
- Prepare eBay Sold manual CSV / JSON observations for the same card subset.
- Prepare Card Ladder manual CSV / JSON observations for the same card subset.
- Prepare Manual Valuation CSV / JSON observations for any cards missing
  eBay or Card Ladder data.
- Store private generated trial outputs outside Git or in ignored paths.
- Repeat the trial with enough records to measure source agreement and report
  quality.

## Acceptance Status

Status: `NOT PASSED`

Acceptance criteria review:

- Imports succeed: partial, local cards JSON import succeeded
- Valuation history preserved: not measured
- eBay remains Primary Market Price: not measured
- Card Ladder remains Validation Source: not measured
- Disagreement remains visible: not measured
- Dashboard matches expected values: not measured
- Daily Report matches manual review: not measured

The trial does not pass because the dataset is below minimum size and required
valuation source files are unavailable.

## Recommendations

1. Prepare a 10-20 card real-data trial packet locally.
2. Include PSA, eBay Sold, Card Ladder, and Manual Valuation files where
   possible.
3. Keep all raw trial files under ignored `imports/` paths.
4. Run connector imports with a fixed reference datetime.
5. Record only aggregate metrics in committed documentation.
6. Repeat the full pipeline after source files are available.

## Next Trial Run Checklist

- [ ] PSA Collection CSV available locally
- [ ] eBay Sold manual file available locally
- [ ] Card Ladder manual file available locally
- [ ] Manual Valuation file available locally when needed
- [ ] At least 10 cards included
- [ ] Reference datetime selected
- [ ] ImportAudit output reviewed
- [ ] Source Agreement output reviewed
- [ ] Dashboard output compared with manual review
- [ ] Daily Report output compared with manual review
- [ ] Decision Queue priorities manually reviewed

