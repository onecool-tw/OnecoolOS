import json
import subprocess
from datetime import date

from onecool_os.market.fund_intelligence_validation import (
    validate_fund_intelligence,
)


def write(root, relative, payload):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_preflight_passes_complete_finite_current_caches(tmp_path) -> None:
    dashboard = {
        "results": [
            {
                "symbol": symbol,
                "current_price": 100,
                "sma50": 99,
                "sma200": 98,
                "weekly_ma30": 97,
                "weekly_ma50": 96,
            }
            for symbol in (
                "SPY", "QQQ", "RUSSELL_2000", "0050", "VIX", "DXY",
                "US30Y", "BTC",
            )
        ]
    }
    write(tmp_path, "data/market/dashboard/dashboard_latest.json", dashboard)
    for name in ("fund_cta_latest.json", "alpha_latest.json"):
        write(tmp_path, f"data/market/fund_nav/{name}", {"results": [{}] * 7})
    write(
        tmp_path,
        "data/market/fund_nav/peer_ranking_latest.json",
        {"results": [{"fund_code": str(index), "data_quality": "VALID"} for index in range(7)]},
    )
    write(
        tmp_path,
        "data/market/ai_revolution/ai_revolution_latest.json",
        {"companies_official_evidence_valid": 6, "review_required": False},
    )
    write(
        tmp_path,
        "data/market/sector_rotation/rotation_latest.json",
        {"results": [{}] * 11},
    )
    write(
        tmp_path,
        "data/market/stockq_rotation/rotation_latest.json",
        {"passed_markets": [{"market": "新加坡", "twd_returns": {"1w": {"status": "VALID"}, "1m": {"status": "VALID"}}}]},
    )
    write(
        tmp_path,
        "data/market/etf_cta/cta_latest.json",
        {"results": [{"symbol": "WTI", "as_of": "2026-07-31"}]},
    )
    write(
        tmp_path,
        "data/market/fundamental_cycle/fundamental_cycle_latest.json",
        {
            "generated_at": "2026-08-03T00:00:00+00:00",
            "phase": "GROWTH",
            "decision_authority": "CONTEXT_ONLY",
        },
    )

    result = validate_fund_intelligence(tmp_path, today=date(2026, 8, 3))

    assert result["status"] == "PASS"
    assert result["issues"] == []


def test_generated_preflight_caches_are_git_trackable() -> None:
    for path in (
        "data/market/sector_rotation/rotation_latest.json",
        "data/market/fundamental_cycle/fundamental_cycle_latest.json",
        "data/market/fund_intelligence/validation_latest.json",
    ):
        result = subprocess.run(
            ["git", "check-ignore", "-q", path],
            check=False,
        )
        assert result.returncode == 1, f"{path} must be committed by the workflow"
