import json
from datetime import date, timedelta
from pathlib import Path

from onecool_os.market.dashboard import (
    MARKET_SYMBOLS,
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
        "SPY", "QQQ", "DIA", "SOXX", "NVDA", "0050", "2330"
    ]
    assert [item.provider_symbol for item in MARKET_SYMBOLS[-2:]] == [
        "0050.TW", "2330.TW"
    ]


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
        record("SOXX", "US", "BULLISH", "BUY"),
        record("NVDA", "US", "BULLISH", "BUY"),
        record("0050", "TW", "BULLISH", "BUY"),
        record("2330", "TW", "BULLISH", "HOLD"),
    ]

    payload = build_dashboard_payload(records)

    assert payload["summary"]["us_market_trend"] == "BULLISH"
    assert payload["summary"]["ai_market_line"] == "CONFIRMED"
    assert payload["summary"]["taiwan_market_trend"] == "BULLISH"
    assert payload["summary"]["us_taiwan_synchronization"] == "SYNCHRONIZED"
    assert payload["summary_method"] == "deterministic CTA aggregation; no forecast"
    assert payload["provider"] == "mixed_by_symbol"
    assert payload["provider_by_symbol"]["SPY"] == "alpha_vantage"
    assert payload["provider_by_symbol"]["0050"] == "yahoo_finance"
    assert payload["provider_by_symbol"]["2330"] == "yahoo_finance"
    assert payload["history_bootstrap_provider"].startswith("yahoo_finance")


def test_cache_loader_and_fund_context_never_query_provider(tmp_path: Path) -> None:
    dashboard_dir = tmp_path / "data" / "market" / "dashboard"
    fund_dir = tmp_path / "data" / "market" / "fund_nav"
    dashboard_dir.mkdir(parents=True)
    fund_dir.mkdir(parents=True)
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
    assert context["market_dashboard"]["generated_at"]
    assert context["fund_alpha"] == {"results": []}
    assert context["fund_cta"] == {
        "results": [{"fund_code": "A10124"}]
    }
    assert context["peer_ranking"] == {
        "results": [{"fund_code": "A10124"}]
    }
