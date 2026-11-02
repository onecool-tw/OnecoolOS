import hashlib
import json
from datetime import date

import pytest

from scripts import update_taiwan_stock_screen as screen


def test_dated_prices_use_published_after_trading_route():
    calls = []

    def fetch(url, **kwargs):
        calls.append(url)
        fields = (["證券代號", "證券名稱", "本益比", "股價淨值比"]
                  if "BWIBBU" in url else
                  ["證券代號", "證券名稱", "收盤價", "成交金額"])
        return {"stat": "OK", "date": "20261019", "fields": fields,
                "data": [["2330", "台積電", "20", "5"]]}

    prices, valuations = screen.fetch_dated_market(date(2026, 10, 19), fetch)
    assert all("/rwd/zh/afterTrading/" in url for url in calls)
    assert prices[0]["Date"] == valuations[0]["Date"] == "2026-10-19"
    assert prices[0]["ClosingPrice"] == "20"


def test_backfill_preserves_prior_bytes_and_identical_retry_is_idempotent(tmp_path, monkeypatch):
    payload = {"expected_as_of": "2026-10-19", "top5": [{"score": 90}]}
    monkeypatch.setattr(screen, "select_income_period", lambda *args: dict(payload))
    screen.update(tmp_path, fetcher=lambda *args, **kwargs: [])
    snapshot = tmp_path / "snapshots/2026-10-19.json"
    original = snapshot.read_bytes()
    payload["top5"] = [{"score": 91}]
    screen.update(tmp_path, fetcher=lambda *args, **kwargs: [])
    archive = tmp_path / "snapshots/revisions/2026-10-19" / (hashlib.sha256(original).hexdigest() + ".json")
    assert archive.read_bytes() == original
    assert json.loads(snapshot.read_bytes())["top5"] == [{"score": 91}]
    assert (tmp_path / "screen_latest.json").read_bytes() == snapshot.read_bytes()
    screen.update(tmp_path, fetcher=lambda *args, **kwargs: [])
    assert list(archive.parent.iterdir()) == [archive]


def test_unpublished_dated_report_never_overwrites_last_success(tmp_path):
    latest = tmp_path / "screen_latest.json"
    latest.write_text('{"expected_as_of":"2026-10-16"}')
    original = latest.read_bytes()
    with pytest.raises(ValueError, match="not ready"):
        screen.update(tmp_path, market_date=date(2026, 10, 19),
                      fetcher=lambda *args, **kwargs: {"stat": "no data"})
    assert latest.read_bytes() == original


def test_partial_quarter_keeps_verified_common_eps_and_current_prices(tmp_path):
    from test_taiwan_stock_screen import _inputs
    prices, valuations, revenues, income = _inputs()
    prior = screen.build_taiwan_stock_screen_payload(prices, valuations, revenues, income)
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    raw = json.dumps(prior).encode()
    (snapshots / "2026-08-25.json").write_bytes(raw)
    for row in prices + valuations:
        row["Date"] = "1151102"
    partial = [{**income[0], "季別": "3", "基本每股盈餘（元）": "99"}]
    result = screen.select_income_period(tmp_path, prices, valuations, revenues, partial)
    assert result["expected_as_of"] == "2026-11-02"
    assert result["fundamentals_as_of"] == "2026Q2"
    assert result["validated_count"] == len(income)
    assert result["rankings"][0]["eps"] != 99
    assert result["fundamental_period_selection"]["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert all(x["financial_quality"]["status"] != "NORMAL" for x in result["rankings"])


def test_partial_quarter_without_valid_previous_period_fails_closed(tmp_path):
    from test_taiwan_stock_screen import _inputs
    prices, valuations, revenues, income = _inputs()
    partial = [{**income[0], "季別": "3"}]
    with pytest.raises(ValueError, match="coverage incomplete"):
        screen.select_income_period(tmp_path, prices, valuations, revenues, partial)


def test_complete_new_quarter_replaces_old_quarter(tmp_path):
    from test_taiwan_stock_screen import _inputs
    prices, valuations, revenues, income = _inputs()
    complete = [{**x, "季別": "3"} for x in income]
    result = screen.select_income_period(tmp_path, prices, valuations, revenues, complete)
    assert result["fundamentals_as_of"] == "2026Q3"
    assert "fundamental_period_selection" not in result
