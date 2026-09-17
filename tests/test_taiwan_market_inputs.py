from onecool_os.market.taiwan_market_inputs import (
    collect_market_pressure_inputs,
    parse_taifex_vix,
    parse_twse_margin,
)
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


def test_taifex_vix_reads_value_from_input_element():
    html = '<table><tr><td>2026/09/17</td><td><input value="24.37"></td></tr></table>'
    result = parse_taifex_vix(html, "2026-09-17")
    assert result == {"status": "VERIFIED", "as_of": "2026-09-17", "value": 24.37, "error": None}


def test_taifex_vix_distinguishes_parse_failure_from_not_published():
    published = '<tr><td>2026/09/17</td><td><input value=""></td></tr>'
    missing = '<tr><td>2026/09/16</td><td><input value="23.1"></td></tr>'
    assert parse_taifex_vix(published, "2026-09-17")["status"] == "PUBLISHED_PARSE_FAILED"
    assert parse_taifex_vix(missing, "2026-09-17")["status"] == "NOT_PUBLISHED"


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
