"""Evidence-gated Super Growth review for public-equity candidates.

This layer deliberately does not create another numerical score.  It turns a
stage-one quantitative candidate into a research bucket only when every claim
is backed by dated source evidence.  Missing evidence remains UNKNOWN.
"""

from __future__ import annotations

from typing import Any, Mapping


GATE_NAMES = (
    "competitive_advantage",
    "structural_growth_runway",
    "financial_quality",
    "business_risk_and_governance",
    "circle_of_competence",
    "valuation",
)
QUALITY_GATES = GATE_NAMES[:-1]
VALID_STATUSES = {"PASS", "FAIL", "UNKNOWN"}

# This flag prompts an explicit cycle review; it is not an automatic rejection.
CYCLICAL_INDUSTRY_TERMS = (
    "半導體",
    "電子通路",
    "鋼鐵",
    "航運",
    "油氣",
    "礦業",
    "塑膠",
    "水泥",
    "造紙",
    "Semiconductor",
    "Energy",
    "Materials",
    "Mining",
    "Oil & Gas",
    "Shipping",
)


def _evidence_index(payload: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    if not payload:
        return {}
    results = payload.get("results", [])
    if not isinstance(results, list):
        return {}
    return {
        str(item.get("symbol")): item
        for item in results
        if isinstance(item, Mapping) and item.get("symbol")
    }


def _verified_gate(record: Mapping[str, Any] | None, gate: str) -> dict[str, Any]:
    gate_map = (record or {}).get("gates") or {}
    if not isinstance(gate_map, Mapping):
        gate_map = {}
    raw = gate_map.get(gate, {})
    if not isinstance(raw, Mapping):
        raw = {}
    status = str(raw.get("status", "UNKNOWN")).upper()
    sources = raw.get("sources", [])
    rationale = raw.get("rationale")
    as_of = raw.get("as_of")
    # PASS/FAIL without a date, rationale and source is an unsupported opinion.
    verified = (
        status in {"PASS", "FAIL"}
        and isinstance(sources, list)
        and bool(sources)
        and bool(rationale)
        and bool(as_of)
    )
    if status not in VALID_STATUSES or not verified:
        status = "UNKNOWN"
    return {
        "status": status,
        "as_of": as_of if verified else None,
        "rationale": rationale if verified else None,
        "sources": list(sources) if verified else [],
    }


def evaluate_super_growth_candidate(
    candidate: Mapping[str, Any],
    evidence_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify one stage-one candidate without inventing missing evidence."""

    symbol = str(candidate.get("symbol", ""))
    record = _evidence_index(evidence_payload).get(symbol)
    gates = {name: _verified_gate(record, name) for name in GATE_NAMES}
    missing = [name for name, gate in gates.items() if gate["status"] == "UNKNOWN"]
    failed_quality = [
        name for name in QUALITY_GATES if gates[name]["status"] == "FAIL"
    ]
    quality_complete = all(gates[name]["status"] == "PASS" for name in QUALITY_GATES)

    if failed_quality:
        bucket = "REJECT"
        reason = "HARD_QUALITY_GATE_FAILED"
    elif not quality_complete:
        bucket = "C"
        reason = "CYCLICAL_OR_UNPROVEN_GROWTH"
    elif gates["valuation"]["status"] == "PASS":
        bucket = "A"
        reason = "SUPER_GROWTH_QUALIFIED"
    else:
        bucket = "B"
        reason = "QUALITY_BUT_VALUATION_GATED"

    industry = str(
        candidate.get("industry")
        or candidate.get("sector")
        or (record or {}).get("industry")
        or (record or {}).get("sector")
        or ""
    )
    cyclical_review = any(term in industry for term in CYCLICAL_INDUSTRY_TERMS)
    known_count = sum(gate["status"] != "UNKNOWN" for gate in gates.values())
    evidence_coverage = (
        "COMPLETE" if known_count == len(GATE_NAMES)
        else "NONE" if known_count == 0
        else "PARTIAL"
    )
    return {
        "super_growth_bucket": bucket,
        "super_growth_reason": reason,
        "quality_gate_status": gates,
        "evidence_coverage": evidence_coverage,
        "missing_evidence": missing,
        "cyclical_review_required": cyclical_review,
        "evidence_as_of": (record or {}).get("as_of"),
        "decision_authority": "RESEARCH_QUALITY_ONLY",
    }


def evaluate_super_growth_candidates(
    candidates: list[Mapping[str, Any]],
    evidence_payload: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [
        evaluate_super_growth_candidate(candidate, evidence_payload)
        for candidate in candidates
    ]
