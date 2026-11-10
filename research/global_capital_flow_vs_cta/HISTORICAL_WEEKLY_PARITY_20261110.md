# Historical CTA weekly-completion replay comparison — 2026-11-10

## Actually calculated

Read GitHub `main` adjusted-close histories (QQQ, SOXX, 0050) and independently implemented the frozen production `_detect_cross` / `cross_priority_cta` formula in an isolated JavaScript execution. Two historical cutoff policies were compared:

- **Rolling-week (production-function-compatible):** all prices through the market session close, treating that week's newest observation as the latest weekly point, as `calculate_cta()` does by default.
- **Confirmed-week research:** retain a weekly point in current ISO week only if a closed Friday bar exists; otherwise use completed prior ISO weeks. Holiday-shortened weeks are conservatively excluded until next ISO week.

After daily-200/weekly-50 warmup, both policies agree on every Friday observation (weekly state and CTA label):

| Asset | Fridays matching | Non-Friday eligible | Non-Friday label discrepancies | Non-Friday weekly-state discrepancies |
|---|---:|---:|---:|---:|
| QQQ | 219 / 219 | 866 | 8 | 866 |
| SOXX | 205 / 205 | 811 | 20 | 811 |
| 0050 | 203 / 203 | 846 | 17 | 846 |
| **Total** | **627 / 627** | **2,523** | **45** | **2,523** |

The weekly cross state differs every eligible non-Friday by at least age/spread/point timestamp, even when the trading label is unchanged.

**Interpretation:** This is an *independent numerical reconstruction*, NOT executed production Python parity tests or a certified full historical strategy return. The comparator reuses the same definitions/formulas, so Friday equality is expected. Historical dividend/split values may have current-date revisions.

## Critical research implications

1. Do not publish previously exploratory price-only CTA CAGR/MDD as official results. They assumed a research week-completion policy, not necessarily the original production engine's default historically intrawEEK snapshot semantics.
2. Maintain separate explicitly named arms for rolling-week production-function semantics and confirmed-week research semantics. Never silently switch between them.
3. Trade decisions can be implemented only when closed price bars are truly observed and traded next eligible session. A Friday market holiday needs official trading-calendar verification before labeling a Thursday bar completed-week close.
4. Confirm 45 label-difference dates and trades with the actual checked-out Python engine, independently of the JavaScript reproduction.
5. Macro-flow and hybrid backtests still blocked by archived WALCL and HY-OAS first-availability evidence and a verified synchronized sample.
6. `main`, live CTA, Dashboard, workflows and schedules must remain unchanged.

## Scope and reproducibility

Repository `research/global_capital_flow_vs_cta/test_cta_replay.py` checks historical Friday parity against `calculate_cta` on actual CSVs, but its execution through GitHub Actions has not been established. Latest published snapshot three-way parity previously observed. As of this audit, no production-system change or merge has been made.
