"""Cached Onecool Market Dashboard built with the shared CTA engine."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from math import isfinite
from pathlib import Path
from typing import Any, Iterable

from onecool_os.market.etf_cta import (
    CTAResult,
    CrossSignal,
    DailyBar,
    read_history,
)


@dataclass(frozen=True)
class MarketSymbol:
    """One dashboard symbol and its provider-specific identifier."""

    symbol: str
    provider_symbol: str
    market: str
    theme: str


US_INDEX_CTA_PROXIES = {
    "S&P 500": "SPY",
    "Nasdaq": "QQQ",
    "Dow": "DIA",
    "Russell 2000": "RUSSELL_2000",
}

COUNTRY_INDEX_CTA_PROXIES = {
    "Japan": "1306",
    "South Korea": "069500",
}

US_PORTFOLIO_CTA_SYMBOLS = ("BABA", "XYZ", "QRVO", "RH", "UPBD")

DASHBOARD_ACTION_REFRESH_GROUPS = {
    "group_a": ("SPY", "QQQ", "DIA"),
    "group_b": ("SOXX", "NVDA"),
}


MARKET_SYMBOLS = (
    MarketSymbol("SPY", "SPY", "US", "broad_market"),
    MarketSymbol("QQQ", "QQQ", "US", "growth_ai"),
    MarketSymbol("RUSSELL_2000", "^RUT", "US", "small_cap"),
    MarketSymbol("DIA", "DIA", "US", "blue_chip"),
    MarketSymbol("SOXX", "SOXX", "US", "semiconductor"),
    MarketSymbol("NVDA", "NVDA", "US", "ai"),
    MarketSymbol("1306", "1306.T", "JP", "broad_market"),
    MarketSymbol("069500", "069500.KS", "KR", "broad_market"),
    MarketSymbol("BABA", "BABA", "US", "portfolio"),
    MarketSymbol("XYZ", "XYZ", "US", "portfolio"),
    MarketSymbol("QRVO", "QRVO", "US", "portfolio"),
    MarketSymbol("RH", "RH", "US", "portfolio"),
    MarketSymbol("UPBD", "UPBD", "US", "portfolio"),
    MarketSymbol("0050", "0050.TW", "TW", "broad_market"),
    MarketSymbol("2330", "2330.TW", "TW", "semiconductor_ai"),
    MarketSymbol("VIX", "^VIX", "CONTEXT", "volatility"),
    MarketSymbol("DXY", "DX-Y.NYB", "CONTEXT", "us_dollar"),
    MarketSymbol("US30Y", "^TYX", "CONTEXT", "us_30y_yield"),
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
    daily_cross: CrossSignal | None = None
    weekly_cross: CrossSignal | None = None


def dashboard_record(config: MarketSymbol, result: CTAResult) -> MarketCTA:
    """Adapt one shared CTA result without introducing another CTA engine."""

    numeric_fields = {
        "price": result.price,
        "daily_50ma": result.daily_50ma,
        "daily_200ma": result.daily_200ma,
        "weekly_30ma": result.weekly_30ma,
        "weekly_50ma": result.weekly_50ma,
    }
    invalid = [name for name, value in numeric_fields.items() if not isfinite(value)]
    if invalid:
        raise ValueError(
            f"{config.symbol} contains non-finite CTA fields: "
            + ", ".join(invalid)
        )

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
        daily_cross=result.daily_cross,
        weekly_cross=result.weekly_cross,
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
    summary_items = [
        item for item in items.values() if item.symbol not in US_PORTFOLIO_CTA_SYMBOLS
    ]
    counts = {
        signal: sum(item.cta == signal for item in summary_items)
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
    """Build the GitHub-cached SSOT payload after passing the US date gate."""

    values = list(records)
    expected_as_of = _validate_us_index_cta_dates(values)
    country_as_of = _validate_country_index_cta_dates(values)
    portfolio_as_of = _validate_us_portfolio_cta_dates(values, expected_as_of)
    generated_at = datetime.now(UTC).isoformat()
    return {
        "schema_version": "1.8",
        "module": "Onecool Market Dashboard",
        "generated_at": generated_at,
        "expected_as_of": expected_as_of,
        "data_status": "READY",
        "last_successful_update_at": generated_at,
        "index_cta_basis": {
            "method": "ETF/index proxies; shared CTA engine",
            "mappings": US_INDEX_CTA_PROXIES,
        },
        "country_index_cta_basis": {
            "method": "Local-listed country ETFs; shared CTA engine",
            "mappings": COUNTRY_INDEX_CTA_PROXIES,
            "as_of": country_as_of,
            "currency_policy": "local-market closing prices in JPY and KRW",
        },
        "portfolio_cta_basis": {
            "method": "Adjusted-close histories; shared CTA engine",
            "symbols": list(US_PORTFOLIO_CTA_SYMBOLS),
            "as_of": portfolio_as_of,
        },
        "provider": "yahoo_finance_raw_primary",
        "provider_by_symbol": {
            item.symbol: "yahoo_finance_raw" for item in MARKET_SYMBOLS
        },
        "history_bootstrap_provider": (
            "yahoo_finance_raw_with_actions_once_when_missing_or_migrating"
        ),
        "cache_policy": "scheduled_writer_only; consumers_read_github_cache",
        "cta_engine": "onecool_os.market.etf_cta.calculate_cta",
        "summary_method": "deterministic CTA aggregation; no forecast",
        "summary": market_summary(values),
        "results": [asdict(item) for item in values],
    }


def _validate_us_index_cta_dates(records: Iterable[MarketCTA]) -> str:
    """Require all four US CTA proxies to use one complete market date."""

    items = {item.symbol: item for item in records}
    missing = [
        symbol for symbol in US_INDEX_CTA_PROXIES.values() if symbol not in items
    ]
    if missing:
        raise ValueError(
            "Market Dashboard is missing US CTA proxies: " + ", ".join(missing)
        )
    dates = {items[symbol].as_of for symbol in US_INDEX_CTA_PROXIES.values()}
    if len(dates) != 1:
        details = ", ".join(
            f"{symbol}={items[symbol].as_of}"
            for symbol in US_INDEX_CTA_PROXIES.values()
        )
        raise ValueError("US CTA proxy dates are inconsistent: " + details)
    return dates.pop()


def _validate_country_index_cta_dates(
    records: Iterable[MarketCTA],
) -> dict[str, str]:
    """Record each local market date without forcing cross-market alignment."""

    items = {item.symbol: item for item in records}
    missing = [
        symbol for symbol in COUNTRY_INDEX_CTA_PROXIES.values()
        if symbol not in items
    ]
    if missing:
        raise ValueError(
            "Market Dashboard is missing country CTA proxies: "
            + ", ".join(missing)
        )
    return {
        country: items[symbol].as_of
        for country, symbol in COUNTRY_INDEX_CTA_PROXIES.items()
    }


def _validate_us_portfolio_cta_dates(
    records: Iterable[MarketCTA], expected_as_of: str
) -> str:
    """Require every US portfolio CTA to use the complete US market date."""

    items = {item.symbol: item for item in records}
    missing = [
        symbol for symbol in US_PORTFOLIO_CTA_SYMBOLS if symbol not in items
    ]
    if missing:
        raise ValueError(
            "Market Dashboard is missing US portfolio CTA symbols: "
            + ", ".join(missing)
        )
    dates = {items[symbol].as_of for symbol in US_PORTFOLIO_CTA_SYMBOLS}
    if dates != {expected_as_of}:
        details = ", ".join(
            f"{symbol}={items[symbol].as_of}"
            for symbol in US_PORTFOLIO_CTA_SYMBOLS
        )
        raise ValueError(
            "US portfolio CTA dates must match the US market date "
            f"{expected_as_of}: {details}"
        )
    return expected_as_of


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
