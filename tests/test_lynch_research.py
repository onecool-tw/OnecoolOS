from copy import deepcopy

import pytest

from onecool_os.market.lynch_research import build_lynch_research


def test_taiwan_growth_and_cycle_are_provisional_without_changing_candidate():
    candidate = {
        "symbol": "3006", "industry": "半導體業",
        "monthly_revenue_yoy": 35.0, "cumulative_revenue_yoy": 25.0,
        "eps": 4.2, "pe": 18.0, "pb": 3.0,
        "monthly_revenue_as_of": "2026-08", "fundamentals_as_of": "2026Q2",
        "price_as_of": "2026-09-17", "score": 92,
    }
    before = deepcopy(candidate)

    result = build_lynch_research(candidate, market="TW")

    assert candidate == before
    assert result["company_type"]["status"] == "PROVISIONAL"
    assert result["company_type"]["primary"] == "MULTIPLE_CANDIDATES"
    assert result["company_type"]["candidates"] == ["FAST_GROWER", "CYCLICAL"]
    assert result["policy"]["ranking_effect"] == "NONE"
    assert result["policy"]["cta_effect"] == "NONE"
    assert result["policy"]["action_effect"] == "NONE"


def test_taiwan_single_snapshot_does_not_infer_unsupported_company_types():
    result = build_lynch_research(
        {"symbol": "1234", "monthly_revenue_yoy": 4, "eps": 2}, market="TW"
    )

    assert result["company_type"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["company_type"]["primary"] == "UNCLASSIFIED"
    assert result["company_type"]["candidates"] == []
    assert "TURNAROUND" in result["company_type"]["unresolved_categories"]
    assert "ASSET_PLAY" in result["company_type"]["unresolved_categories"]


def test_us_fast_growth_requires_verified_growth_and_quality_gates():
    gates = {
        name: {
            "status": "PASS", "as_of": "2026-09-16",
            "rationale": f"Verified {name}", "sources": ["filing"],
        }
        for name in (
            "competitive_advantage", "structural_growth_runway", "financial_quality",
            "business_risk_and_governance", "circle_of_competence", "valuation",
        )
    }
    result = build_lynch_research(
        {"symbol": "NVDA", "quality_gate_status": gates}, market="US"
    )

    assert result["company_type"]["primary"] == "FAST_GROWER"
    assert len(result["investment_story"]["evidence"]) == 6
    assert all(item["sources"] == ["filing"] for item in result["investment_story"]["evidence"])


def test_us_scores_and_popularity_cannot_create_a_company_type():
    result = build_lynch_research(
        {"symbol": "HOT", "canslim_score": 99, "minervini_score": 99},
        market="US",
    )

    assert result["company_type"]["primary"] == "UNCLASSIFIED"
    assert result["investment_story"]["status"] == "INSUFFICIENT_EVIDENCE"


def test_invalid_market_is_rejected():
    with pytest.raises(ValueError, match="TW or US"):
        build_lynch_research({}, market="JP")
