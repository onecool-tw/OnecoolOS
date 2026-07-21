from datetime import date, timedelta

from onecool_os.market.fund_alpha import FundNav
from onecool_os.market.fund_cta import (
    calculate_fund_cta,
    classify_signal_alignment,
    fund_cta_payload,
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


def test_fund_cta_reuses_shared_engine_for_buy() -> None:
    result = calculate_fund_cta(
        "A10124", nav_history(400), benchmark_cta="BUY"
    )

    assert result.fund_cta == "BUY"
    assert result.data_quality == "sufficient_history"
    assert result.signal_alignment == "confirmed_strength"
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
    assert payload["schema_version"] == "1.2"
    assert payload["method"]["cross_detection"]["priority"].startswith(
        "weekly crossover"
    )
    assert payload["results"][0]["weekly_cross"]["phase"] in {
        "NEW", "CONFIRMED", "ACTIVE", "AGING"
    }
    assert (
        payload["method"]["cross_detection"]["daily"]
        == "SMA50 crosses SMA200"
    )
    assert payload["results"][0]["fund_code"] == "A10124"
