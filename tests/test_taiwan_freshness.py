from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from onecool_os.market.session_cutoff import completed_daily_bars
from scripts.update_taiwan_stock_screen import normalize_dated_report, update


def test_previous_day_screen_not_current_after_close(tmp_path):
    import json
    from onecool_os.market.taiwan_stock_intelligence import build_taiwan_stock_daily_context
    from tests.test_taiwan_stock_intelligence import setup_prompt, write
    setup_prompt(tmp_path)
    write(tmp_path, "data/market/taiwan_stock_intelligence/screen_latest.json", {
        "expected_as_of": "2026-09-04", "data_status": "READY", "top5": [],
    })
    result = build_taiwan_stock_daily_context(tmp_path, generated_at=datetime(2026, 9, 7, 10, tzinfo=UTC))
    assert result["display_status"] == "STALE"
    assert result["screen_as_of"] == "2026-09-04"


@pytest.mark.parametrize("market,hour", [("TW", 6), ("JP", 7), ("KR", 7)])
def test_asia_drops_unfinished_and_future_bars(market, hour):
    bars = [SimpleNamespace(trading_date=date(2026, 9, d)) for d in (4, 7, 8)]
    assert completed_daily_bars(bars, market, datetime(2026, 9, 7, 3, tzinfo=UTC)) == bars[:1]
    assert completed_daily_bars(bars, market, datetime(2026, 9, 7, hour, tzinfo=UTC)) == bars[:2]


def test_dated_report_maps_named_columns_not_positions():
    payload = {"stat": "OK", "date": "20260907", "fields": ["本益比", "證券代號"], "data": [["12.3", "2330"]]}
    rows = normalize_dated_report(payload, date(2026, 9, 7), {"證券代號": "Code", "本益比": "PEratio"})
    assert rows == [{"Date": "2026-09-07", "Code": "2330", "PEratio": "12.3"}]
    with pytest.raises(ValueError, match="not ready"):
        normalize_dated_report(payload, date(2026, 9, 8), {"證券代號": "Code"})


def test_unpublished_session_preserves_last_success(tmp_path):
    path = tmp_path / "screen_latest.json"
    path.write_text('{"expected_as_of":"2026-09-04"}')
    before = path.read_bytes()
    with pytest.raises(ValueError, match="not ready"):
        update(tmp_path, market_date=date(2026, 9, 7), fetcher=lambda *a, **kw: {"stat": "no data"})
    assert path.read_bytes() == before


def test_missing_price_column_is_not_estimated():
    payload = {"stat": "OK", "date": "20260907", "fields": ["證券代號"], "data": [["2330"]]}
    with pytest.raises(ValueError, match="columns"):
        normalize_dated_report(payload, date(2026, 9, 7), {"證券代號": "Code", "收盤價": "ClosingPrice"})


def test_automatic_sync_is_non_blocking_but_formal_refresh_stays_strict():
    root = Path(__file__).resolve().parents[1]
    workflow = (
        root / ".github" / "workflows" / "update-taiwan-stock-screen.yml"
    ).read_text(encoding="utf-8")

    assert "github.event_name == 'workflow_run' || github.event_name == 'push'" in workflow
    assert "::warning::Opportunistic Taiwan refresh incomplete" in workflow
    assert "github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'" in workflow
    assert "::error::Formal Taiwan refresh incomplete" in workflow
    assert workflow.count("steps.screen.outcome == 'failure'") == 2
