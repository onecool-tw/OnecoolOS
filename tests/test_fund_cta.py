from datetime import date, timedelta

from onecool_os.market.fund_alpha import FundNav
from onecool_os.market.fund_cta import (
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
    assert payload["schema_version"] == "1.4"
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


def test_joint_sell_is_explicit_but_does_not_auto_redeem() -> None:
    assert technical_conclusion("SELL", "SELL") == "SELL"
    assert dca_action("SELL", "SELL") == "REVIEW_DCA"


def test_non_joint_sell_keeps_dca_separate() -> None:
    assert technical_conclusion("SELL", "WATCH") == "WATCH"
    assert dca_action("SELL", "WATCH") == "MAINTAIN_DCA"
    assert dca_action(None, "SELL") == "DATA_REVIEW"


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
