# US valuation inputs

The daily updater reads `data/market/us_stock_intelligence/reviewed_valuation_inputs.json` before requesting SEC Company Facts. This is a reviewed official issuer reference fallback, not a successful SEC fetch and not an automatically refreshed issuer feed.

Each reference has symbol/company identity, publication date, expiry, reported financial facts, original issuer URLs, and specific model gaps. Publication must precede the scan cutoff; expired references fall back to SEC. New earnings, guidance or material transactions require updating the reference; the current five references expire 2026-10-14. No quarterly EPS annualization, implicit ADR currency conversion, or unsourced fair multiple is permitted.

Optional `valuation_model` records require method, USD denominator per listed security, normalization bridge, denominator source, fair multiple range, range rationale/sources, rationale and policy version. Range assumptions must be identified as Onecool analyst assumptions rather than issuer guidance. Model gaps must be empty before a model may form an opinion. Cyclical/capital intensive names require a researched mid-cycle/FCF crosscheck; acquisitions require a normalized earnings and net debt bridge.

Daily prices come only from the validated scan history at its exact cutoff. The computed price/multiple and PASS/FAIL are checked by the existing `super_growth_quality._verified_gate`, then saved/read back before publishing quality annotations. A computed opinion expires the same session. Missing prices, invalid candidates and rejected models invalidate an older opinion. CTA, scores and technical ranking are untouched.

As of 2026-10-06, the five official references are populated, but no complete fair-value model has been approved into this registry. Valuations remain UNKNOWN with specific research gaps; this repair does not certify valuations as complete. It removes SEC access as the sole input path and prevents a previous price gap from being carried forward after current prices are available.

Validation: nine direct regression test functions in `tests/test_us_valuation_inputs.py` cover point-in-time filings, exact prices, provider errors, official fallback, full model calculation, expiry, identity, stale PASS invalidation, and invalid model units/evidence. These can also run under pytest.
