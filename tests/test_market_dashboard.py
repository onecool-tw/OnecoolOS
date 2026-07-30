import json
from datetime import date, timedelta
from pathlib import Path

from onecool_os.market.dashboard import (
    DASHBOARD_ACTION_REFRESH_GROUPS,
    MARKET_SYMBOLS,
    US_PORTFOLIO_CTA_SYMBOLS,
    MarketCTA,
    build_dashboard_payload,
    dashboard_record,
    load_latest_dashboard,
)
from onecool_os.market.etf_cta import CTAResult, DailyBar
from onecool_os.market.fund_intelligence import load_fund_intelligence_context


def record(symbol: str, market: str, trend: str, cta: str) -> MarketCTA:
    return MarketCTA(
        symbol=symbol,
        provider_symbol=symbol,
        market=market,
        theme="test",
        as_of="2026-07-17",
        current_price=100,
        sma50=90,
        sma200=80,
        weekly_ma30=85,
        weekly_ma50=75,
        trend=trend,
        cta=cta,
        confidence=100,
        reason="test",
    )


def test_dashboard_symbols_are_fixed_and_provider_mapped() -> None:
    assert [item.symbol for item in MARKET_SYMBOLS] == [
        "SPY", "QQQ", "RUSSELL_2000", "DIA", "SOXX", "NVDA", "BABA",
        "XYZ", "QRVO", "RH", "UPBD", "0050", "2330", "VIX", "DXY",
        "US30Y",
    ]
    assert {item.symbol: item.provider_symbol for item in MARKET_SYMBOLS}[
        "US30Y"
    ] == "^TYX"
    assert DASHBOARD_ACTION_REFRESH_GROUPS == {
        "group_a": ("SPY", "QQQ", "DIA"),
        "group_b": ("SOXX", "NVDA"),
    }
    assert set().union(*DASHBOARD_ACTION_REFRESH_GROUPS.values()) == {
        "SPY", "QQQ", "DIA", "SOXX", "NVDA"
    }


def test_dashboard_record_uses_shared_cta_values() -> None:
    result = CTAResult(
        symbol="SPY",
        as_of="2026-07-17",
        price=100,
        daily_50ma=90,
        daily_200ma=80,
        weekly_30ma=85,
        weekly_50ma=75,
        cta="BUY",
        reason="shared",
    )

    item = dashboard_record(MARKET_SYMBOLS[0], result)

    assert item.cta == "BUY"
    assert item.trend == "BULLISH"
    assert item.confidence == 100
    assert item.sma50 == result.daily_50ma
    assert item.daily_cross is result.daily_cross
    assert item.weekly_cross is result.weekly_cross


def test_market_summary_is_deterministic_and_not_a_forecast() -> None:
    records = [
        record("SPY", "US", "BULLISH", "BUY"),
        record("QQQ", "US", "BULLISH", "BUY"),
        record("DIA", "US", "BULLISH", "HOLD"),
        record("RUSSELL_2000", "US", "BULLISH", "BUY"),
        record("SOXX", "US", "BULLISH", "BUY"),
        record("NVDA", "US", "BULLISH", "BUY"),
        record("BABA", "US", "MIXED", "HOLD"),
        record("XYZ", "US", "BEARISH", "SELL"),
        record("QRVO", "US", "MIXED", "WATCH"),
        record("RH", "US", "MIXED", "HOLD"),
        record("UPBD", "US", "BULLISH", "BUY"),
        record("0050", "TW", "BULLISH", "BUY"),
        record("2330", "TW", "BULLISH", "HOLD"),
    ]

    payload = build_dashboard_payload(records)

    assert payload["summary"]["us_market_trend"] == "BULLISH"
    assert payload["summary"]["ai_market_line"] == "CONFIRMED"
    assert payload["summary"]["taiwan_market_trend"] == "BULLISH"
    assert payload["summary"]["us_taiwan_synchronization"] == "SYNCHRONIZED"
    assert payload["summary_method"] == "deterministic CTA aggregation; no forecast"
    assert payload["schema_version"] == "1.4"
    assert payload["expected_as_of"] == "2026-07-17"
    assert payload["data_status"] == "READY"
    assert payload["last_successful_update_at"] == payload["generated_at"]
    assert payload["index_cta_basis"]["mappings"]["Nasdaq"] == "QQQ"
    assert payload["portfolio_cta_basis"]["symbols"] == list(
        US_PORTFOLIO_CTA_SYMBOLS
    )
    assert payload["portfolio_cta_basis"]["as_of"] == "2026-07-17"
    assert payload["provider"] == "mixed_by_symbol"
    assert payload["provider_by_symbol"]["SPY"] == "alpha_vantage"
    assert payload["provider_by_symbol"]["0050"] == "yahoo_finance"
    assert payload["provider_by_symbol"]["2330"] == "yahoo_finance"
    assert payload["provider_by_symbol"]["RUSSELL_2000"] == "yahoo_finance"
    assert payload["provider_by_symbol"]["BABA"] == "yahoo_finance"
    assert payload["provider_by_symbol"]["XYZ"] == "yahoo_finance"
    assert payload["provider_by_symbol"]["QRVO"] == "yahoo_finance"
    assert payload["provider_by_symbol"]["RH"] == "yahoo_finance"
    assert payload["provider_by_symbol"]["UPBD"] == "yahoo_finance"
    assert payload["provider_by_symbol"]["VIX"] == "yahoo_finance"
    assert payload["provider_by_symbol"]["DXY"] == "yahoo_finance"
    assert payload["provider_by_symbol"]["US30Y"] == "yahoo_finance"
    assert payload["history_bootstrap_provider"].startswith("yahoo_finance")


