"""Collect dated valuation inputs; collection is not a fair-value opinion.

Use the scan's adjusted price history, never an intraday quote. SEC annual
GAAP EPS is a separately labelled reference, not forward/normalized earnings.
No collected input can promote an objective research gate to PASS.
"""
from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
from math import isfinite
from urllib.request import Request, urlopen

from onecool_os.market.sec_fundamentals import _series


def fetch_sec_json(url, user_agent):
    """Bound each optional research request so report delivery can proceed."""
    request = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
    with urlopen(request, timeout=12) as response:
        return json.load(response)


def _positive(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and isfinite(value) and value > 0)


def collect_valuation_inputs(scan, histories, evidence, client, registry=None):
    """Attempt every validated Top 5 independently, retaining named failures.

    A previous collection is never treated as a current successful fetch.
    Existing quality opinions and technical results are left untouched.
    """
    result = deepcopy(evidence or {"schema_version": "1.0", "results": []})
    cutoff = date.fromisoformat(scan["expected_as_of"])
    if scan.get("data_status") != "READY" or scan.get("price_basis") != "adjusted_close":
        raise ValueError("VALUATION_SCAN_NOT_READY_OR_WRONG_PRICE_BASIS")
    records = {r["symbol"]: r for r in result.setdefault("results", [])}
    mapping = dict(registry or {})
    candidates = scan.get("top5", [])
    registry_error = None
    if any(r["symbol"] not in mapping for r in candidates):
        try:
            rows = client._fetch("https://www.sec.gov/files/company_tickers.json")
            mapping.update({r["ticker"]: str(r["cik_str"]).zfill(10) for r in rows.values()})
        except Exception as exc:
            registry_error = type(exc).__name__
    for candidate in candidates:
        symbol = candidate["symbol"]
        record = records.get(symbol)
        if record is None:
            record = {"symbol": symbol, "gates": {}}
            result["results"].append(record)
            records[symbol] = record
        pack = {"as_of": cutoff.isoformat(), "status": "PARTIAL", "gaps": [],
                "price_basis": "adjusted_close", "inputs": {}, "sources": [],
                "decision_authority": "REFERENCE_INPUTS_ONLY_NOT_FAIR_VALUE"}
        record["valuation_input_collection"] = pack
        if (candidate.get("validation_status") != "PASSED"
                or candidate.get("technical_confidence", 0) < 90
                or candidate.get("price_as_of") != cutoff.isoformat()):
            pack["gaps"].append("CANDIDATE_TECHNICAL_VALIDATION_FAILED")
            continue
        bars = [b for b in histories.get(symbol, []) if b.trading_date == cutoff]
        if len(bars) != 1 or not _positive(bars[0].adjusted_close) or not bars[0].source:
            pack["gaps"].append("SAME_CUTOFF_ADJUSTED_CLOSE_UNAVAILABLE")
        else:
            bar = bars[0]
            pack["inputs"]["adjusted_close"] = bar.adjusted_close
            pack["price_source"] = {"provider": bar.source, "symbol": symbol,
                                    "as_of": cutoff.isoformat(),
                                    "url": (f"https://finance.yahoo.com/quote/{symbol}/history/"
                                            if "yahoo" in bar.source.lower() else None)}
            # A source URL alone is not evidence: retain the exact used bar hash.
            snapshot = {"date": cutoff.isoformat(), "adjusted_close": bar.adjusted_close,
                        "raw_close": bar.close, "provider": bar.source}
            pack["price_observation"] = snapshot
            pack["price_sha256"] = sha256(json.dumps(snapshot, sort_keys=True, allow_nan=False).encode()).hexdigest()
        cik = mapping.get(symbol)
        if not cik:
            pack["fundamental_fetch_status"] = "REGISTRY_UNAVAILABLE" if registry_error else "TICKER_UNMAPPED"
            pack["gaps"].append(pack["fundamental_fetch_status"])
            continue
        cik = str(cik).zfill(10)
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        pack["sources"].append(url)
        try:
            facts = client.fetch_companyfacts(cik)
            if int(facts["cik"]) != int(cik):
                raise ValueError("CIK_MISMATCH")
            pack["fundamental_fetch_status"] = "FETCHED"
            pack["company_name"] = facts.get("entityName")
            options = _series(facts, "us-gaap", ("EarningsPerShareDiluted",), cutoff, (330, 380))
            rows = [r for _, unit, items in options if unit == "USD/shares" for r in items]
            latest = max(rows, key=lambda r: (r["end"], r["filed"]), default=None)
            if latest is None or (cutoff - date.fromisoformat(latest["end"])).days > 550:
                pack["gaps"].append("RECENT_FILED_ANNUAL_GAAP_DILUTED_EPS_UNAVAILABLE")
            else:
                pack["annual_gaap_eps_evidence"] = deepcopy(latest)
                pack["inputs"]["annual_gaap_diluted_eps"] = latest["val"]
                pack["gaps"].append("COMPANY_SPECIFIC_FORWARD_OR_NORMALIZED_EARNINGS_MODEL_REQUIRED")
            pack["gaps"].append("SOURCE_BACKED_FAIR_VALUE_RANGE_REQUIRED")
        except Exception as exc:
            pack["fundamental_fetch_status"] = "FETCH_FAILED"
            pack["fetch_error_type"] = type(exc).__name__
            pack["gaps"].append("SEC_COMPANYFACTS_FETCH_OR_IDENTITY_VALIDATION_FAILED")
    return result
