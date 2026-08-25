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
    path.write_text("版本：v1.1 Taiwan Broad Screen\n", encoding="utf-8")


def test_current_candidates_require_cta_and_green_pressure(tmp_path):
    setup_prompt(tmp_path)
    write(tmp_path, "data/market/taiwan_stock_intelligence/screen_latest.json", {
        "expected_as_of": "2026-08-24", "data_status": "READY",
        "top5": [{"symbol": "2330", "score": 90}],
    })
    write(tmp_path, "data/market/taiwan_cta/cta_latest.json", {
        "results": [{"symbol": "0050", "weekly_cross": {"alignment": "GOLDEN"}}]
    })

    payload = build_taiwan_stock_daily_context(
        tmp_path,
        today=date(2026, 8, 25),
        generated_at=datetime(2026, 8, 25, tzinfo=UTC),
    )

    assert payload["display_status"] == "CURRENT"
    assert payload["candidate_action_gate"] == "REQUIRES_INDIVIDUAL_CTA_AND_PRESSURE_GREEN"
    assert payload["top5"][0]["candidate_role"] == "RESEARCH_PRIORITY_ONLY"


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
