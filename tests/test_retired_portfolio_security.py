from datetime import UTC, datetime
from onecool_os.market.dashboard import (
    MARKET_SYMBOLS, INNOVATION_OPTION_SYMBOLS, MarketCTA,
    build_dashboard_payload, retired_security_record,
)


def records(day):
    return [MarketCTA(c.symbol, c.provider_symbol, c.market, c.theme, day,
                      100, 90, 80, 85, 75, "BULLISH", "BUY", 100, "test")
            for c in MARKET_SYMBOLS]


def payload(rows, day):
    return build_dashboard_payload(rows, innovation_option_watch=[
        {"symbol": s, "as_of": day} for s in INNOVATION_OPTION_SYMBOLS
    ], reference_time=datetime(2026, 10, 7, 8, tzinfo=UTC))


def test_retired_qrvo_does_not_block_current_market_or_reuse_buy():
    rows = records("2026-10-06")
    rows = [r if r.symbol != "QRVO" else records("2026-10-02")[10]
            for r in rows]
    result = payload(rows, "2026-10-06")
    qrvo = next(r for r in result["results"] if r["symbol"] == "QRVO")
    assert result["data_status"] == "READY"
    assert result["expected_as_of"] == "2026-10-06"
    assert qrvo["cta"] == "Unknown"
    assert qrvo["as_of"] is None
    assert qrvo["current_price"] is None
    assert qrvo["assessment_as_of"] == "2026-10-06"
    assert qrvo["security_lifecycle"]["last_trading_date"] == "2026-10-02"
    assert qrvo["security_lifecycle"]["sources"]
    assert all(r["cta"] == "BUY" for r in result["results"] if r["symbol"] != "QRVO")


def test_pre_merger_qrvo_keeps_existing_engine_signal():
    result = payload(records("2026-10-02"), "2026-10-02")
    assert next(r for r in result["results"] if r["symbol"] == "QRVO")["cta"] == "BUY"
    config = next(c for c in MARKET_SYMBOLS if c.symbol == "QRVO")
    assert retired_security_record(config, "2026-10-02") is None


def test_other_stale_portfolio_still_fails_closed():
    rows = records("2026-10-06")
    from dataclasses import replace
    rows = [replace(r, as_of="2026-10-05") if r.symbol == "RH" else r for r in rows]
    try:
        payload(rows, "2026-10-06")
    except ValueError as exc:
        assert "US portfolio CTA dates" in str(exc)
    else:
        raise AssertionError("Active portfolio date gate must remain strict")


def test_retirement_does_not_bypass_index_date_gate():
    from dataclasses import replace
    rows = [replace(r, as_of="2026-10-05") if r.symbol == "QQQ" else r
            for r in records("2026-10-06")]
    try:
        payload(rows, "2026-10-06")
    except ValueError as exc:
        assert "US CTA proxy dates are inconsistent" in str(exc)
    else:
        raise AssertionError("Index date gate must remain strict")
