from dataclasses import replace
from datetime import date
from onecool_os.market.us_breakout_scan import fundamental_validation_error
from onecool_os.market.us_background_validation import build_background_validation
from onecool_os.market.sec_fundamentals import annotate_reviewed_exclusions
from tests.test_us_breakout_scan import _fundamental, _history
import pytest
from onecool_os.market.yahoo_chart import parse_adjusted_chart


def chart_fixture():
    return {"chart": {"result": [{"meta": {"exchangeTimezoneName": "America/New_York"},
            "timestamp": [1793114200, 1793200600],
            "indicators": {"quote": [{"open": [100, 104], "high": [105, 109],
                "low": [98, 102], "close": [102, 106], "volume": [1000, 1200]}],
                "adjclose": [{"adjclose": [51, 53]}]}}]}}


def test_chart_adjusts_entire_ohlc_from_observed_factor_and_discards_future_session():
    p = chart_fixture()
    bars = parse_adjusted_chart(p, "2026-10-27")
    assert len(bars) == 1
    assert (bars[0].open, bars[0].high, bars[0].low, bars[0].close) == (50, 52.5, 49, 51)
    assert bars[0].volume == 1000


def test_chart_missing_adjustment_and_duplicate_sessions_never_pass():
    p = chart_fixture()
    p["chart"]["result"][0]["indicators"]["adjclose"][0]["adjclose"][0] = None
    with pytest.raises(ValueError, match="INCOMPLETE"):
        parse_adjusted_chart(p, "2026-10-28")
    p = chart_fixture()
    p["chart"]["result"][0]["timestamp"][1] = p["chart"]["result"][0]["timestamp"][0]
    with pytest.raises(ValueError, match="DUPLICATE"):
        parse_adjusted_chart(p, "2026-10-28")


def test_unattributed_provider_cache_cannot_pass_validation():
    f = _fundamental("2026-10-27")
    for bad in (replace(f, source_urls=()), replace(f, published_as_of=None),
                replace(f, source_urls=("http://unverified",))):
        assert fundamental_validation_error(bad, date(2026, 10, 27))


def test_background_never_carries_old_dates_or_overrides_cta():
    bars = _history()
    cutoff = bars[-1].trading_date.isoformat()
    p = build_background_validation({"SPY": bars, "AMD": bars, "TSM": bars[:-1], "NVDA": bars}, cutoff)
    assert p["data_status"] == "PARTIAL"
    assert p["results"][0]["validation_status"] == "PASSED"
    assert p["results"][1]["validation_status"] == "Technical Data Validation Failed"
    assert "adjusted_close" not in p["results"][1]
    assert all("cta" not in r for r in p["results"])


def test_current_sec_evidence_classifies_rule_exclusion_without_manual_expiry_extension():
    scan = {"validated_count": 1, "universe_size": 2,
            "exclusions": [{"symbol": "BA", "technical_confidence": 100,
                            "reason": "fundamental validation unavailable"}]}
    detail = {"BA": {"status": "NONPOSITIVE_COMPARISON_BASE:quarterly_eps",
                     "source_url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000012927.json",
                     "evidence": {"pairs": {"quarterly_eps": {"prior": {"val": -1}}}}}}
    annotate_reviewed_exclusions(scan, {}, "2026-10-27", detail)
    assert scan["assessment_status"] == "COMPLETE"
    assert scan["rule_excluded_count"] == 1
    assert scan["validated_count"] == 1
