"""Collect dated valuation inputs; collection is not a fair-value opinion.

Use the scan's adjusted price history, never an intraday quote. SEC annual
GAAP EPS is a separately labelled reference, not forward/normalized earnings.
Reference facts alone cannot promote an objective research gate to PASS.
An optional complete reviewed model is checked by the existing quality engine.
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


def scenario_multiple(scenario):
    """Two-stage equity cash-flow multiple; inputs are analyst assumptions.

    Cash conversion is FCFE/earnings for EPS, or 1 for owner cash flow.
    No market price is used to select the assumptions.
    """
    g, r, terminal = (scenario[k] for k in
                      ("growth", "required_return", "terminal_growth"))
    cash, terminal_cash = (scenario[k] for k in
                           ("cash_conversion", "terminal_cash_conversion"))
    years = scenario["years"]
    values = (g, r, terminal, cash, terminal_cash)
    if (any(isinstance(v, bool) or not isinstance(v, (int, float))
            or not isfinite(v) for v in values)
            or isinstance(years, bool) or not isinstance(years, int)
            or not 1 <= years <= 10 or not 0 <= g <= .5
            or not 0 <= terminal < r <= .3
            or not 0 < cash <= 1 or not 0 < terminal_cash <= 1):
        raise ValueError("VALUATION_SCENARIO_INVALID")
    interim = sum(cash * (1 + g)**t / (1 + r)**t
                  for t in range(1, years + 1))
    return interim + terminal_cash * (1 + g)**years * (1 + terminal) / (
        (r - terminal) * (1 + r)**years)


def collect_valuation_inputs(scan, histories, evidence, client, registry=None, reviewed=None):
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
        # Invalidate an old opinion before any early return. A stale PASS must
        # never survive missing current-session prices or an invalid candidate.
        if reviewed is not None:
            record.setdefault("gates", {})["valuation"] = {
                "status": "UNKNOWN", "as_of": cutoff.isoformat(),
                "rationale": "Current-session valuation model not yet validated.",
                "sources": [],
            }
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
        official = (reviewed or {}).get("results", {}).get(symbol)
        if official is not None:
            _collect_reviewed(official, candidate, pack, record, cutoff)
            # A reviewed official snapshot is an independent source, not a
            # successful SEC response. Do not spend another 12s retrying SEC.
            if pack.get("official_reference_status") == "VERIFIED":
                continue
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


def _collect_reviewed(official, candidate, pack, record, cutoff):
    """Use dated issuer facts; only a fully sourced model can form an opinion.

    EPS guidance/quarterly EPS alone cannot establish a fair P/E range. Reviewed
    models must preserve currency, security/share basis, normalization bridge,
    source dates and policy assumptions. Technical results remain unchanged.
    """
    try:
        published = date.fromisoformat(official["published_at"])
        expiry = date.fromisoformat(official["valid_through"])
        if not published < cutoff <= expiry:
            raise ValueError("OFFICIAL_REFERENCE_EXPIRED_OR_NOT_POINT_IN_TIME")
        if official.get("symbol") != candidate["symbol"] or not official.get("company_name"):
            raise ValueError("OFFICIAL_REFERENCE_SECURITY_MAPPING_FAILED")
        sources = official.get("sources", [])
        if not sources or not official.get("reported_facts"):
            raise ValueError("OFFICIAL_REFERENCE_EVIDENCE_MISSING")
        if not all(isinstance(s, str) and s.startswith("https://") for s in sources):
            raise ValueError("OFFICIAL_REFERENCE_SOURCE_INVALID")
        pack["official_reference_status"] = "VERIFIED"
        pack["fundamental_fetch_status"] = "REVIEWED_OFFICIAL_REFERENCE"
        pack["company_name"] = official["company_name"]
        pack["official_reference"] = deepcopy(official)
        pack["sources"].extend(sources)
        pack["gaps"].extend(official.get("model_gaps", []))
        model = official.get("valuation_model")
        if not model:
            if not pack["gaps"]:
                pack["gaps"].append("SOURCE_BACKED_VALUATION_MODEL_UNAVAILABLE")
            record["gates"]["valuation"].update(
                rationale="; ".join(pack["gaps"]), data_gap="; ".join(pack["gaps"]),
                price_as_of=cutoff.isoformat(), inputs={"price": pack["inputs"].get("adjusted_close")},
                price_source=deepcopy(pack.get("price_source")), sources=sources)
            return
        required = ("method", "rationale", "normalization_bridge", "denominator_source",
                    "fair_range_rationale", "fair_range_sources", "policy_version")
        if not all(model.get(key) for key in required):
            raise ValueError("REVIEWED_VALUATION_MODEL_EVIDENCE_INCOMPLETE")
        if (model.get("currency") != "USD" or model.get("share_basis") != "listed_security"
                or not _positive(model.get("denominator"))):
            raise ValueError("REVIEWED_VALUATION_MODEL_UNIT_OR_DENOMINATOR_INVALID")
        limits = model.get("fair_range")
        if model.get("scenarios"):
            if model.get("assumption_authority") != "ONECOOL_ANALYST_NOT_ISSUER_GUIDANCE":
                raise ValueError("VALUATION_ASSUMPTION_AUTHORITY_MISSING")
            recomputed = [scenario_multiple(s) for s in model["scenarios"]]
            if len(recomputed) != 2 or any(abs(a-b) > 1e-8 for a,b in zip(recomputed, limits or [])) or len(limits or []) != 2:
                raise ValueError("VALUATION_SCENARIO_RANGE_MISMATCH")
        if (not isinstance(limits, list) or len(limits) != 2
                or not all(_positive(v) for v in limits) or limits[0] > limits[1]):
            raise ValueError("REVIEWED_VALUATION_MODEL_RANGE_INVALID")
        if pack["gaps"]:
            return
        price = pack["inputs"].get("adjusted_close")
        if not _positive(price):
            return
        multiple = price / model["denominator"]
        gate = {"status": "FAIL" if multiple > limits[1] else "PASS",
                "as_of": cutoff.isoformat(), "price_as_of": cutoff.isoformat(),
                # Price is recalculated each run. Never carry a valuation to
                # another session; the earnings reference has separate expiry.
                "valid_through": cutoff.isoformat(), "method": model["method"],
                "rationale": model["rationale"], "sources": sources,
                "price_source": deepcopy(pack["price_source"]),
                "denominator_source": model["denominator_source"],
                "fair_range_rationale": model["fair_range_rationale"],
                "fair_range_sources": model["fair_range_sources"],
                "normalization_bridge": model["normalization_bridge"],
                "policy_version": model["policy_version"],
                "assumption_authority": model.get("assumption_authority"),
                "scenarios": deepcopy(model.get("scenarios", [])),
                "research_grade": model.get("research_grade", "REVIEWED_MODEL"),
                "inputs": {"price": price, "denominator": model["denominator"],
                           "multiple": multiple, "fair_range": limits}}
        # Reuse the existing quality engine's validation; do not create a
        # second, weaker gate evaluator.
        from onecool_os.market.super_growth_quality import _verified_gate
        verified = _verified_gate({"gates": {"valuation": gate}}, "valuation", candidate_as_of=cutoff.isoformat())
        if verified["status"] != gate["status"]:
            raise ValueError("REVIEWED_VALUATION_MODEL_GATE_VALIDATION_FAILED")
        record["gates"]["valuation"] = gate
        pack["status"] = "COMPLETE"
        pack["decision_authority"] = "REVIEWED_SOURCE_BACKED_VALUATION_MODEL"
    except (KeyError, TypeError, ValueError) as exc:
        pack["official_reference_status"] = "REJECTED"
        pack["gaps"].append(str(exc))
