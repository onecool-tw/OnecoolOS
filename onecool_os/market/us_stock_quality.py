"""Attach the formal Super Growth research gate to US stock candidates."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from onecool_os.market.super_growth_quality import evaluate_super_growth_candidate


INNOVATION_OPTION_EXEMPTIONS = {"TSLA", "SPCX"}
EXISTING_PORTFOLIO_EXEMPTIONS = {"BABA", "XYZ", "QRVO", "RH", "UPBD"}


def apply_us_super_growth_quality_gate(
    scan_payload: Mapping[str, Any],
    evidence_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Enrich a scan without changing its ranking or technical signals."""

    payload = deepcopy(dict(scan_payload))
    top5 = payload.get("top5", [])
    if not isinstance(top5, list):
        top5 = []
    bucket_counts = {
        "A": 0,
        "B": 0,
        "C": 0,
        "REJECT": 0,
        "INNOVATION_OPTION": 0,
        "EXISTING_POSITION": 0,
    }
    enriched = []
    for raw in top5:
        item = deepcopy(raw) if isinstance(raw, Mapping) else {}
        symbol = str(item.get("symbol", ""))
        if symbol in INNOVATION_OPTION_EXEMPTIONS:
            item.update({
                "super_growth_bucket": "EXEMPT",
                "super_growth_reason": "INNOVATION_OPTION_SPECIAL_POLICY",
                "quality_gate_application": "NOT_APPLICABLE",
                "action_eligibility": "FOLLOW_INNOVATION_OPTION_POLICY_ONLY",
            })
            bucket_counts["INNOVATION_OPTION"] += 1
        elif symbol in EXISTING_PORTFOLIO_EXEMPTIONS:
            item.update({
                "super_growth_bucket": "EXISTING_POSITION",
                "super_growth_reason": "EXISTING_PORTFOLIO_POLICY_PREVAILS",
                "quality_gate_application": "NOT_APPLICABLE",
                "action_eligibility": "FOLLOW_EXISTING_CTA_AND_THESIS_POLICY",
            })
            bucket_counts["EXISTING_POSITION"] += 1
        else:
            quality = evaluate_super_growth_candidate(item, evidence_payload)
            item.update(quality)
            item["quality_gate_application"] = "FORMAL_NEW_CANDIDATE_RESEARCH_GATE"
            bucket = quality["super_growth_bucket"]
            bucket_counts[bucket] += 1
            if bucket == "A" and item.get("formal_breakout") is True:
                item["action_eligibility"] = (
                    "REQUIRES_MARKET_CTA_INDIVIDUAL_CTA_AND_PRESSURE_GREEN"
                )
            elif bucket == "A":
                item["action_eligibility"] = "WATCH_FOR_TECHNICAL_TRIGGER"
            elif bucket == "B":
                item["action_eligibility"] = "RESEARCH_ONLY_VALUATION_GATED"
            elif bucket == "C":
                item["action_eligibility"] = (
                    "RESEARCH_ONLY_QUALITY_EVIDENCE_INCOMPLETE"
                )
            else:
                item["action_eligibility"] = "REJECTED_BY_QUALITY_GATE"
        enriched.append(item)
    payload["top5"] = enriched
    payload["super_growth_quality_gate"] = {
        "framework": "LIN_TZU_YANG_QUALITY_PLUS_ONECOOL_CTA_TIMING",
        "scope": "NEW_US_STOCK_CANDIDATES_ONLY",
        "bucket_counts": bucket_counts,
        "ranking_policy": "ANNOTATE_ONLY; NEVER_REORDER_TECHNICAL_SCAN",
        "missing_evidence_policy": "UNKNOWN_NEVER_INFERRED",
        "existing_position_policy": "NO_AUTOMATIC_EXIT_OR_DOWNGRADE",
        "innovation_option_policy": "TSLA_AND_SPCX_EXEMPT",
        "canslim_role": "CONCEPTUAL_CROSSWALK_ONLY_NOT_AN_EXTRA_SCORE",
    }
    return payload
