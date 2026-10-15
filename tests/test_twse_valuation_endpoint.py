from datetime import date

import pytest

from scripts.update_taiwan_stock_screen import fetch_dated_market, update


def official_fetcher(valuation_day="20261015"):
    def fetch(url, **kwargs):
        assert kwargs["expected_type"] is dict
        if "/exchangeReport/MI_INDEX?" in url:
            return {"stat": "OK", "date": "20261015", "tables": [{
                "fields": ["證券代號", "證券名稱", "收盤價", "成交金額"],
                "data": [["2330", "台積電", "2500", "1000000"]],
            }]}
        if "/rwd/zh/afterTrading/BWIBBU_d?" in url:
            assert "date=20261015" in url
            return {"stat": "OK", "date": valuation_day,
                    "fields": ["證券名稱", "股價淨值比", "證券代號", "本益比"],
                    "data": [["台積電", "5.1", "2330", "25.2"]]}
        raise AssertionError(f"Unexpected source: {url}")
    return fetch


def test_published_aftertrading_report_maps_valuation_columns():
    prices, valuations = fetch_dated_market(date(2026, 10, 15), official_fetcher())
    assert prices[0]["ClosingPrice"] == "2500"
    assert valuations == [{"Date": "2026-10-15", "Code": "2330",
                           "Name": "台積電", "PEratio": "25.2", "PBratio": "5.1"}]


def test_prior_session_valuation_cannot_replace_valid_screen(tmp_path):
    path = tmp_path / "screen_latest.json"
    path.write_text('{"expected_as_of":"2026-10-14"}')
    before = path.read_bytes()
    with pytest.raises(ValueError, match="not ready"):
        update(tmp_path, market_date=date(2026, 10, 15),
               fetcher=official_fetcher("20261014"))
    assert path.read_bytes() == before
