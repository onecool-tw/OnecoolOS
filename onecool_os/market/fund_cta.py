"""Fund-NAV CTA confirmation built on the shared Onecool CTA engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from onecool_os.market.etf_cta import (
    CrossSignal,
    DailyBar,
    ETFCTAError,
    calculate_cta,
)
from onecool_os.market.fund_alpha import FUND_WATCHLIST, FundNav


@dataclass(frozen=True)
class FundCTAResult:
    """Auditable fund CTA result; unknown never means a bearish signal."""

    fund_code: str
    fund_name: str
    benchmark_etf: str
    theme: str
    fund_nav_as_of: str | None
    nav: float | None
    daily_50ma: float | None
    daily_200ma: float | None
    weekly_30ma: float | None
    weekly_50ma: float | None
    fund_cta: str
    data_quality: str
    nav_observations: int
    reason: str
    benchmark_cta: str | None = None
    signal_alignment: str = "unknown"
    daily_cross: CrossSignal | None = None
    weekly_cross: CrossSignal | None = None
    technical_conclusion: str = "UNKNOWN"
    dca_action: str = "DATA_REVIEW"
    auxiliary_symbol: str | None = None
    auxiliary_cta: str | None = None
    auxiliary_alignment: str = "not_applicable"
    auxiliary_visibility: str = "HIDE"
    auxiliary_reason: str = "No auxiliary confirmation configured."


def calculate_fund_cta(
    fund_code: str,
    history: Iterable[FundNav],
    *,
    benchmark_cta: str | None = None,
    auxiliary_signal: dict[str, Any] | None = None,
) -> FundCTAResult:
    """Calculate a fund NAV CTA with the exact shared CTA implementation."""

    navs = sorted(history, key=lambda item: item.nav_date)
    name, benchmark, theme = FUND_WATCHLIST[fund_code]
    latest = navs[-1] if navs else None
    bars = [
        DailyBar(
            trading_date=item.nav_date,
            open=item.nav,
            high=item.nav,
            low=item.nav,
            close=item.nav,
            volume=0,
            adjusted_close=item.nav,
            source=item.source,
        )
        for item in navs
    ]
    try:
        cta = calculate_cta(fund_code, bars)
    except ETFCTAError as exc:
        auxiliary = classify_auxiliary_confirmation(
            benchmark_cta, "UNKNOWN", auxiliary_signal
        )
        return FundCTAResult(
            fund_code=fund_code,
            fund_name=name,
            benchmark_etf=benchmark,
            theme=theme,
            fund_nav_as_of=latest.nav_date.isoformat() if latest else None,
            nav=latest.nav if latest else None,
            daily_50ma=None,
            daily_200ma=None,
            weekly_30ma=None,
            weekly_50ma=None,
            fund_cta="UNKNOWN",
            data_quality="insufficient_history",
            nav_observations=len(navs),
            reason=str(exc),
            benchmark_cta=benchmark_cta,
            technical_conclusion="UNKNOWN",
            dca_action="DATA_REVIEW",
            **auxiliary,
        )

    auxiliary = classify_auxiliary_confirmation(
        benchmark_cta, cta.cta, auxiliary_signal
    )
    return FundCTAResult(
        fund_code=fund_code,
        fund_name=name,
        benchmark_etf=benchmark,
        theme=theme,
        fund_nav_as_of=cta.as_of,
        nav=cta.price,
        daily_50ma=cta.daily_50ma,
        daily_200ma=cta.daily_200ma,
        weekly_30ma=cta.weekly_30ma,
        weekly_50ma=cta.weekly_50ma,
        fund_cta=cta.cta,
        data_quality="sufficient_history",
        nav_observations=len(navs),
        reason=cta.reason,
        benchmark_cta=benchmark_cta,
        signal_alignment=classify_signal_alignment(benchmark_cta, cta.cta),
        daily_cross=cta.daily_cross,
        weekly_cross=cta.weekly_cross,
        technical_conclusion=technical_conclusion(benchmark_cta, cta.cta),
        dca_action=dca_action(benchmark_cta, cta.cta),
        **auxiliary,
    )


def classify_auxiliary_confirmation(
    benchmark_cta: str | None,
    fund_cta: str,
    auxiliary_signal: dict[str, Any] | None,
) -> dict[str, str | None]:
    """Show GLD/WTI only when they add decision-relevant context."""

    if not auxiliary_signal:
        return {
            "auxiliary_symbol": None,
            "auxiliary_cta": None,
            "auxiliary_alignment": "not_applicable",
            "auxiliary_visibility": "HIDE",
            "auxiliary_reason": "No auxiliary confirmation configured.",
        }
    symbol = auxiliary_signal.get("symbol")
    auxiliary_cta = auxiliary_signal.get("cta")
    strong = {"BUY", "HOLD"}
    weak = {"WATCH", "SELL"}
    divergent = (
        benchmark_cta in strong and auxiliary_cta in weak
    ) or (
        benchmark_cta in weak and auxiliary_cta in strong
    )
    phases = {
        (auxiliary_signal.get(period) or {}).get("phase")
        for period in ("daily_cross", "weekly_cross")
    }
    new_cross = bool(phases & {"NEW", "CONFIRMED"})
    formal_weakness = benchmark_cta in weak or fund_cta in weak
    visibility = "SHOW" if divergent or new_cross or formal_weakness else "HIDE"
    if divergent:
        alignment = "DIVERGENT"
        reason = "Auxiliary commodity trend diverges from the formal benchmark."
    elif auxiliary_cta in {"BUY", "HOLD", "WATCH", "SELL"}:
        alignment = "CONFIRMS"
        reason = "Auxiliary commodity trend confirms the formal benchmark."
    else:
        alignment = "UNKNOWN"
        reason = "Auxiliary commodity signal is unavailable."
    if new_cross:
        reason += " A new or confirming auxiliary crossover requires disclosure."
    elif formal_weakness:
        reason += " Formal fund/benchmark weakness requires auxiliary context."
    return {
        "auxiliary_symbol": str(symbol) if symbol else None,
        "auxiliary_cta": str(auxiliary_cta) if auxiliary_cta else None,
        "auxiliary_alignment": alignment,
        "auxiliary_visibility": visibility,
        "auxiliary_reason": reason,
    }


def technical_conclusion(benchmark_cta: str | None, fund_cta: str) -> str:
    """Keep the technical verdict separate from the DCA disposition."""

    if benchmark_cta == "SELL" and fund_cta == "SELL":
        return "SELL"
    return fund_cta if fund_cta in {"BUY", "HOLD", "WATCH", "SELL"} else "UNKNOWN"


def dca_action(benchmark_cta: str | None, fund_cta: str) -> str:
    """A technical SELL triggers review; it never implies automatic redemption."""

    if benchmark_cta == "SELL" and fund_cta == "SELL":
        return "REVIEW_DCA"
    if benchmark_cta not in {"BUY", "HOLD", "WATCH", "SELL"}:
        return "DATA_REVIEW"
    return "MAINTAIN_DCA"


def classify_signal_alignment(
    benchmark_cta: str | None, fund_cta: str
) -> str:
    """Describe ETF/fund agreement without creating a second CTA rule."""

    if benchmark_cta not in {"BUY", "HOLD", "WATCH", "SELL"}:
        return "unknown"
    if fund_cta not in {"BUY", "HOLD", "WATCH", "SELL"}:
        return "unknown"
    if benchmark_cta == "BUY" and fund_cta == "BUY":
        return "confirmed_strength"
    if benchmark_cta == "BUY" and fund_cta in {"WATCH", "SELL"}:
        return "fund_lagging_strong_market"
    if benchmark_cta in {"WATCH", "SELL"} and fund_cta == "BUY":
        return "fund_resilient_weak_market"
    if benchmark_cta in {"WATCH", "SELL"} and fund_cta in {"WATCH", "SELL"}:
        return "joint_weakness"
    return "mixed_or_neutral"


def fund_cta_payload(results: Iterable[FundCTAResult]) -> dict[str, Any]:
    """Build the cache consumed by Fund Intelligence without provider calls."""

    return {
        "schema_version": "1.4",
        "metric": "Onecool Fund NAV CTA",
        "source": "OnecoolOS committed fund NAV history",
        "engine": "shared_onecool_cta_engine",
        "decision_layers": {
            "technical_conclusion": "trend verdict; SELL is explicit when fund and benchmark are both SELL",
            "dca_action": "periodic-investment disposition; REVIEW_DCA is not automatic redemption",
        },
        "auxiliary_confirmation": {
            "gold": "GLD confirms RING",
            "energy": "WTI confirms IXC",
            "visibility": "SHOW only for divergence, NEW/CONFIRMED crossover, or formal weakness",
            "decision_use": "context only; never independently changes DCA action",
        },
        "method": {
            "daily": ["fund_nav", "SMA50", "SMA200"],
            "weekly": ["last_published_nav", "SMA30", "SMA50"],
            "rules": "Onecool CTA v2 weekly crossover priority",
            "cross_detection": {
                "daily": "SMA50 crosses SMA200",
                "weekly": "SMA30 crosses SMA50",
                "delta_rule": "cross_status is non-NONE only on the crossing period",
                "priority": "weekly crossover > daily crossover > alignment",
                "phase": "NEW, CONFIRMED, ACTIVE, AGING",
            },
        },
        "results": [asdict(item) for item in results],
    }
