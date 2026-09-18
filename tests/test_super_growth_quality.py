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
        if name == "valuation":
            gates[name].update({
                "method": "FORWARD_PE",
                "price_source": "fixture-dated-close",
                "denominator_source": "fixture-filing",
                "fair_range_rationale": "Test fixture only",
                "fair_range_sources": ["fixture-comparables"],
                "price_as_of": "2026-08-24",
                "valid_through": "2026-09-02",
                "inputs": {
                    "price": 150.0 if valuation == "FAIL" else 100.0,
                    "denominator": 5.0,
                    "multiple": 30.0 if valuation == "FAIL" else 20.0,
                    "fair_range": [15.0, 25.0],
                },
            })
    return {"results": [{"expected_as_of": "2026-08-24", "symbol": "2330", "as_of": "2026-08-24", "gates": gates}]}


def test_complete_quality_and_valuation_is_bucket_a():
    result = evaluate_super_growth_candidate(
        {"expected_as_of": "2026-08-24", "symbol": "2330", "industry": "半導體業"}, evidence()
    )
    assert result["super_growth_bucket"] == "A"
    assert result["evidence_coverage"] == "COMPLETE"
    assert result["cyclical_review_required"] is True


def test_quality_pass_but_valuation_fail_is_bucket_b_not_reject():
    result = evaluate_super_growth_candidate(
        {"expected_as_of": "2026-08-24", "symbol": "2330"}, evidence(valuation="FAIL")
    )
    assert result["super_growth_bucket"] == "B"
    assert result["super_growth_reason"] == "VALUATION_ABOVE_DISCIPLINED_RANGE"
    assert result["valuation_posture"] == "ABOVE_DISCIPLINED_RANGE"


def test_hard_quality_failure_is_rejected():
    result = evaluate_super_growth_candidate(
        {"expected_as_of": "2026-08-24", "symbol": "2330"}, evidence(failed_gate="financial_quality")
    )
    assert result["super_growth_bucket"] == "REJECT"


def test_unknown_circle_of_competence_is_pre_trade_overlay_not_bucket_c():
    result = evaluate_super_growth_candidate(
        {"expected_as_of": "2026-08-24", "symbol": "2330"}, evidence(omit_source="circle_of_competence")
    )
    assert result["super_growth_bucket"] == "A"
    assert result["manual_confirmation_required"] == ["circle_of_competence"]
    assert result["circle_of_competence_policy"] == (
        "PRE_TRADE_USER_CONFIRMATION_NOT_DAILY_RESEARCH_BLOCKER"
    )


def test_unsupported_pass_is_downgraded_to_unknown():
    result = evaluate_super_growth_candidate(
        {"expected_as_of": "2026-08-24", "symbol": "2330"}, evidence(omit_source="competitive_advantage")
    )
    assert result["super_growth_bucket"] == "C"
    assert "competitive_advantage" in result["missing_evidence"]
    assert result["quality_gate_status"]["competitive_advantage"]["status"] == "UNKNOWN"


def test_valuation_with_wrong_price_cutoff_is_unknown_with_specific_posture():
    result = evaluate_super_growth_candidate(
        {"expected_as_of": "2026-08-24", "symbol": "2330", "expected_as_of": "2026-08-25"}, evidence()
    )
    assert result["super_growth_bucket"] == "B"
    assert result["super_growth_reason"] == "VALUATION_INPUTS_UNAVAILABLE_OR_STALE"
    assert result["valuation_posture"] == "UNRESOLVED_WITH_SPECIFIC_GAP"
