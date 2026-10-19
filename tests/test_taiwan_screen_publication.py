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
    monkeypatch.setattr(screen, "build_taiwan_stock_screen_payload", lambda *args: dict(payload))
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
