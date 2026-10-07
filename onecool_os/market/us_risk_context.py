"""Dated US risk observations; no CTA calculation or aggregate score."""
from datetime import date
from hashlib import sha256
import json
from math import isfinite
from onecool_os.market.etf_cta import merge_and_adjust

RISK_SYMBOLS = {"VIX": "^VIX", "DXY": "DX-Y.NYB", "US10Y": "^TNX",
                "US30Y": "^TYX", "SOX": "^SOX"}


def collect_us_risk_context(expected_as_of, histories, bootstrapper):
    cutoff = date.fromisoformat(expected_as_of)
    rows = []
    for symbol, provider_symbol in RISK_SYMBOLS.items():
        row = {"symbol": symbol, "provider_symbol": provider_symbol,
               "expected_as_of": expected_as_of, "as_of": None,
               "data_status": "UNKNOWN", "value": None,
               "unit": "percent" if symbol in {"US10Y", "US30Y"} else "index_points",
               "price_basis": "adjusted_close", "decision_authority": "SHORT_TERM_CONTEXT_ONLY"}
        try:
            bars = histories.get(symbol)
            if bars is None:
                # One bounded provider request; no workflow-length retry loop.
                bars = merge_and_adjust([], bootstrapper.fetch_raw_daily(provider_symbol, period="10d"))
            observed = [b for b in bars if b.trading_date == cutoff]
            if len(observed) != 1:
                raise ValueError("SAME_CUTOFF_CLOSE_MISSING_OR_DUPLICATE")
            bar = observed[0]
            values = [bar.open, bar.high, bar.low, bar.close, bar.adjusted_close]
            if (not bar.source or any(not isfinite(v) or v <= 0 for v in values)
                    or bar.low > min(bar.open, bar.close)
                    or bar.high < max(bar.open, bar.close)):
                raise ValueError("RISK_OHLC_OR_SOURCE_INVALID")
            snapshot = {"as_of": expected_as_of, "value": bar.adjusted_close,
                        "source": bar.source, "provider_symbol": provider_symbol}
            row.update(as_of=expected_as_of, data_status="READY", value=bar.adjusted_close,
                       source=bar.source,
                       source_url=f"https://finance.yahoo.com/quote/{provider_symbol}/history/",
                       observation_sha256=sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest())
        except Exception as exc:
            row.update(error_type=type(exc).__name__, data_gap=str(exc)[:200])
        rows.append(row)
    return {"schema_version": "1.0", "expected_as_of": expected_as_of,
            "price_basis": "adjusted_close",
            "data_status": "READY" if all(r["data_status"] == "READY" for r in rows) else "PARTIAL",
            "decision_authority": "SHORT_TERM_CONTEXT_ONLY_NO_CTA_OVERRIDE",
            "results": rows}
