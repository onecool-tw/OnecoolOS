# Independent research checkpoint: 2026-11-10

## Checks actually executed in this session

- Isolated local PIT tests: **14/14** pass (`/mnt/data/flow_stage`, not repository CI).
- Isolated local execution ledger tests: **9/9** pass (`/mnt/data/onecool_backtest_stage`, not repository CI).
- Cross-checked most recent shared engine signal calculations against authoritative `main` snapshots and CSVs: **QQQ, SOXX, 0050 3/3** agree on CTA label and every field of daily/weekly cross state (alignment, crossing status/date, age, spread, phase).
  - QQQ: 2026-11-09 HOLD
  - SOXX: 2026-11-09 HOLD
  - 0050: 2026-11-10 HOLD
- Eligible Friday observation candidates after 200-day / 50-week warmup: **QQQ 219; SOXX 205; 0050 203 (627 total)**. **Candidates are not historical test pass counts**.
- Committed `test_published_parity.py` so future repository test execution can check all three against frozen shared engine.
- GitHub API reported **zero workflow runs** on this research branch and **zero check runs** on the earlier research SHA. Therefore claim no GitHub CI pass and no confirmed completion of full historical parity.

## Important limitations

- Checking published latest CTA output is a spot-check, not independent parity across historical completed sessions. Current production `calculate_cta` derives an ISO-week last observation even for a partially completed current week; research-only `replay_signal` conservatively excludes provisional non-Friday weeks. These signals are **not guaranteed identical** on Monday–Thursday.
- Historical split/dividend adjustments in currently revised caches are not proven to equal what was observable at each historical date.
- Macro vintage ledger remains missing verified release-specific WALCL and HY OAS data; no true historical four-strategy returns should be reported.
- The price-only exploratory CAGR/MDD from preceding chat is not a vetted research outcome.
- Saturday/holiday / early exchange close conditions require independent session-calendar validation.
- The isolated original ledger tests do not establish model parameters, strategy validity, or no-lookahead macro releases.

## Next gate

Build, run and archive read-only full historical CTA-versus-replay parity with actual market calendars and closed sessions. Independently source and authenticate archived first-available macro vintages, then form a common PIT sample and execute fees/slippage and walk-forward tests. Do not alter live CTA, Dashboard, workflow or main.
