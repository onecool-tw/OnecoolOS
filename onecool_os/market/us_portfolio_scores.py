"""Portfolio adapter for the exact same scoring engine used by the scan."""

from onecool_os.market.us_breakout_scan import (
    CANSLIM_PASS, MINERVINI_PASS, PORTFOLIO_SYMBOLS, PRICE_BASIS, SCORE_VERSION,
    score_security,
)


def build_portfolio_score_payload(histories, *, expected_as_of, fundamentals=None):
    """Never substitute hand-assigned baselines for missing fundamental inputs."""
    fundamentals = fundamentals or {}
    spy = histories.get("SPY", [])
    results = [
        score_security(symbol, histories.get(symbol, []), fundamentals.get(symbol),
                       spy, expected_as_of)
        for symbol in PORTFOLIO_SYMBOLS
    ]
    return {
        "schema_version": "2.0", "score_version": SCORE_VERSION,
        "classification": "Onecool proxy scores; not IBD official ratings",
        "expected_as_of": expected_as_of, "price_basis": PRICE_BASIS,
        "data_status": "READY" if all(r["validation_status"] == "PASSED" for r in results) else "PARTIAL",
        "thresholds": {"canslim": CANSLIM_PASS, "minervini": MINERVINI_PASS},
        "fundamentals_policy": "same-run shared inputs; missing or stale inputs are Unknown",
        "results": results,
    }
