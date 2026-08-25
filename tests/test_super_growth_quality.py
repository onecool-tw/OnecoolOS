from onecool_os.market.super_growth_quality import evaluate_super_growth_candidate


GATES = (
    "competitive_advantage",
    "structural_growth_runway",
    "financial_quality",
    "business_risk_and_governance",
    "circle_of_competence",
    "valuation",
)


def evidence(*, valuation="PASS", failed_gate=None, omit_source=None):
    gates = {}
    for name in GATES:
        status = valuation if name == "valuation" else "PASS"
        if name == failed_gate:
            status = "FAIL"
        gates[name] = {
            "status": status,
            "as_of": "2026-08-24",
            "rationale": f"Evidence for {name}",
            "sources": [] if name == omit_source else ["official-filing"],
        }
    return {"results": [{"symbol": "2330", "as_of": "2026-08-24", "gates": gates}]}


def test_complete_quality_and_valuation_is_bucket_a():
    result = evaluate_super_growth_candidate(
        {"symbol": "2330", "industry": "半導體業"}, evidence()
    )
    assert result["super_growth_bucket"] == "A"
    assert result["evidence_coverage"] == "COMPLETE"
    assert result["cyclical_review_required"] is True


def test_quality_pass_but_valuation_fail_is_bucket_b_not_reject():
    result = evaluate_super_growth_candidate(
        {"symbol": "2330"}, evidence(valuation="FAIL")
    )
    assert result["super_growth_bucket"] == "B"
    assert result["super_growth_reason"] == "QUALITY_BUT_VALUATION_GATED"


def test_hard_quality_failure_is_rejected():
    result = evaluate_super_growth_candidate(
        {"symbol": "2330"}, evidence(failed_gate="financial_quality")
    )
    assert result["super_growth_bucket"] == "REJECT"


def test_unsupported_pass_is_downgraded_to_unknown():
    result = evaluate_super_growth_candidate(
        {"symbol": "2330"}, evidence(omit_source="competitive_advantage")
    )
    assert result["super_growth_bucket"] == "C"
    assert "competitive_advantage" in result["missing_evidence"]
    assert result["quality_gate_status"]["competitive_advantage"]["status"] == "UNKNOWN"
