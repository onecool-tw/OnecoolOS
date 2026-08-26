import json
from datetime import UTC, date, datetime, timedelta

from onecool_os.market.etf_cta import DailyBar
from onecool_os.market.taiwan_stock_cta import (
    classify_onecool_state,
    universe_from_screen,
    update_candidate_cta,
)


def history(end: date, *, falling: bool = False):
    bars = []
    for index in range(400):
        day = end - timedelta(days=399 - index)
        close = 500.0 - index if falling else 100.0 + index
        bars.append(DailyBar(
            trading_date=day, open=close, high=close, low=close, close=close,
            volume=1000, adjusted_close=close, source="test",
        ))
    return bars


def business_history(end: date):
    days = []
    cursor = end
    while len(days) < 400:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    days.reverse()
    return [DailyBar(
        trading_date=day, open=100 + index, high=100 + index,
        low=100 + index, close=100 + index, volume=1000,
        adjusted_close=100 + index, source="test",
    ) for index, day in enumerate(days)]


def write_screen(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "expected_as_of": "2026-08-25",
        "universe_method": "test universe",
        "universe": [
            {"symbol": "2330", "company_name": "台積電", "liquidity_rank": 1,
             "provider_symbol": "2330.TW"},
            {"symbol": "2317", "company_name": "鴻海", "liquidity_rank": 2,
             "provider_symbol": "2317.TW"},
        ],
    }), encoding="utf-8")


def test_background_cta_updates_full_universe_without_ranking_authority(tmp_path):
    screen = tmp_path / "screen.json"
    write_screen(screen)

    def fetcher(symbols, period):
        return {
            symbol: history(date(2026, 8, 25), falling=symbol == "2317.TW")
            for symbol in symbols
        }

    payload = update_candidate_cta(
        screen, tmp_path / "cta", fetcher=fetcher,
        generated_at=datetime(2026, 8, 26, tzinfo=UTC), batch_size=1,
    )

    assert payload["requested_count"] == 2
    assert payload["coverage"] == {
        "current": 2, "stale_last_known": 0, "unknown": 0,
    }
    assert payload["ranking_authority"] == "NONE"
    assert [item["symbol"] for item in payload["results"]] == ["2330", "2317"]
    assert payload["results"][0]["state"] == "WEEKLY_BULLISH_DAILY_BULLISH"
    assert payload["results"][1]["state"] == "WEEKLY_BEARISH_DAILY_BEARISH"


def test_failure_preserves_last_known_result_but_marks_it_stale(tmp_path):
    screen = tmp_path / "screen.json"
    data_dir = tmp_path / "cta"
    write_screen(screen)

    def all_ok(symbols, period):
        return {symbol: history(date(2026, 8, 25)) for symbol in symbols}

    update_candidate_cta(screen, data_dir, fetcher=all_ok)

    def one_missing(symbols, period):
        return {
            symbol: history(date(2026, 8, 26))
            for symbol in symbols if symbol != "2317.TW"
        }

    payload = update_candidate_cta(screen, data_dir, fetcher=one_missing)
    items = {item["symbol"]: item for item in payload["results"]}

    assert items["2330"]["update_status"] == "CURRENT"
    assert items["2317"]["update_status"] == "STALE_LAST_KNOWN"
    assert payload["coverage"]["stale_last_known"] == 1


def test_backward_compatible_universe_reconstruction_includes_exclusions():
    members = universe_from_screen({
        "rankings": [{"symbol": "2330", "liquidity_rank": 1}],
        "exclusions": [{"symbol": "2317", "reason": "missing valuation"}],
    })

    assert [item["symbol"] for item in members] == ["2330", "2317"]


def test_weekly_bearish_daily_bullish_is_only_a_rebound():
    state = classify_onecool_state({
        "update_status": "CURRENT",
        "weekly_cross": {"alignment": "DEATH"},
        "daily_cross": {"alignment": "GOLDEN"},
    })

    assert state["state"] == "WEEKLY_BEARISH_DAILY_BULLISH"
    assert state["action"] == "WATCH_ONLY_REBOUND_NOT_FORMAL_BULLISH"


def test_daily_updates_but_unfinished_week_is_not_used_as_weekly_cutoff(tmp_path):
    screen = tmp_path / "screen.json"
    write_screen(screen)

    def fetcher(symbols, period):
        return {symbol: business_history(date(2026, 8, 27)) for symbol in symbols}

    payload = update_candidate_cta(screen, tmp_path / "cta", fetcher=fetcher)
    item = payload["results"][0]

    assert item["source_data_as_of"] == "2026-08-27"
    assert item["weekly_data_as_of"] == "2026-08-21"
