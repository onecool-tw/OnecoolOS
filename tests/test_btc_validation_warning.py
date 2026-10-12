import json
from onecool_os.market.fund_intelligence_validation import validate_fund_intelligence


def test_missing_completed_btc_week_is_disclosed(tmp_path):
    folder = tmp_path / "data/market/dashboard"
    folder.mkdir(parents=True)
    row = dict(symbol="BTC", current_price=100, sma50=90, sma200=80,
               weekly_ma30=80, weekly_ma50=90, weekly_data_status="LAGGED",
               weekly_data_as_of="2026-10-04", weekly_expected_as_of="2026-10-11")
    (folder / "dashboard_latest.json").write_text(json.dumps({"results": [row]}))
    result = validate_fund_intelligence(tmp_path)
    warning = next(w for w in result["warnings"] if w["module"] == "Bitcoin")
    assert warning["code"] == "WEEKLY_CLOSE_UNAVAILABLE"
    assert "2026-10-04" in warning["detail"] and "2026-10-11" in warning["detail"]
