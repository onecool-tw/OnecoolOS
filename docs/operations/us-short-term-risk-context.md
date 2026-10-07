# US short-term risk context

Dashboard publishes `us_short_term_risk_context`: VIX (^VIX), DXY (DX-Y.NYB), US10Y (^TNX), US30Y (^TYX) and SOX (^SOX). Reuse staged VIX/DXY/US30Y history; fetch only missing index series. Require exactly one valid positive OHLC observation at Dashboard expected_as_of. No previous-session substitution, provisional current-session bar, aggregate score or CTA override is permitted. Yield values are percentage points; index values are index points. Each row carries its source and observation hash.

Optional context failure produces PARTIAL and a specific UNKNOWN row while leaving validated core CTA publication available. READY means all five dated observations exist; it does not itself activate or release a risk brake. Reports must read these fields before labelling a missing data gap. Dashboard also exposes the latest recorded quarterly universe review whose review_cutoff does not exceed expected_as_of; audit status is not a fresh daily re-review.
