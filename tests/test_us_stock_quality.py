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
    gates["valuation"].update({
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
    assert item["lynch_research"]["company_type"]["primary"] == "FAST_GROWER"
    assert item["lynch_research"]["policy"]["ranking_effect"] == "NONE"
    assert payload["lynch_research_layer"]["action_policy"] == (
        "NO_CTA_OR_ACTION_AUTHORITY"
    )


def test_missing_evidence_keeps_new_candidate_in_research_only_bucket_c():
    payload = apply_us_super_growth_quality_gate(scan(), None)

    assert payload["top5"][0]["super_growth_bucket"] == "C"
    assert payload["top5"][0]["action_eligibility"] == (
        "RESEARCH_ONLY_QUALITY_EVIDENCE_INCOMPLETE"
    )
    assert payload["top5"][0]["lynch_research"]["company_type"]["primary"] == (
        "UNCLASSIFIED"
    )


def test_formal_breakout_with_unknown_circle_requires_only_pre_trade_confirmation():
    payload = apply_us_super_growth_quality_gate(
        scan(), evidence()
    )
    # Remove only the personal ability-circle support; objective research stays complete.
    payload_with_unknown_circle = apply_us_super_growth_quality_gate(
        scan(),
        {
            "results": [{
                **evidence()["results"][0],
                "gates": {
                    **evidence()["results"][0]["gates"],
                    "circle_of_competence": {
                        "status": "UNKNOWN",
                        "as_of": None,
                        "rationale": None,
                        "sources": [],
                    },
                },
            }],
        },
    )
    item = payload_with_unknown_circle["top5"][0]
    assert item["super_growth_bucket"] == "A"
    assert item["action_eligibility"] == (
        "REQUIRES_CIRCLE_OF_COMPETENCE_CONFIRMATION_AND_MARKET_GATES"
    )


def test_quality_pass_without_breakout_remains_watch_only():
    payload = apply_us_super_growth_quality_gate(
        scan(breakout=False), evidence()
    )

    assert payload["top5"][0]["action_eligibility"] == (
        "WATCH_FOR_TECHNICAL_TRIGGER"
    )


def test_quality_pass_but_expensive_valuation_names_the_action():
    payload = apply_us_super_growth_quality_gate(
        scan(), evidence(valuation="FAIL")
    )
    item = payload["top5"][0]
    assert item["valuation_posture"] == "ABOVE_DISCIPLINED_RANGE"
    assert item["action_eligibility"] == "RESEARCH_ONLY_VALUATION_TOO_HIGH"


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


def test_stale_valuation_is_rejected_using_scan_cutoff():
    data = scan()
    data['expected_as_of'] = '2026-08-25'
    result = apply_us_super_growth_quality_gate(data, evidence())['top5'][0]
    assert result['quality_gate_status']['valuation']['status'] == 'UNKNOWN'
    assert 'PRICE_CUTOFF_MISMATCH' in result['quality_gate_status']['valuation']['data_gap']


def test_invalid_numbers_and_unbacked_ranges_never_pass():
    cases = [('price', 0), ('denominator', 0), ('multiple', float('nan')),
             ('fair_range', [25, 15]), ('price', True), ('denominator', '5'),
             ('multiple', 200)]
    for key, value in cases:
        data = evidence()
        data['results'][0]['gates']['valuation']['inputs'][key] = value
        gate = apply_us_super_growth_quality_gate(scan(), data)['top5'][0]['quality_gate_status']['valuation']
        assert gate['status'] == 'UNKNOWN', (key, value)
        assert gate['data_gap']
    data = evidence()
    del data['results'][0]['gates']['valuation']['fair_range_sources']
    result = apply_us_super_growth_quality_gate(scan(), data)['top5'][0]
    assert result['quality_gate_status']['valuation']['status'] == 'UNKNOWN'


def test_unknown_reason_is_preserved():
    data = evidence(valuation='UNKNOWN')
    data['results'][0]['gates']['valuation']['data_gap'] = 'DATED_CLOSE_NOT_VERIFIED'
    result = apply_us_super_growth_quality_gate(scan(), data)['top5'][0]
    assert result['quality_gate_status']['valuation']['data_gap'] == 'DATED_CLOSE_NOT_VERIFIED'
