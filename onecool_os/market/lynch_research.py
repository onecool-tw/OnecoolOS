"""Evidence-only Peter Lynch research notes for stock candidates.

This layer helps a reader classify and explain a company.  It has no scoring,
ranking, CTA, or action authority.  A category remains provisional because a
single point-in-time cache cannot establish a durable company type.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


VERSION = "onecool_lynch_research_v1"
LYNCH_CATEGORIES = (
    "SLOW_GROWER",
    "STALWART",
    "FAST_GROWER",
    "CYCLICAL",
    "TURNAROUND",
    "ASSET_PLAY",
)
CYCLICAL_TERMS = (
    "半導體", "鋼鐵", "航運", "油氣", "礦業", "塑膠", "水泥", "造紙",
    "Semiconductor", "Energy", "Materials", "Mining", "Oil & Gas", "Shipping",
)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _gate(item: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    gates = item.get("quality_gate_status")
    if not isinstance(gates, Mapping):
        return {}
    value = gates.get(name)
    return value if isinstance(value, Mapping) else {}


def build_lynch_research(
    candidate: Mapping[str, Any], *, market: str
) -> dict[str, Any]:
    """Create an evidence-only annotation without changing the candidate."""

    if market not in {"TW", "US"}:
        raise ValueError("market must be TW or US")
    item = deepcopy(dict(candidate))
    categories: list[str] = []
    category_evidence: list[dict[str, Any]] = []
    story_evidence: list[dict[str, Any]] = []
    break_conditions: list[dict[str, str]] = []

    industry = str(item.get("industry") or item.get("sector") or "")
    cyclical = bool(item.get("cyclical_review_required")) or any(
        term in industry for term in CYCLICAL_TERMS
    )
    if cyclical:
        categories.append("CYCLICAL")
        category_evidence.append({
            "field": "industry", "value": industry or "verified cyclical flag",
            "interpretation": "CYCLE_REVIEW_REQUIRED",
        })

    if market == "TW":
        monthly = _number(item.get("monthly_revenue_yoy"))
        cumulative = _number(item.get("cumulative_revenue_yoy"))
        eps = _number(item.get("eps"))
        if monthly is not None:
            story_evidence.append({
                "field": "monthly_revenue_yoy", "value": monthly,
                "as_of": item.get("monthly_revenue_as_of"),
            })
        if cumulative is not None:
            story_evidence.append({
                "field": "cumulative_revenue_yoy", "value": cumulative,
                "as_of": item.get("monthly_revenue_as_of"),
            })
        if eps is not None:
            story_evidence.append({
                "field": "eps", "value": eps,
                "as_of": item.get("fundamentals_as_of"),
            })
        for field in ("pe", "pb"):
            value = _number(item.get(field))
            if value is not None:
                story_evidence.append({
                    "field": field, "value": value,
                    "as_of": item.get("price_as_of"),
                })
        if (
            monthly is not None and monthly >= 20
            and cumulative is not None and cumulative >= 20
            and eps is not None and eps > 0
        ):
            categories.append("FAST_GROWER")
            category_evidence.append({
                "field": "revenue_and_eps_snapshot",
                "value": {
                    "monthly_revenue_yoy": monthly,
                    "cumulative_revenue_yoy": cumulative,
                    "eps": eps,
                },
                "interpretation": "FAST_GROWTH_CANDIDATE_NOT_DURABILITY_PROOF",
            })
        break_conditions.extend([
            {
                "condition": "CUMULATIVE_REVENUE_YOY_NONPOSITIVE",
                "meaning": "Growth story requires fundamental review",
            },
            {
                "condition": "EPS_NONPOSITIVE",
                "meaning": "Profitability story requires fundamental review",
            },
            {
                "condition": "FINANCIAL_QUALITY_EVIDENCE_DETERIORATES",
                "meaning": "Cash flow, leverage, inventory or receivables require review",
            },
        ])
    else:
        growth = _gate(item, "structural_growth_runway")
        quality = _gate(item, "financial_quality")
        if growth.get("status") == "PASS" and quality.get("status") == "PASS":
            categories.append("FAST_GROWER")
            category_evidence.append({
                "field": "verified_quality_gates",
                "value": ["structural_growth_runway", "financial_quality"],
                "interpretation": "FAST_GROWTH_CANDIDATE_NOT_DURABILITY_PROOF",
            })
        for name in (
            "competitive_advantage", "structural_growth_runway", "financial_quality",
            "business_risk_and_governance", "circle_of_competence", "valuation",
        ):
            gate = _gate(item, name)
            if gate.get("status") in {"PASS", "FAIL"}:
                story_evidence.append({
                    "field": name, "value": gate.get("status"),
                    "as_of": gate.get("as_of"), "rationale": gate.get("rationale"),
                    "sources": list(gate.get("sources") or []),
                })
        break_conditions.extend([
            {
                "condition": "VERIFIED_COMPETITIVE_ADVANTAGE_FAILS",
                "meaning": "Investment story requires review",
            },
            {
                "condition": "VERIFIED_STRUCTURAL_GROWTH_RUNWAY_FAILS",
                "meaning": "Growth story requires review",
            },
            {
                "condition": "VERIFIED_FINANCIAL_QUALITY_OR_GOVERNANCE_FAILS",
                "meaning": "Quality story requires review",
            },
        ])

    categories = [name for name in LYNCH_CATEGORIES if name in set(categories)]
    return {
        "version": VERSION,
        "company_type": {
            "status": "PROVISIONAL" if categories else "INSUFFICIENT_EVIDENCE",
            "primary": categories[0] if len(categories) == 1 else (
                "MULTIPLE_CANDIDATES" if categories else "UNCLASSIFIED"
            ),
            "candidates": categories,
            "evidence": category_evidence,
            "unresolved_categories": [
                name for name in LYNCH_CATEGORIES if name not in categories
            ],
        },
        "investment_story": {
            "status": "EVIDENCE_ONLY" if story_evidence else "INSUFFICIENT_EVIDENCE",
            "evidence": story_evidence,
            "required_manual_confirmation": [
                "BUSINESS_DRIVER", "DURABILITY", "MANAGEMENT_EXECUTION",
            ],
        },
        "story_break_conditions": break_conditions,
        "policy": {
            "decision_authority": "NONE",
            "ranking_effect": "NONE",
            "score_effect": "NONE",
            "cta_effect": "NONE",
            "action_effect": "NONE",
            "observation_is_research_lead_only": True,
            "manual_confirmation_required": True,
        },
    }
