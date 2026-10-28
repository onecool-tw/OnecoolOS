"""Same-run background observations, isolated from the shared CTA engine."""
from dataclasses import asdict
from datetime import date
from hashlib import sha256
import json

from onecool_os.market.us_breakout_scan import technical_confidence


def build_background_validation(histories, expected_as_of):
    expected = date.fromisoformat(expected_as_of)
    spy = histories.get("SPY", [])
    results = []
    for symbol in ("AMD", "TSM", "NVDA"):
        bars = histories.get(symbol, [])
        confidence, errors = technical_confidence(bars, expected)
        if not spy or [b.trading_date for b in bars[-252:]] != [b.trading_date for b in spy[-252:]]:
            errors = [*errors, "trading calendar differs from SPY"]
        row = {"symbol": symbol, "as_of": bars[-1].trading_date.isoformat() if bars else None,
               "expected_as_of": expected_as_of, "price_basis": "adjusted_close",
               "technical_confidence": confidence, "validation_errors": errors,
               "validation_status": "PASSED" if confidence >= 90 and not errors else "Technical Data Validation Failed"}
        if row["validation_status"] == "PASSED":
            closes = [float(b.adjusted_close) for b in bars]
            row.update(observations=len(bars), adjusted_close=closes[-1],
                       moving_averages={str(n): sum(closes[-n:])/n for n in (20, 50, 150, 200)},
                       volume_average_50d=sum(b.volume for b in bars[-50:])/50,
                       high_52w_adjusted=max(closes[-252:]), low_52w_adjusted=min(closes[-252:]),
                       relative_return_126d_to_SPY=(closes[-1]/closes[-127])/(spy[-1].adjusted_close/spy[-127].adjusted_close)-1,
                       source_url=f"https://finance.yahoo.com/quote/{symbol}/history/",
                       history_sha256=sha256(json.dumps([asdict(b) for b in bars], default=str, sort_keys=True).encode()).hexdigest(),
                       corporate_action_policy="Own security adjusted history only; no ticker splice")
        results.append(row)
    return {"schema_version": "1.1", "expected_as_of": expected_as_of,
            "price_basis": "adjusted_close", "data_status": "READY" if all(r["validation_status"] == "PASSED" for r in results) else "PARTIAL",
            "decision_authority": "BACKGROUND_VALIDATION_ONLY_NO_CTA_OR_RANKING_OVERRIDE", "results": results}
