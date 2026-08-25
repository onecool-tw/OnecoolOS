import json
from datetime import UTC, datetime

from onecool_os.market.macro_regime import (
    build_macro_regime_payload,
    update_macro_regime_cache,
)


def record(symbol, alignment, as_of="2026-08-24"):
    return {
        "symbol": symbol,
        "as_of": as_of,
        "weekly_cross": {"alignment": alignment},
    }


def inputs(overrides=None):
    states = {
        "SPY": "GOLDEN", "QQQ": "GOLDEN", "RUSSELL_2000": "GOLDEN",
        "0050": "GOLDEN", "VIX": "DEATH", "DXY": "DEATH",
        "US30Y": "DEATH", "BTC": "GOLDEN",
    }
    states.update(overrides or {})
    dashboard = {"results": [record(symbol, state) for symbol, state in states.items()]}
    etf = {"results": [record("WTI", "DEATH")]}
    return dashboard, etf


def test_market_and_fundamentals_align_positive_without_cta_override():
    dashboard, etf = inputs()
    payload = build_macro_regime_payload(
        dashboard,
        etf,
        {"phase": "GROWTH", "confidence": "HIGH", "data_as_of": "2026-07-01"},
        generated_at=datetime(2026, 8, 25, tzinfo=UTC),
    )

    assert payload["market_regime"]["primary_scenario"] == "A LIQUIDITY RISK-ON"
    assert payload["macro_confirmation"] == "ALIGNED_POSITIVE"
    assert payload["taiwan_operating_posture"] == "CTA_BULLISH_NORMAL"
    assert payload["allocation_policy"] == "QUALITATIVE_ONLY_NO_PERCENTAGES"
    assert payload["cta_override_allowed"] is False


def test_fundamentals_cannot_front_run_bearish_weekly_cta():
    dashboard, etf = inputs({
        "SPY": "DEATH", "QQQ": "DEATH", "RUSSELL_2000": "DEATH",
        "0050": "DEATH", "VIX": "GOLDEN", "DXY": "GOLDEN",
        "US30Y": "GOLDEN", "BTC": "DEATH",
    })
    payload = build_macro_regime_payload(
        dashboard, etf, {"phase": "RECOVERY", "confidence": "MEDIUM"}
    )

    assert payload["market_regime"]["primary_scenario"] == "D DEFENSIVE STRESS"
    assert payload["macro_confirmation"] == "FUNDAMENTALS_LEAD_DIVERGENT"
    assert payload["taiwan_operating_posture"] == "WATCH_ONLY_WAIT_WEEKLY_CTA"


def test_update_publishes_latest_and_snapshot(tmp_path):
    dashboard, etf = inputs()
    paths = {
        "data/market/dashboard/dashboard_latest.json": dashboard,
        "data/market/etf_cta/cta_latest.json": etf,
        "data/market/fundamental_cycle/fundamental_cycle_latest.json": {
            "phase": "GROWTH", "confidence": "HIGH"
        },
    }
    for relative, payload in paths.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    payload = update_macro_regime_cache(tmp_path)

    assert (tmp_path / "data/market/macro_regime/macro_regime_latest.json").exists()
    assert (tmp_path / f"data/market/macro_regime/snapshots/{payload['generated_at'][:10]}.json").exists()
