# Global Capital Flow vs CTA — final decision audit (2026-11-10)

**Decision: KEEP PRODUCTION CTA UNCHANGED. DO NOT DEPLOY A CAPITAL-FLOW GATE.**

**Evidence grade**
- Price-only original-CTA comparison: EXPLORATORY (historical adjusted price snapshots, not certified PIT prices/fees/exchange calendar).
- Capital-flow-only and capital-flow+CTA: NOT TESTED ON A VERIFIED POINT-IN-TIME FACTOR PANEL. No performance claims.
- 2010–2026 four-strategy experiment: **NOT COMPLETABLE** from the current repository snapshots and publicly demonstrated source evidence. This is a data-limited research outcome, not a performance conclusion.

## Audited price-only comparison

Sources: `main:data/market/dashboard/history/{QQQ,SOXX,0050}.csv`, common strategy-eligibility windows, shared CTA `calculate_cta`, separate confirmed-Friday replay. Signal after close, execute next session open, value at subsequent open using approximated adjustment `open * adjusted_close/close`. Initial position flat; BUY enters, SELL exits, HOLD/WATCH preserve. 0 or 10 basis points charged per position change. Different tickers have different sample windows.

| Ticker | Eligible valuation window | Buyhold CAGR | Rolling-week CTA CAGR | Confirmed-Friday CTA CAGR | Buyhold MDD | Rolling/confirmed CTA MDD |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| QQQ | 2022-07-18 — 2026-11-09 | 21.385% | 18.760% | 18.462% | -24.171% | -24.171% |
| SOXX | 2022-10-24 — 2026-11-09 | 40.668% | 23.474% | 23.944% | -42.790% | -36.377% |
| 0050 | 2022-07-18 — 2026-11-10 | 36.822% | 31.525% | 30.774% | -25.206% | -25.206% |

Zero-fee descriptive returns above. At 10bp per-side: QQQ 18.732% vs 18.434%, SOXX 23.382% vs 23.852%, 0050 31.433% vs 30.683% for rolling vs confirmed respectively. These price-only outcomes were calculated in separate JavaScript analysis of repository series. `price_cta_comparison.py` is committed for independent Python repetition but the GitHub branch has **zero workflow runs** as checked on 2026-11-10; full Python CI return parity is NOT claimed.

On 627 Friday comparable observations, reconstructed weekly crossover state agreed for both policies. Of 2,523 non-Friday observations, 45 action labels differed: 8 QQQ, 20 SOXX, 17 0050. No conclusion that the 45 differences add real investment value. Weekly data, trade-date calendar and revised price adjustments are not PIT certified.

## Macro data gate — why no four-strategy conclusion

- Fed H.4.1 releases usually Thursday 4:30 PM Eastern, may shift on holidays; observation dates cannot be used as decision times. Official calendar https://www.federalreserve.gov/releases/h41/ .
- ALFRED vintage/realtime metadata can reconstruct data known on historical dates, but historical *intraday* availability, actual series-release revision link, and licensing require further evidence: https://fred.stlouisfed.org/docs/api/fred/realtime_period.html .
- ICE BofA HY OAS (`BAMLH0A0HYM2`) FRED publicly limits data to about 3 years starting April 2026, and ALFRED release metadata is not a vetted 2010-2026 PIT source. https://fred.stlouisfed.org/series/BAMLH0A0HYM2 .
- BAA10Y is an ALFRED-vintaged **investment-grade Baa/Treasury spread**, not the HY OAS; it may be a distinct sensitivity project, **never silently substituted into the original hypothesis**. https://alfred.stlouisfed.org/series?seid=BAA10Y .
- `main` price caches start in July/November 2021, not 2010. As of this audit, no documented complete price plus factor first-release common session set is assembled.
- `pit_guard.py` checks date format, source/evidence identifier presence and visible-vintage logic, but **does not authenticate true source content or its earliest publication timestamp**.

## Decisions

1. **Do not integrate a global-flow signal** into formal CTA, Dashboard, scheduled tasks, market-pressure, or portfolio execution. The hypothesis remains UNPROVEN, not falsified.
2. Keep the currently produced rolling-week CTA engine unchanged. The research confirmed-week variation is a separate exploratory arm and must not be deployed as an unreviewed rule change.
3. Treat the 2022–2026 price-only CTA comparison as evidence that in this particular selected interval buy/hold generated more returns, while SOXX CTA reduced MDD; not a prediction and not full historical validation.
4. **Close this research phase as BLOCKED BY EVIDENCE** rather than asserting that it succeeded. Reopen only when independent first-available macro vintages, historic 2010+ adjusted prices, authentic exchange calendars, a clean historical Python replay, fee/slippage and walk-forward tests are available.
5. Preserve Draft PR #146 as an auditable research archive. No merge or main changes.

## Audit distinctions

- Local synthetic tests previously run in isolated environments: PIT 14/14, execution 9/9.
- 3/3 latest CTA published snapshots matched numerically in separate reconstruction.
- 627 Friday candidate cross-policy comparisons matched numerically; this does not establish executed GitHub Python CI or end-to-end PIT certification.
- Zero CI workflow runs found on the research branch at the audit time.
