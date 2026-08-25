# Onecool US Stock Intelligence cache

This directory contains machine-generated, date-auditable artifacts consumed
by the 10:30 Asia/Taipei US Stock Intelligence report.

- `portfolio_scores_latest.json`: daily BABA/XYZ/QRVO/RH/UPBD CANSLIM and
  Minervini proxy scores.
- `breakout_scan_latest.json`: daily same-cutoff Onecool Breakout Scan and at
  most five ranked candidates.
- `super_growth_evidence_latest.json`: dated, source-backed quality evidence
  for the formal US-new-candidate research gate. Missing evidence remains
  `UNKNOWN`; the gate never reorders the technical scan.

The Market Dashboard workflow refreshes the breakout scan on its three US
close runs.  A successful scan has `publication_status=CURRENT` and the same
`expected_as_of` as the Dashboard.  If a provider fails, the last successful
artifact remains unchanged and the Dashboard copy is marked `LAST_VALID` with
its actual effective date.

Scores are Onecool proxy scores, not official IBD ratings.

The Super Growth gate applies only to new US candidates. Existing portfolio
positions remain under their established CTA/thesis rules, while TSLA and SPCX
remain exempt innovation-option positions.
