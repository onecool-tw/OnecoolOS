# Taiwan common-quarter publication guard

During official quarterly filing rollovers, use one common financial period.
The latest period is eligible when at least 80% of the current liquid universe
has an official income observation. This is a data completeness guard, not a
score, valuation, industry or CTA rule.

When coverage is below that floor, the updater may use the immediately preceding
quarter's actual EPS observations from a previously verified formal Screen.
It records the exact source snapshot and SHA-256, selected and pending periods,
and missing count. It never carries prices, valuations, monthly revenue, scores,
or ranks forward; the existing sole scoring engine uses current official inputs.
The retained EPS is a reported value, never an estimate or inferred quarterly EPS.
Missing income observations remain excluded and are never filled with zero.

The preceding period must also cover at least 80% of the current universe.
If no such period is available, fail before replacing the last valid Screen.
Do not reach back multiple quarters. Full financial-quality conclusions are not
reconstructed from EPS; the existing official three-statement verifier remains
responsible for each selected company and actual financial period.

The normal data, pressure persistence, Snapshot, artifact readback and final Email
gates continue to apply. A preserved old Screen must retain its actual price date.
