from datetime import date, timedelta

from onecool_os.market.fund_alpha import FundNav
from onecool_os.market.fund_cta import (
    CrossSignal,
    calculate_fund_cta,
    classify_signal_alignment,
    fund_cta_payload,
    dca_action,
    classify_auxiliary_confirmation,
    technical_conclusion,
)


def nav_history(days: int, *, rising: bool = True) -> list[FundNav]:
    start = date(2025, 1, 1)
    return [
        FundNav(
            nav_date=start + timedelta(days=index),
            nav=float(index + 1 if rising else days - index),
        )
        for index in range(days)
    ]


def test_fund_cta_reuses_shared_engine_for_rising_history() -> None:
    result = calculate_fund_cta(
        "A10124", nav_history(400), benchmark_cta="BUY"
    )

    # A rising synthetic history has bullish alignment, but no recent weekly
    # crossover event; weekly-priority CTA therefore correctly returns HOLD.
    assert result.fund_cta == "HOLD"
    assert result.data_quality == "sufficient_history"
    assert result.signal_alignment == "mixed_or_neutral"
    assert result.nav_observations == 400
    assert result.fund_nav_as_of == "2026-02-04"
    assert result.daily_cross is not None
    assert result.weekly_cross is not None


def test_fund_cta_is_unknown_when_history_is_short() -> None:
    result = calculate_fund_cta(
        "A10124", nav_history(199), benchmark_cta="BUY"
    )

    assert result.fund_cta == "UNKNOWN"
    assert result.data_quality == "insufficient_history"
    assert result.daily_200ma is None
    assert result.signal_alignment == "unknown"
    assert result.daily_cross is None
    assert result.weekly_cross is None


def test_signal_alignment_is_deterministic() -> None:
    assert classify_signal_alignment("BUY", "SELL") == "fund_lagging_strong_market"
    assert classify_signal_alignment("SELL", "BUY") == "fund_resilient_weak_market"
    assert classify_signal_alignment("WATCH", "SELL") == "joint_weakness"
    assert classify_signal_alignment("HOLD", "BUY") == "mixed_or_neutral"


def test_payload_declares_shared_engine() -> None:
    result = calculate_fund_cta("A10124", nav_history(400))
    payload = fund_cta_payload([result])

    assert payload["engine"] == "shared_onecool_cta_engine"
    assert payload["schema_version"] == "1.6"
    assert payload["method"]["cross_detection"]["priority"].startswith(
        "weekly crossover"
    )
    # Synthetic monotonic history need not contain an observable crossover.
    assert payload["results"][0]["weekly_cross"]["phase"] == "UNKNOWN"
    assert (
        payload["method"]["cross_detection"]["daily"]
        == "SMA50 crosses SMA200"
    )
    assert payload["results"][0]["fund_code"] == "A10124"


def weekly_signal(
    alignment: str,
    *,
    cross_status: str = "NONE",
    phase: str = "AGING",
) -> CrossSignal:
    return CrossSignal(
        alignment=alignment,
        cross_status=cross_status,
        last_cross_status=alignment,
        last_cross_date="2026-08-11",
        periods_since_cross=1,
        spread_pct=1.0,
        phase=phase,
    )


def test_existing_weekly_bull_continues_original_dca() -> None:
    daily_bull = weekly_signal("GOLDEN")
    daily_bear = weekly_signal("DEATH")
    weekly_bull = weekly_signal("GOLDEN")

    assert (
        dca_action("BUY", daily_bull, weekly_bull)
        == "TRANSITION_CONTINUE_ORIGINAL_DCA"
    )
    assert (
        dca_action("WATCH", daily_bear, weekly_bull)
        == "TRANSITION_CONTINUE_ORIGINAL_DCA"
    )


def test_existing_weekly_bear_uses_daily_trend_for_dca() -> None:
    weekly_bear = weekly_signal("DEATH")

    assert (
        dca_action("SELL", weekly_signal("GOLDEN"), weekly_bear)
        == "REDUCED_DCA"
    )
    assert (
        dca_action("SELL", weekly_signal("DEATH"), weekly_bear)
        == "PAUSE_DCA"
    )


def test_new_weekly_cross_owns_capital_action() -> None:
    assert (
        dca_action(
            "BUY",
            weekly_signal("GOLDEN"),
            weekly_signal("GOLDEN", cross_status="GOLDEN", phase="NEW"),
        )
        == "DEPLOY_LUMP_SUM_AND_CONTINUE_DCA"
    )
    assert (
        dca_action(
            "SELL",
            weekly_signal("DEATH"),
            weekly_signal("DEATH", cross_status="DEATH", phase="CONFIRMED"),
        )
        == "REDEEM_AT_NEXT_AVAILABLE_NAV"
    )


def test_action_requires_valid_fund_and_signals() -> None:
    signal = weekly_signal("GOLDEN")
    assert dca_action("UNKNOWN", signal, signal) == "DATA_REVIEW"
    assert dca_action("SELL", None, signal) == "DATA_REVIEW"
    assert dca_action("SELL", signal, None) == "DATA_REVIEW"

def auxiliary(symbol: str, cta: str, phase: str = "AGING") -> dict:
    cross = {"phase": phase}
    return {
        "symbol": symbol,
        "cta": cta,
        "daily_cross": cross,
        "weekly_cross": cross,
    }


def test_auxiliary_confirmation_stays_hidden_when_normal() -> None:
    result = classify_auxiliary_confirmation(
        "BUY", "BUY", auxiliary("GLD", "BUY")
    )

    assert result["auxiliary_alignment"] == "CONFIRMS"
    assert result["auxiliary_visibility"] == "HIDE"


def test_auxiliary_confirmation_shows_on_divergence() -> None:
    result = classify_auxiliary_confirmation(
        "BUY", "BUY", auxiliary("WTI", "SELL")
    )

    assert result["auxiliary_alignment"] == "DIVERGENT"
    assert result["auxiliary_visibility"] == "SHOW"


def test_auxiliary_confirmation_shows_new_cross_or_formal_weakness() -> None:
    new_cross = classify_auxiliary_confirmation(
        "BUY", "BUY", auxiliary("GLD", "BUY", "NEW")
    )
    weak = classify_auxiliary_confirmation(
        "SELL", "SELL", auxiliary("WTI", "SELL")
    )

    assert new_cross["auxiliary_visibility"] == "SHOW"
    assert weak["auxiliary_visibility"] == "SHOW"
