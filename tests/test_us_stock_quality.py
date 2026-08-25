from onecool_os.market.us_stock_quality import apply_us_super_growth_quality_gate


GATES = (
    "competitive_advantage",
    "structural_growth_runway",
    "financial_quality",
    "business_risk_and_governance",
    "circle_of_competence",
    "valuation",
)


def evidence(symbol="NVDA", *, valuation="PASS"):
    gates = {
        name: {
            "status": valuation if name == "valuation" else "PASS",
            "as_of": "2026-08-24",
            "rationale": f"Verified {name}",
            "sources": ["company-filing"],
        }
        for name in GATES
    }
    return {"results": [{"symbol": symbol, "gates": gates}]}


def scan(symbol="NVDA", *, breakout=True):
    return {
        "expected_as_of": "2026-08-24",
        "top5": [{
            "symbol": symbol,
            "rank_score": 90,
            "formal_breakout": breakout,
        }],
    }


def test_quality_gate_annotates_but_does_not_reorder_or_rewrite_scan():
    payload = apply_us_super_growth_quality_gate(scan(), evidence())
    item = payload["top5"][0]

    assert item["rank_score"] == 90
    assert item["formal_breakout"] is True
    assert item["super_growth_bucket"] == "A"
    assert item["action_eligibility"] == (
        "REQUIRES_MARKET_CTA_INDIVIDUAL_CTA_AND_PRESSURE_GREEN"
    )


def test_missing_evidence_keeps_new_candidate_in_research_only_bucket_c():
    payload = apply_us_super_growth_quality_gate(scan(), None)

    assert payload["top5"][0]["super_growth_bucket"] == "C"
    assert payload["top5"][0]["action_eligibility"] == (
        "RESEARCH_ONLY_QUALITY_EVIDENCE_INCOMPLETE"
    )


def test_quality_pass_without_breakout_remains_watch_only():
    payload = apply_us_super_growth_quality_gate(
        scan(breakout=False), evidence()
    )

    assert payload["top5"][0]["action_eligibility"] == (
        "WATCH_FOR_TECHNICAL_TRIGGER"
    )


def test_tsla_is_exempt_and_keeps_innovation_option_policy():
    payload = apply_us_super_growth_quality_gate(scan("TSLA"), None)
    item = payload["top5"][0]

    assert item["super_growth_bucket"] == "EXEMPT"
    assert item["action_eligibility"] == "FOLLOW_INNOVATION_OPTION_POLICY_ONLY"
    assert payload["super_growth_quality_gate"]["innovation_option_policy"] == (
        "TSLA_AND_SPCX_EXEMPT"
    )


def test_existing_position_overlap_is_not_reclassified_as_a_new_candidate():
    payload = apply_us_super_growth_quality_gate(scan("XYZ"), None)
    item = payload["top5"][0]

    assert item["super_growth_bucket"] == "EXISTING_POSITION"
    assert item["action_eligibility"] == "FOLLOW_EXISTING_CTA_AND_THESIS_POLICY"
