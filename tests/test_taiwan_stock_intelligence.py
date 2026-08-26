import json
from datetime import UTC, date, datetime

from onecool_os.market.taiwan_stock_intelligence import (
    build_taiwan_stock_daily_context,
)


def write(root, relative, payload):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def setup_prompt(root):
    path = root / "config/taiwan_stock_intelligence_master_prompt.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "版本：v1.3 Taiwan Broad Screen with Background CTA\n",
        encoding="utf-8",
    )


def write_stock_cta(root, *, status="CURRENT", weekly="GOLDEN", daily="GOLDEN"):
    write(root, "data/market/taiwan_stock_intelligence/cta/cta_latest.json", {
        "screen_as_of": "2026-08-24",
        "generated_at": "2026-08-25T00:00:00+00:00",
        "requested_count": 200,
        "coverage": {"current": 200, "stale_last_known": 0, "unknown": 0},
        "results": [{
            "symbol": "2330", "as_of": "2026-08-24",
            "update_status": status,
            "state": f"WEEKLY_{'BULLISH' if weekly == 'GOLDEN' else 'BEARISH'}_DAILY_{'BULLISH' if daily == 'GOLDEN' else 'BEARISH'}",
            "action": "ELIGIBLE_IF_0050_BULLISH_AND_PRESSURE_GREEN",
            "cta": "BUY",
            "weekly_cross": {"alignment": weekly},
            "daily_cross": {"alignment": daily},
        }],
    })


def test_current_candidates_require_cta_and_green_pressure(tmp_path):
    setup_prompt(tmp_path)
    write(tmp_path, "data/market/taiwan_stock_intelligence/screen_latest.json", {
        "expected_as_of": "2026-08-24", "data_status": "READY",
        "top5": [{"symbol": "2330", "score": 90}],
    })
    write(tmp_path, "data/market/taiwan_cta/cta_latest.json", {
        "results": [{"symbol": "0050", "weekly_cross": {"alignment": "GOLDEN"}}]
    })
    write_stock_cta(tmp_path)

    payload = build_taiwan_stock_daily_context(
        tmp_path,
        today=date(2026, 8, 25),
        generated_at=datetime(2026, 8, 25, tzinfo=UTC),
    )

    assert payload["display_status"] == "CURRENT"
    assert payload["candidate_action_gate"] == "REQUIRES_INDIVIDUAL_CTA_AND_PRESSURE_GREEN"
    assert payload["top5"][0]["candidate_role"] == "RESEARCH_PRIORITY_ONLY"
    assert payload["top5"][0]["action_eligibility"] == (
        "ELIGIBLE_IF_0050_BULLISH_AND_PRESSURE_GREEN"
    )
    assert payload["top5"][0]["individual_cta"]["state"] == (
        "WEEKLY_BULLISH_DAILY_BULLISH"
    )
    assert payload["candidate_cta_cache"]["requested_count"] == 200
    assert payload["optional_quality_research"]["authority"] == "NONE"


def test_stale_screen_is_displayed_with_original_date_but_cannot_trade(tmp_path):
    setup_prompt(tmp_path)
    write(tmp_path, "data/market/taiwan_stock_intelligence/screen_latest.json", {
        "expected_as_of": "2026-08-20", "data_status": "READY",
        "top5": [{"symbol": "2330", "score": 90}],
    })
    write(tmp_path, "data/market/taiwan_cta/cta_latest.json", {
        "results": [{"symbol": "0050", "weekly_cross": {"alignment": "GOLDEN"}}]
    })

    payload = build_taiwan_stock_daily_context(
        tmp_path, today=date(2026, 8, 25)
    )

    assert payload["display_status"] == "STALE"
    assert payload["screen_as_of"] == "2026-08-20"
    assert payload["top5"][0]["symbol"] == "2330"
    assert payload["candidate_action_gate"] == "WATCH_ONLY_STALE_OR_MISSING_SCREEN"


def test_bearish_0050_keeps_current_candidates_watch_only(tmp_path):
    setup_prompt(tmp_path)
    write(tmp_path, "data/market/taiwan_stock_intelligence/screen_latest.json", {
        "expected_as_of": "2026-08-25", "data_status": "READY",
        "top5": [{"symbol": "2330", "score": 90}],
    })
    write(tmp_path, "data/market/taiwan_cta/cta_latest.json", {
        "results": [{"symbol": "0050", "weekly_cross": {"alignment": "DEATH"}}]
    })

    payload = build_taiwan_stock_daily_context(
        tmp_path, today=date(2026, 8, 25)
    )

    assert payload["candidate_action_gate"] == "WATCH_ONLY_0050_WEEKLY_BEARISH"
    assert payload["top5"][0]["action_eligibility"] == (
        "WATCH_ONLY_0050_WEEKLY_BEARISH"
    )


def test_optional_quality_review_never_blocks_a_taiwan_candidate(tmp_path):
    setup_prompt(tmp_path)
    write(tmp_path, "data/market/taiwan_stock_intelligence/screen_latest.json", {
        "expected_as_of": "2026-08-25", "data_status": "READY",
        "top5": [{"symbol": "2330", "score": 99, "industry": "半導體業"}],
    })
    write(tmp_path, "data/market/taiwan_cta/cta_latest.json", {
        "results": [{"symbol": "0050", "weekly_cross": {"alignment": "GOLDEN"}}]
    })
    write_stock_cta(tmp_path)

    payload = build_taiwan_stock_daily_context(tmp_path, today=date(2026, 8, 25))
    item = payload["top5"][0]

    assert "super_growth_bucket" not in item
    assert item["action_eligibility"] == (
        "ELIGIBLE_IF_0050_BULLISH_AND_PRESSURE_GREEN"
    )
    assert payload["optional_quality_research"]["application"] == (
        "MANUAL_ON_REQUEST_ONLY"
    )


def test_missing_individual_cta_is_unknown_and_never_actionable(tmp_path):
    setup_prompt(tmp_path)
    write(tmp_path, "data/market/taiwan_stock_intelligence/screen_latest.json", {
        "expected_as_of": "2026-08-25", "data_status": "READY",
        "top5": [{"symbol": "2330", "score": 90}],
    })
    write(tmp_path, "data/market/taiwan_cta/cta_latest.json", {
        "results": [{"symbol": "0050", "weekly_cross": {"alignment": "GOLDEN"}}]
    })

    payload = build_taiwan_stock_daily_context(tmp_path, today=date(2026, 8, 25))

    assert payload["top5"][0]["individual_cta"]["update_status"] == "UNKNOWN"
    assert payload["top5"][0]["action_eligibility"] == (
        "WATCH_ONLY_INDIVIDUAL_CTA_UNKNOWN"
    )
