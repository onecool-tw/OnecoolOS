from onecool_os.market.dashboard import MARKET_SYMBOLS, US_PORTFOLIO_CTA_SYMBOLS
from onecool_os.market.us_breakout_scan import PORTFOLIO_SYMBOLS, US_BREAKOUT_UNIVERSE, US_SECURITY_MASTER
from onecool_os.market.us_portfolio_scores import build_portfolio_score_payload
from onecool_os.market.us_stock_quality import EXISTING_PORTFOLIO_EXEMPTIONS


def test_all_active_portfolio_layers_track_swks():
    expected = ("BABA", "XYZ", "SWKS", "RH", "UPBD")
    assert US_PORTFOLIO_CTA_SYMBOLS == PORTFOLIO_SYMBOLS == expected
    assert EXISTING_PORTFOLIO_EXEMPTIONS == set(expected)
    mapping = {r.symbol: r for r in MARKET_SYMBOLS}
    assert mapping["SWKS"].provider_symbol == "SWKS"
    assert mapping["SWKS"].theme == "portfolio"
    assert "QRVO" not in mapping
    assert US_SECURITY_MASTER["SWKS"].company_name == "Skyworks Solutions, Inc."
    assert US_SECURITY_MASTER["SWKS"].security_type == "COMMON_STOCK"
    assert len(US_BREAKOUT_UNIVERSE) == 70
    assert "SWKS" not in US_BREAKOUT_UNIVERSE


def test_no_qrvo_history_or_scores_are_reused_for_swks():
    result = build_portfolio_score_payload({"QRVO": []}, expected_as_of="2026-10-06")
    assert [r["symbol"] for r in result["results"]] == list(PORTFOLIO_SYMBOLS)
    swks = next(r for r in result["results"] if r["symbol"] == "SWKS")
    assert swks["validation_status"] == "Technical Data Validation Failed"
    assert swks["canslim_score"] is None
    assert swks["minervini_score"] is None
