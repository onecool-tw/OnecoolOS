from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from onecool_os.health.monitor import BLOCKED, PARTIAL, READY, build_health_report


NOW = datetime(2026, 8, 30, 3, 0, tzinfo=timezone.utc)


def _write(root: Path, relative: str, payload: dict) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_ready(root: Path) -> None:
    daily = "2026-08-28"
    taiwan = "2026-08-28"
    generated = "2026-08-30T02:00:00+00:00"
    _write(root, "data/market/dashboard/dashboard_latest.json", {"expected_as_of": daily, "data_status": READY})
    _write(root, "data/market/us_stock_intelligence/breakout_scan_latest.json", {"expected_as_of": daily, "data_status": READY})
    _write(root, "data/market/us_stock_intelligence/portfolio_scores_latest.json", {"expected_as_of": daily, "data_status": READY})
    _write(root, "data/market/etf_cta/cta_latest.json", {"data_status": [{"symbol": "AIQ", "status": "CURRENT", "as_of": daily}]})
    _write(root, "data/market/fund_nav/fund_cta_latest.json", {
        "generated_at": generated,
        "nav_refresh": {"status": "COMPLETE"},
        "results": [{"fund_nav_as_of": daily} for _ in range(7)],
    })
    _write(root, "data/market/taiwan_cta/cta_latest.json", {"data_cutoff": taiwan})
    _write(root, "data/market/taiwan_stock_intelligence/screen_latest.json", {"expected_as_of": taiwan, "data_status": READY})
    _write(root, "data/market/taiwan_stock_intelligence/cta/cta_latest.json", {"screen_as_of": taiwan, "requested_count": 200, "coverage": {"current": 200, "stale_last_known": 0, "unknown": 0}})
    _write(root, "data/market/taiwan_stock_intelligence/daily_context_latest.json", {"screen_as_of": taiwan, "display_status": "CURRENT"})
    _write(root, "data/market/macro_regime/macro_regime_latest.json", {"generated_at": generated})
    _write(root, "data/market/fund_nav/alpha_latest.json", {"results": [{"end_date": daily}]})
    _write(root, "data/market/fund_nav/peer_ranking_latest.json", {"generated_at": generated})
    _write(root, "data/market/stockq_rotation/rotation_latest.json", {"as_of": daily})
    _write(root, "data/market/sector_rotation/rotation_latest.json", {"as_of": daily})
    _write(root, "data/market/fundamental_cycle/fundamental_cycle_latest.json", {"generated_at": generated})
    _write(root, "data/market/ai_revolution/ai_revolution_latest.json", {"generated_at": generated, "cache_status": "VALID", "review_required": False})
    _write(root, "data/market/fund_intelligence/validation_latest.json", {"generated_at": generated, "status": "PASS"})


def _module(report: dict, module_id: str) -> dict:
    return next(item for item in report["modules"] if item["module_id"] == module_id)


def test_all_ready_caches_produce_ready_health(tmp_path: Path) -> None:
    _seed_ready(tmp_path)

    report = build_health_report(tmp_path, now=NOW)

    assert report["status"] == READY
    assert report["scope_status"] == {"morning": READY, "asia": READY, "weekly": READY}
    assert report["recovery_workflows"] == []
    assert report["action_readiness"] == "SAFE"


def test_missing_action_cache_is_blocked_and_recovery_is_deduplicated(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    (tmp_path / "data/market/dashboard/dashboard_latest.json").unlink()
    (tmp_path / "data/market/us_stock_intelligence/breakout_scan_latest.json").unlink()

    report = build_health_report(tmp_path, now=NOW)

    assert report["status"] == BLOCKED
    assert report["scope_status"]["morning"] == BLOCKED
    assert report["recovery_workflows"].count("update-market-dashboard.yml") == 1
    assert _module(report, "market_dashboard")["status"] == BLOCKED


def test_ai_review_is_partial_manual_issue_not_failed_schedule(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    _write(tmp_path, "data/market/ai_revolution/ai_revolution_latest.json", {
        "generated_at": "2026-08-30T02:00:00+00:00",
        "cache_status": "VALID",
        "review_required": True,
    })

    report = build_health_report(tmp_path, now=NOW)

    assert report["status"] == PARTIAL
    assert report["scope_status"]["weekly"] == PARTIAL
    assert _module(report, "ai_revolution")["retryable"] is False
    assert report["recovery_workflows"] == []


def test_one_unknown_taiwan_candidate_is_partial_without_ranking_change(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    _write(tmp_path, "data/market/taiwan_stock_intelligence/cta/cta_latest.json", {
        "screen_as_of": "2026-08-28",
        "requested_count": 200,
        "coverage": {"current": 199, "stale_last_known": 0, "unknown": 1},
    })

    report = build_health_report(tmp_path, now=NOW)

    item = _module(report, "taiwan_candidate_cta")
    assert item["status"] == PARTIAL
    assert item["retryable"] is False
    assert "unknown 1" in item["reason"]
    assert report["scope_status"]["asia"] == PARTIAL


def test_stale_daily_cache_blocks_only_affected_scope(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    _write(tmp_path, "data/market/taiwan_cta/cta_latest.json", {"data_cutoff": "2026-08-24"})

    report = build_health_report(tmp_path, now=NOW)

    assert report["scope_status"]["asia"] == BLOCKED
    assert report["scope_status"]["morning"] == READY
    assert "update-taiwan-cta.yml" in report["recovery_workflows"]
