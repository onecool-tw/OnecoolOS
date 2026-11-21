"""Backfill reviewed COST quality and valuation evidence for 2026-11-20.

The live SEC Company Facts request failed, but Costco's filed FY2026 10-K and
issuer earnings release were already public before the price cutoff.  This
repair installs the official-source fallback used by future daily runs and
rebuilds the same-date evidence without changing CTA or technical scores.
"""

from __future__ import annotations

import json
from pathlib import Path

from onecool_os.market.us_stock_quality import apply_us_super_growth_quality_gate
from onecool_os.market.us_valuation_inputs import scenario_multiple


ROOT = Path(__file__).resolve().parents[1]
INTEL = ROOT / "data/market/us_stock_intelligence"
OFFICIAL_RELEASE = (
    "https://investor.costco.com/news/news-details/2026/"
    "Costco-Wholesale-Corporation-Reports-Fourth-Quarter-and-Fiscal-Year-2026-Operating-Results/"
)
SEC_10K = "https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/cost-20260830.htm"
POLICY = "https://github.com/onecool-tw/OnecoolOS/blob/main/docs/operations/us-valuation-inputs.md"


def write(path: Path, payload: dict) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    path.write_text(text, encoding="utf-8")
    if json.loads(path.read_text(encoding="utf-8")) != payload:
        raise RuntimeError(f"readback mismatch: {path}")