def test_cache_loader_and_fund_context_never_query_provider(tmp_path: Path) -> None:
    dashboard_dir = tmp_path / "data" / "market" / "dashboard"
    fund_dir = tmp_path / "data" / "market" / "fund_nav"
    dashboard_dir.mkdir(parents=True)
    fund_dir.mkdir(parents=True)
    prompt_dir = tmp_path / "config"
    prompt_dir.mkdir()
    prompt_dir.joinpath("fund_intelligence_master_prompt.md").write_text(
        "版本：v1.0 Freeze\n", encoding="utf-8"
    )
    (dashboard_dir / "dashboard_latest.json").write_text(
        json.dumps({"generated_at": "2026-07-19T00:00:00Z"}), encoding="utf-8"
    )
    (fund_dir / "alpha_latest.json").write_text(
        json.dumps({"results": []}), encoding="utf-8"
    )
    (fund_dir / "fund_cta_latest.json").write_text(
        json.dumps({"results": [{"fund_code": "A10124"}]}),
        encoding="utf-8",
    )
    (fund_dir / "peer_ranking_latest.json").write_text(
        json.dumps({"results": [{"fund_code": "A10124"}]}),
        encoding="utf-8",
    )

    assert load_latest_dashboard(tmp_path)["generated_at"]
    context = load_fund_intelligence_context(tmp_path)
    assert context["source_policy"] == "github_cache_only"
    assert context["master_prompt"]["version"] == "v1.0 Freeze"
    assert context["market_dashboard"]["generated_at"]
    assert context["fund_alpha"] == {"results": []}
    assert context["fund_cta"] == {
        "results": [{"fund_code": "A10124"}]
    }
    assert context["peer_ranking"] == {
        "results": [{"fund_code": "A10124"}]
    }


def test_dashboard_rejects_mixed_us_proxy_dates() -> None:
    records = [
        record("SPY", "US", "BULLISH", "BUY"),
        record("QQQ", "US", "BULLISH", "BUY"),
        record("DIA", "US", "BULLISH", "BUY"),
        record("RUSSELL_2000", "US", "BULLISH", "BUY"),
    ]
    records[-1] = MarketCTA(
        **{**records[-1].__dict__, "as_of": "2026-07-16"}
    )

    try:
        build_dashboard_payload(records)
    except ValueError as exc:
        assert "dates are inconsistent" in str(exc)
    else:
        raise AssertionError("Mixed US CTA dates must not be published")


def test_dashboard_rejects_mixed_us_portfolio_dates() -> None:
    records = [
        record("SPY", "US", "BULLISH", "BUY"),
        record("QQQ", "US", "BULLISH", "BUY"),
        record("DIA", "US", "BULLISH", "BUY"),
        record("RUSSELL_2000", "US", "BULLISH", "BUY"),
        *[
            record(symbol, "US", "MIXED", "HOLD")
            for symbol in US_PORTFOLIO_CTA_SYMBOLS
        ],
    ]
    records[-1] = MarketCTA(
        **{**records[-1].__dict__, "as_of": "2026-07-16"}
    )

    try:
        build_dashboard_payload(records)
    except ValueError as exc:
        assert "portfolio CTA dates must match" in str(exc)
    else:
        raise AssertionError("Mixed US portfolio CTA dates must not be published")
