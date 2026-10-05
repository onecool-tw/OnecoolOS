# Taiwan final context regression v1

The frozen baseline is the verified 2026-10-05 formal SSOT and delivered
Snapshot. Original source bytes are pinned by the Snapshot provenance hashes.
The private complete report and Gmail responses are not published here; only
the verified artifact and Snapshot SHA-256 are retained in the fixture.

Run `python scripts/check_taiwan_regression.py` after installing the project.
It verifies the frozen inputs, replays the existing context merger and Snapshot
projection at a fixed completed-session timestamp, and compares every decision
field to the verified golden output. It never fetches feeds, recalculates CTA,
evaluates a pressure light or reranks candidates. This establishes a **consumer
and publication regression baseline**, not a new CTA backtest.

The fixture is `tests/fixtures/taiwan_final_regression_v1.json.gz`. Its compressed
SHA-256 is pinned in the checker. Deliberate investment-rule changes require a
reviewed, separately versioned baseline and an explanation of differences;
automatic baseline replacement is forbidden. A failed replay stops publication.

`Refresh Taiwan Final Context` follows Dashboard, Screen, Taiwan CTA and pressure
persistence completion. It shares the Screen/pressure lock, reads latest main,
merges the existing formal inputs and atomically commits context, Snapshot,
regression status and health. A rejected push restarts the merge on newer inputs;
it never rebases a previously derived Snapshot over a newer Dashboard.

The formal pressure object is preserved. Same-day pressure, actual Screen date
and READY pressure inputs remain mandatory for final email readiness. Health
and publication do not establish email/conversation delivery. This workflow
does not send or resend mail, and does not modify the user's report schedule.