def main() -> None:
    registry_path = INTEL / "reviewed_valuation_inputs.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    conservative = {
        "name": "conservative", "years": 5, "growth": 0.07,
        "required_return": 0.12, "terminal_growth": 0.02,
        "cash_conversion": 0.70, "terminal_cash_conversion": 0.85,
    }
    base = {
        "name": "base", "years": 5, "growth": 0.11,
        "required_return": 0.10, "terminal_growth": 0.03,
        "cash_conversion": 0.85, "terminal_cash_conversion": 0.90,
    }
    fair_range = [scenario_multiple(conservative), scenario_multiple(base)]
    registry["reviewed_at"] = "2026-11-21T04:05:00+00:00"
    registry["results"]["COST"] = {
        "symbol": "COST",
        "company_name": "Costco Wholesale Corporation",
        "published_at": "2026-10-07",
        "reviewed_as_of": "2026-11-21",
        "valid_through": "2027-01-05",
        "sources": [OFFICIAL_RELEASE, SEC_10K, POLICY],
        "reported_facts": {
            "period": "FY2026",
            "revenue_million": 303154,
            "net_sales_million": 297247,
            "membership_fees_million": 5907,
            "net_income_million": 9226,
            "reported_diluted_eps": 20.76,
            "tariff_refund_benefit_eps": 0.15,
            "normalized_diluted_eps": 20.61,
            "warehouses": 939,
        },
        "model_gaps": [],
        "refresh_on": [
            "NEW_EARNINGS_OR_GUIDANCE", "MATERIAL_CORPORATE_EVENT",
            "REFERENCE_EXPIRY",
        ],
        "valuation_model": {
            "method": "FY26_NORMALIZED_GAAP_DILUTED_PE_WITH_CASH_CONVERSION_STRESS",
            "denominator": 20.61,
            "currency": "USD",
            "share_basis": "listed_security",
            "normalization_bridge": {
                "formula": "FY2026 reported diluted EPS 20.76 less disclosed non-recurring tariff-refund benefit 0.15",
                "inputs": [20.76, -0.15],
                "limitations": "Historical normalized EPS, not issuer FY2027 guidance; the tariff adjustment is the only disclosed non-recurring EPS item removed.",
            },
            "denominator_source": [OFFICIAL_RELEASE, SEC_10K],
            "fair_range": fair_range,
            "scenarios": [conservative, base],
            "assumption_authority": "ONECOOL_ANALYST_NOT_ISSUER_GUIDANCE",
            "research_grade": "SCREENING_SCENARIO_NOT_FULL_DCF",
            "policy_version": "onecool_equity_two_stage_screen_v1",
            "rationale": "Membership renewal economics, warehouse expansion and recurring fee income support durable growth; retail margin sensitivity, wage and merchandise costs, international execution and reinvestment justify 7%/11% growth and stressed cash conversion scenarios.",
            "fair_range_rationale": "Five-year 7%/11% growth, 70%/85% interim cash conversion, 85%/90% terminal conversion, 12%/10% required return and 2%/3% terminal growth are Onecool screening assumptions selected without reference to the current share price.",
            "fair_range_sources": [OFFICIAL_RELEASE, SEC_10K, POLICY],
        },
        "source_review": {
            "status": "VERIFIED_CURRENT_OFFICIAL",
            "checked_at": "2026-11-21T04:05:00+00:00",
            "information_cutoff": "2026-11-20",
            "conclusion": "FY2026 10-K and issuer results replace the failed live Company Facts request and provide a current reproducible denominator.",
        },
    }
    write(registry_path, registry)

    evidence_path = INTEL / "super_growth_evidence_latest.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    record = next(x for x in evidence["results"] if x.get("symbol") == "COST")
    sources = [OFFICIAL_RELEASE, SEC_10K]
    record.update({
        "company_name": "Costco Wholesale Corporation",
        "sector": "Consumer Defensive",
        "industry": "Discount Stores",
        "as_of": "2026-11-20",
    })
    record["gates"].update({
        "competitive_advantage": {
            "status": "PASS", "as_of": "2026-10-07",
            "rationale": "Membership-fee economics, purchasing scale and a 939-warehouse network support recurring traffic, customer retention and price leadership.",
            "sources": sources,
        },
        "structural_growth_runway": {
            "status": "PASS", "as_of": "2026-10-07",
            "rationale": "FY2026 net sales rose 10.1%, membership fees rose 11.0%, digitally enabled sales rose 20.9%, and the warehouse base expanded to 939, supporting a source-backed growth runway.",
            "sources": sources,
        },
        "financial_quality": {
            "status": "PASS", "as_of": "2026-10-07",
            "rationale": "FY2026 revenue was $303.154 billion, net income $9.226 billion and diluted EPS $20.76; the 10-K received an unqualified audit opinion and reported effective internal control.",
            "sources": sources,
        },
        "business_risk_and_governance": {
            "status": "PASS", "as_of": "2026-10-07",
            "rationale": "The 10-K identifies merchandise, wage, supply-chain, cybersecurity, international and regulatory risks; the audit and internal-control opinions disclose no current issue that invalidates research eligibility.",
            "sources": [SEC_10K],
        },
        "circle_of_competence": {
            "status": "UNKNOWN", "as_of": "2026-11-20",
            "rationale": "Understanding membership economics, retail margins and international execution remains a user confirmation before a new position and does not block ranking.",
            "sources": sources,
            "data_gap": "PRE_TRADE_USER_CONFIRMATION_ONLY",
        },
    })
    price = 1102.1500244140625
    multiple = price / 20.61
    model = registry["results"]["COST"]["valuation_model"]
    record["gates"]["valuation"] = {
        "status": "FAIL", "as_of": "2026-11-20",
        "price_as_of": "2026-11-20", "valid_through": "2026-11-20",
        "method": model["method"], "rationale": model["rationale"],
        "sources": registry["results"]["COST"]["sources"],
        "price_source": {
            "provider": "yahoo_finance_adjusted_batch", "symbol": "COST",
            "as_of": "2026-11-20", "url": "https://finance.yahoo.com/quote/COST/history/",
        },
        "denominator_source": model["denominator_source"],
        "fair_range_rationale": model["fair_range_rationale"],
        "fair_range_sources": model["fair_range_sources"],
        "normalization_bridge": model["normalization_bridge"],
        "policy_version": model["policy_version"],
        "assumption_authority": model["assumption_authority"],
        "scenarios": model["scenarios"],
        "research_grade": model["research_grade"],
        "inputs": {"price": price, "denominator": 20.61,
                   "multiple": multiple, "fair_range": fair_range},
    }
    record["valuation_input_collection"] = {
        "as_of": "2026-11-20", "status": "COMPLETE", "gaps": [],
        "price_basis": "adjusted_close", "inputs": {"adjusted_close": price},
        "sources": registry["results"]["COST"]["sources"],
        "decision_authority": "REVIEWED_SOURCE_BACKED_VALUATION_MODEL",
        "price_source": record["gates"]["valuation"]["price_source"],
        "price_observation": {"date": "2026-11-20", "adjusted_close": price,
                              "raw_close": price, "provider": "yahoo_finance_adjusted_batch"},
        "official_reference_status": "VERIFIED",
        "fundamental_fetch_status": "REVIEWED_OFFICIAL_REFERENCE",
        "company_name": "Costco Wholesale Corporation",
        "official_reference": registry["results"]["COST"],
    }
    evidence["generated_at"] = "2026-11-21T04:05:00+00:00"
    evidence["valuation_models_reviewed_at"] = registry["reviewed_at"]
    write(evidence_path, evidence)

    scan_path = INTEL / "breakout_scan_latest.json"
    scan = json.loads(scan_path.read_text(encoding="utf-8"))
    enriched = apply_us_super_growth_quality_gate(scan, evidence)
    write(scan_path, enriched)
    dashboard_path = ROOT / "data/market/dashboard/dashboard_latest.json"
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    dashboard["daily_top5_scan"] = enriched
    write(dashboard_path, dashboard)


if __name__ == "__main__":
    main()
