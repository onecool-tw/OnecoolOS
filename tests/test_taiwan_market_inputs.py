from onecool_os.market.taiwan_market_inputs import (
    collect_once,
    collect_market_pressure_inputs,
    parse_taifex_vix,
    parse_taifex_vix_download,
    parse_twse_margin,
)
from datetime import datetime
from zoneinfo import ZoneInfo
from onecool_os.market.taiwan_stock_intelligence import market_pressure_input_readiness


def test_twse_margin_parses_current_date_and_both_balance_sides():
    payload = {"tables": [{
        "title": "115年09月17日 信用交易統計",
        "fields": ["項目", "前日餘額", "今日餘額", "今日增減"],
        "data": [
            ["融資金額(仟元)", "100,000", "101,500", "1,500"],
            ["融券(交易單位)", "9,000", "8,500", "-500"],
        ],
    }]}
    result = parse_twse_margin(payload, "2026-09-17")
    assert result["status"] == "VERIFIED"
    assert result["metrics"]["融資金額(仟元)"]["current"] == 101500
    assert result["metrics"]["融券(交易單位)"]["change"] == -500


def test_twse_margin_does_not_mislabel_previous_date_as_current():
    payload = {"tables": [{
        "title": "115年09月16日 信用交易統計",
        "fields": ["項目", "前日餘額", "今日餘額", "今日增減"],
        "data": [["融資", "1", "2", "1"], ["融券", "2", "1", "-1"]],
    }]}
    assert parse_twse_margin(payload, "2026-09-17")["status"] == "NOT_PUBLISHED"


def test_taifex_vix_reads_download_key_from_listing():
    html = """<table><tr><td>2026/09/17</td><td><input
        onClick="window.open('getVixData?filesname=20260917')"
        value="下載"></td></tr></table>"""
    result = parse_taifex_vix(html, "2026-09-17")
    assert result == {
        "status": "DOWNLOAD_AVAILABLE",
        "as_of": "2026-09-17",
        "file_date": "20260917",
        "error": None,
    }


def test_taifex_vix_accepts_explicit_txt_title_when_onclick_is_absent():
    html = '''<table><tr><td>2026/09/17</td><td><input
        title="20260917(txt)" value="下載"></td></tr></table>'''
    result = parse_taifex_vix(html, "2026-09-17")
    assert result["status"] == "DOWNLOAD_AVAILABLE"
    assert result["file_date"] == "20260917"


def test_taifex_vix_download_uses_official_last_one_minute_average():
    raw = (
        "交易日期\t時間\t臺指選擇權波動率指數\r\n"
        "20260917\t13450000\t\t\t24.06\r\n"
        "20260917\tLast 1 min AVG\t\t\t24.05\r\n"
    ).encode("cp950")
    result = parse_taifex_vix_download(raw, "2026-09-17")
    assert result["status"] == "VERIFIED"
    assert result["value"] == 24.05
    assert result["value_basis"] == "LAST_1_MIN_AVG"


def test_taifex_vix_distinguishes_parse_failure_from_not_published():
    published = '<tr><td>2026/09/17</td><td><input value="下載"></td></tr>'
    missing = """<tr><td>2026/09/16</td><td><input
        onClick="window.open('getVixData?filesname=20260916')"></td></tr>"""
    assert parse_taifex_vix(published, "2026-09-17")["status"] == "PUBLISHED_PARSE_FAILED"
    assert parse_taifex_vix(missing, "2026-09-17")["status"] == "NOT_PUBLISHED"


def test_collect_once_accepts_latest_official_margin_before_evening_publication():
    current_payload = {"stat": "很抱歉，沒有符合條件的資料"}
    prior_payload = {"tables": [{
        "title": "115年09月16日 信用交易統計",
        "fields": ["項目", "前日餘額", "今日餘額"],
        "data": [["融資", "1", "2"], ["融券", "2", "1"]],
    }]}
    def get_json(url):
        return current_payload if "20260917" in url else prior_payload
    listing = """<tr><td>2026/09/17</td><td><input
        onClick="window.open('getVixData?filesname=20260917')"></td></tr>"""
    raw = "20260917\tLast 1 min AVG\t\t\t24.05\r\n".encode("cp950")
    result = collect_once(
        "2026-09-17",
        get_json=get_json,
        get_text=lambda _: listing,
        get_bytes=lambda _: raw,
        now_taipei=datetime(2026, 9, 17, 18, 0, tzinfo=ZoneInfo("Asia/Taipei")),
    )
    assert result["margin"]["status"] == "VERIFIED"
    assert result["margin"]["as_of"] == "2026-09-16"
    assert result["margin"]["official_lag_accepted"] is True
    assert result["volatility"]["value"] == 24.05


def test_retry_stops_after_both_sources_are_verified():
    calls = []
    def collector(as_of):
        calls.append(as_of)
        status = "NOT_PUBLISHED" if len(calls) == 1 else "VERIFIED"
        return {
            "margin": {"status": status, "as_of": as_of if status == "VERIFIED" else None},
            "volatility": {"status": "VERIFIED", "as_of": as_of},
        }
    result = collect_market_pressure_inputs("2026-09-17", attempts=3, collector=collector)
    assert result["status"] == "READY"
    assert result["attempts_used"] == 2


def test_final_delivery_readiness_requires_both_current_official_inputs():
    payload = {
        "requested_as_of": "2026-09-17",
        "sources": {
            "margin": {"status": "VERIFIED", "as_of": "2026-09-17"},
            "volatility": {"status": "VERIFIED", "as_of": "2026-09-17"},
        },
    }
    assert market_pressure_input_readiness(payload, "2026-09-17")["status"] == "READY"
    payload["sources"]["volatility"]["status"] = "PUBLISHED_PARSE_FAILED"
    result = market_pressure_input_readiness(payload, "2026-09-17")
    assert result["status"] == "UPDATE_INCOMPLETE"
    assert "volatility_published_parse_failed" in result["issues"]


def test_final_delivery_accepts_verified_official_margin_lag():
    payload = {
        "requested_as_of": "2026-09-17",
        "sources": {
            "margin": {
                "status": "VERIFIED",
                "as_of": "2026-09-16",
                "official_lag_accepted": True,
            },
            "volatility": {"status": "VERIFIED", "as_of": "2026-09-17"},
        },
    }
    assert market_pressure_input_readiness(payload, "2026-09-17")["status"] == "READY"
