"""Cached Onecool Market Dashboard built with the shared CTA engine."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from onecool_os.market.etf_cta import CTAResult, DailyBar, read_history


@dataclass(frozen=True)
class MarketSymbol:
    """One dashboard symbol and its provider-specific identifier."""

    symbol: str
    provider_symbol: str
    market: str
    theme: str


MARKET_SYMBOLS = (
    MarketSymbol("SPY", "SPY", "US", "broad_market"),
    MarketSymbol("QQQ", "QQQ", "US", "growth_ai"),
    MarketSymbol("DIA", "DIA", "US", "blue_chip"),
    MarketSymbol("SOXX", "SOXX", "US", "semiconductor"),
    MarketSymbol("NVDA", "NVDA", "US", "ai"),
    MarketSymbol("0050", "0050.TW", "TW", "broad_market"),
    MarketSymbol("2330", "2330.TW", "TW", "semiconductor_ai"),
)


@dataclass(frozen=True)
class MarketCTA:
    """A dashboard record derived from the shared CTA result."""

    symbol: str
    provider_symbol: str
    market: str
    theme: str
    as_of: str
    current_price: float
    sma50: float
    sma200: float
    weekly_ma30: float
    weekly_ma50: float
    trend: str
    cta: str
    confidence: int
    reason: str


def dashboard_record(config: MarketSymbol, result: CTAResult) -> MarketCTA:
    """Adapt one shared CTA result without introducing another CTA engine."""

    bullish = sum(
        (
            result.price > result.daily_50ma,
            result.daily_50ma > result.daily_200ma,
            result.price > result.weekly_30ma,
            result.weekly_30ma > result.weekly_50ma,
        )
    )
    bearish = 4 - bullish
    if result.daily_50ma > result.daily_200ma and result.weekly_30ma > result.weekly_50ma:
        trend = "BULLISH"
    elif result.daily_50ma < result.daily_200ma and result.weekly_30ma < result.weekly_50ma:
        trend = "BEARISH"
    else:
        trend = "MIXED"
    confidence = round(max(bullish, bearish) / 4 * 100)
    return MarketCTA(
        symbol=config.symbol,
        provider_symbol=config.provider_symbol,
        market=config.market,
        theme=config.theme,
        as_of=result.as_of,
        current_price=result.price,
        sma50=result.daily_50ma,
        sma200=result.daily_200ma,
        weekly_ma30=result.weekly_30ma,
        weekly_ma50=result.weekly_50ma,
        trend=trend,
        cta=result.cta,
        confidence=confidence,
        reason=result.reason,
    )


def market_summary(records: Iterable[MarketCTA]) -> dict[str, str]:
    """Create a deterministic summary from CTA records only."""

    items = {item.symbol: item for item in records}
    us = [items[symbol] for symbol in ("SPY", "QQQ", "DIA", "SOXX", "NVDA")]
    tw = [items[symbol] for symbol in ("0050", "2330")]
    ai = [items[symbol] for symbol in ("QQQ", "SOXX", "NVDA")]
    us_trend = _aggregate_trend(us)
    tw_trend = _aggregate_trend(tw)
    if all(item.trend == "BULLISH" and item.cta != "SELL" for item in ai):
        ai_line = "CONFIRMED"
    elif sum(item.trend == "BEARISH" or item.cta == "SELL" for item in ai) >= 2:
        ai_line = "WEAK"
    else:
        ai_line = "MIXED"
    synchronization = (
        "SYNCHRONIZED"
        if us_trend == tw_trend and us_trend != "MIXED"
        else "DIVERGENT_OR_MIXED"
    )
    counts = {
        signal: sum(item.cta == signal for item in items.values())
        for signal in ("BUY", "HOLD", "WATCH", "SELL")
    }
    return {
        "us_market_trend": us_trend,
        "ai_market_line": ai_line,
        "taiwan_market_trend": tw_trend,
        "us_taiwan_synchronization": synchronization,
        "market_cta_summary": ", ".join(
            f"{signal}={counts[signal]}"
            for signal in ("BUY", "HOLD", "WATCH", "SELL")
        ),
    }


def build_dashboard_payload(records: Iterable[MarketCTA]) -> dict[str, Any]:
    """Build the GitHub-cached SSOT payload."""

    values = list(records)
    return {
        "schema_version": "1.1",
        "module": "Onecool Market Dashboard",
        "generated_at": datetime.now(UTC).isoformat(),
        "provider": "alpha_vantage",
        "history_bootstrap_provider": "yahoo_finance_once_when_missing",
        "cache_policy": "scheduled_writer_only; consumers_read_github_cache",
        "cta_engine": "onecool_os.market.etf_cta.calculate_cta",
        "summary_method": "deterministic CTA aggregation; no forecast",
        "summary": market_summary(values),
        "results": [asdict(item) for item in values],
    }


def load_latest_dashboard(root: Path) -> dict[str, Any] | None:
    """Read the latest successful cache without calling a provider."""

    path = root / "data" / "market" / "dashboard" / "dashboard_latest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_dashboard_histories(root: Path) -> dict[str, list[DailyBar]]:
    """Read all committed dashboard histories."""

    directory = root / "data" / "market" / "dashboard" / "history"
    return {
        item.symbol: read_history(directory / f"{item.symbol}.csv")
        for item in MARKET_SYMBOLS
    }


def _aggregate_trend(records: Iterable[MarketCTA]) -> str:
    values = list(records)
    bullish = sum(item.trend == "BULLISH" for item in values)
    bearish = sum(item.trend == "BEARISH" for item in values)
    threshold = len(values) // 2 + 1
    if bullish >= threshold:
        return "BULLISH"
    if bearish >= threshold:
        return "BEARISH"
    return "MIXED"
