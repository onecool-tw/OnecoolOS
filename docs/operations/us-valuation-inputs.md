# US valuation inputs

The daily updater reads `data/market/us_stock_intelligence/reviewed_valuation_inputs.json` before requesting SEC Company Facts. This is a reviewed official issuer reference fallback, not a successful SEC fetch and not an automatically refreshed issuer feed.

Each reference has symbol/company identity, publication date, expiry, reported financial facts, original issuer URLs, and specific model gaps. Publication must precede the scan cutoff; expired references fall back to SEC. New earnings, guidance or material transactions require updating the reference; the current five references expire 2026-10-14. No quarterly EPS annualization, implicit ADR currency conversion, or unsourced fair multiple is permitted.

Optional `valuation_model` records require method, USD denominator per listed security, normalization bridge, denominator source, fair multiple range, range rationale/sources, rationale and policy version. Range assumptions must be identified as Onecool analyst assumptions rather than issuer guidance. Model gaps must be empty before a model may form an opinion. Cyclical/capital intensive names require a researched mid-cycle/FCF crosscheck; acquisitions require a normalized earnings and net debt bridge.

Daily prices come only from the validated scan history at its exact cutoff. The computed price/multiple and PASS/FAIL are checked by the existing `super_growth_quality._verified_gate`, then saved/read back before publishing quality annotations. A computed opinion expires the same session. Missing prices, invalid candidates and rejected models invalidate an older opinion. CTA, scores and technical ranking are untouched.

As of 2026-10-06, five reviewed models are populated. These are Onecool screening scenario valuations, not issuer fair values or full investment-grade DCFs. They cannot change CTA, technical ranking or scores and do not authorize automatic trades. A FAIL means above this explicitly conservative discipline, not an assertion that the market price must fall.

Policy `onecool_equity_two_stage_screen_v1` values five years of equity cash distributions plus a terminal perpetuity. For an EPS denominator, cash conversion represents assumed distributable cash/earnings; for the SBC-costed owner-FCF proxy it is 1. Formula: sum(cash_conversion * (1+growth)^t / (1+required_return)^t, t=1..5) + terminal_cash_conversion * (1+growth)^5 * (1+terminal_growth) / ((required_return-terminal_growth) * (1+required_return)^5). Method reference: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/invfables/peratio.htm . The source supports the method, not our numeric assumptions.

Both scenarios use analyst required returns 12%/10% and terminal growth 2%/3%; these are investment hurdles, not measured market WACC. Fair range spans conservative/base cases, excludes an optimistic bull case, and is computed without using current market prices. No safety margin is implied by merely being inside the range. Cash conversion and growth remain uncertain scenario assumptions; a full reinvestment/ROE forecast has not been certified.

| Company | Five-year growth conservative/base | Cash conversion conservative/base | Terminal cash conversion | Rationale |
|---|---|---|---|---|
| ABBV | 5%/10% | 55%/70% | 85%/90% | Acquisition dilution, IPR&D and leverage constrain distribution. |
| DDOG | 15%/25% | 100%/100% | 100%/100% | Denominator is cash flow after full economic SBC charge; growth persistence remains uncertain. |
| AMD | 8%/15% | 50%/65% | 80%/85% | Historical two-year earnings anchor and cycle-sensitive demand; no peak-quarter annualization. |
| TSM ADR | 8%/15% | 40%/50% | 80%/85% | Historical two-year ADR earnings anchor; substantial capital spending limits cash distributions. |
| NVDA | 15%/25% | 60%/70% | 85%/90% | AI growth tempered by customer concentration, reinvestment and growth fade. |

Every denominator stores source URLs, units, period, arithmetic bridge and limitations. AMD's 13% item-tax normalization is an assumption using the issuer normalized rate. TSM USD ADR figures are issuer quarterly rounded values, not current-FX translations; the two-year anchor is a conservative historical proxy, not proven mid-cycle earnings. NVDA retains SBC using issuer recast financials. DDOG owner-FCF proxy is not GAAP EPS. ABBV holds operating earnings constant while applying full-year acquisition dilution; its debt bridge is estimated rather than an observed post-closing balance. The base/conservative assumptions should be reconsidered with each earnings/event refresh; reference expiry is 2026-10-14, with prices revalidated every trading session. This registry is not an automatic issuer-event detector.

Validation: twelve direct regression functions cover original input collection, source expiry/mapping, missing same-date prices, stale PASS invalidation, invalid units, exact cash-flow math, divergent terminal assumptions, scenario-range tampering and committed denominator arithmetic. They can also run under pytest.
