"""Reproducible Onecool proxy scores for the US portfolio.

These are not IBD ratings.  The CANSLIM proxy combines a dated, reviewed
fundamental baseline with daily price/volume and market data.  The Minervini
proxy is recalculated entirely from the same adjusted-close histories used by
the Market Dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Iterable

from onecool_os.market.etf_cta import DailyBar


SCORE_VERSION = "onecool_us_portfolio_dual_v1"


@dataclass(frozen=True)
class FundamentalSnapshot:
    symbol: str
    as_of: str
    quality_score: int
    source: str
    source_url: str


# Reviewed fundamental baselines are deliberately dated.  They change only
# after a new filing/earnings release is validated; daily market components do
# not pretend that quarterly fundamentals changed every session.
FUNDAMENTAL_SNAPSHOTS = {
    "BABA": FundamentalSnapshot(
        "BABA", "2026-05-13", 42,
        "Alibaba FY2026 results (company release)",
        "https://www.alibabagroup.com/en-US/document-1991237455038119936",
    ),
    "XYZ": FundamentalSnapshot(
        "XYZ", "2026-05-07", 78,
        "Block Q1 2026 Form 10-Q",
        "https://www.sec.gov/Archives/edgar/data/1512673/000162828026032200/0001628280-26-032200-index.htm",
    ),
    "QRVO": FundamentalSnapshot(
        "QRVO", "2026-05-05", 52,
        "Qorvo FY2026 Q4 results (company release)",
        "https://www.qorvo.com/about/news-events/news-releases/2026/qorvo-announces-fiscal-2026-fourth-quarter-financial-results",
    ),
    "RH": FundamentalSnapshot(
        "RH", "2026-06-11", 32,
        "RH Q1 2026 results (company filing)",
        "https://ir.rh.com/financials-filings/sec-filings/content/0001104659-26-072941/rh-20260611xex99d2.htm",
    ),
    "UPBD": FundamentalSnapshot(
        "UPBD", "2026-07-30", 64,
        "Upbound Q2 2026 results (company filing)",
        "https://investor.upbound.com/node/24801/html",
    ),
}


def build_portfolio_score_payload(
    histories: dict[str, list[DailyBar]],
    *,
    expected_as_of: str,
) -> dict:
    """Calculate same-cutoff CANSLIM and Minervini proxy scores."""

    required = set(FUNDAMENTAL_SNAPSHOTS) | {"SPY"}
    missing = sorted(required - histories.keys())
    if missing:
        raise ValueError("dual-system histories missing: " + ", ".join(missing))

    expected = date.fromisoformat(expected_as_of)
    for symbol in sorted(required):
        _validate_history(symbol, histories[symbol], expected)

    spy = histories["SPY"]
    results = []
    for symbol, snapshot in FUNDAMENTAL_SNAPSHOTS.items():
        if date.fromisoformat(snapshot.as_of) > expected:
            raise ValueError(
                f"{symbol} fundamentals date {snapshot.as_of} is after "
                f"price date {expected_as_of}"
            )
        history = histories[symbol]
        technical = _technical_metrics(history, spy)
        canslim_components = {
            "fundamentals_45": round(snapshot.quality_score * 0.45, 2),
            "new_high_momentum_10": round(
                _scaled(technical["return_126"], -0.20, 0.40, 10), 2
            ),
            "supply_demand_10": round(
                technical["up_volume_ratio_20"] * 10, 2
            ),
            "leadership_15": round(
                _scaled(technical["relative_126"], -0.20, 0.20, 15), 2
            ),
            "market_20": technical["market_points"],
        }
        canslim = round(sum(canslim_components.values()))

        trend_points = 8 * sum(technical["trend_template_checks"].values())
        minervini_components = {
            "trend_template_64": trend_points,
            "relative_strength_20": round(
                _scaled(technical["relative_126"], -0.20, 0.20, 20), 2
            ),
            "price_volume_quality_16": technical["quality_points"],
        }
        minervini = round(sum(minervini_components.values()))
        results.append(
            {
                "symbol": symbol,
                "price_as_of": expected_as_of,
                "fundamentals_as_of": snapshot.as_of,
                "price_basis": "locally_adjusted_close",
                "validation_status": "PASSED",
                "canslim_score": _bounded_score(canslim),
                "minervini_score": _bounded_score(minervini),
                "canslim_components": canslim_components,
                "minervini_components": minervini_components,
                "fundamental_source": snapshot.source,
                "fundamental_source_url": snapshot.source_url,
            }
        )

    return {
        "schema_version": "1.0",
        "score_version": SCORE_VERSION,
        "classification": "Onecool proxy scores; not IBD official ratings",
        "expected_as_of": expected_as_of,
        "data_status": "READY",
        "price_basis": "locally_adjusted_close",
        "fundamentals_policy": (
            "dated reviewed snapshot; refresh only after validated filing"
        ),
        "results": results,
    }


def _validate_history(symbol: str, bars: list[DailyBar], expected: date) -> None:
    if len(bars) < 252:
        raise ValueError(f"{symbol} needs at least 252 daily observations")
    if bars[-1].trading_date != expected:
        raise ValueError(
            f"{symbol} price date {bars[-1].trading_date} != {expected}"
        )
    dates = [bar.trading_date for bar in bars]
    if dates != sorted(set(dates)):
        raise ValueError(f"{symbol} has duplicate or unsorted trading dates")
    if any(
        bar.adjusted_close is None
        or not isfinite(float(bar.adjusted_close))
        or float(bar.adjusted_close) <= 0
        or bar.volume < 0
        for bar in bars
    ):
        raise ValueError(f"{symbol} failed OHLCV/adjusted-close validation")


def _technical_metrics(history: list[DailyBar], spy: list[DailyBar]) -> dict:
    closes = [float(bar.adjusted_close) for bar in history]
    volumes = [bar.volume for bar in history]
    spy_closes = [float(bar.adjusted_close) for bar in spy]
    price = closes[-1]
    sma20 = _mean(closes[-20:])
    sma50 = _mean(closes[-50:])
    sma150 = _mean(closes[-150:])
    sma200 = _mean(closes[-200:])
    sma200_20d_ago = _mean(closes[-220:-20])
    high_52 = max(closes[-252:])
    low_52 = min(closes[-252:])
    return_126 = price / closes[-127] - 1
    spy_return_126 = spy_closes[-1] / spy_closes[-127] - 1
    relative_126 = (1 + return_126) / (1 + spy_return_126) - 1
    recent = list(zip(closes[-20:], volumes[-20:]))
    up_volume = sum(
        volume
        for index, (_, volume) in enumerate(recent[1:], 1)
        if recent[index][0] > recent[index - 1][0]
    )
    total_volume = sum(volume for _, volume in recent[1:])
    up_volume_ratio = up_volume / total_volume if total_volume else 0.5

    spy50 = _mean(spy_closes[-50:])
    spy200 = _mean(spy_closes[-200:])
    market_points = 5 * sum(
        (
            spy_closes[-1] > spy50,
            spy_closes[-1] > spy200,
            spy50 > spy200,
            spy_closes[-1] > spy_closes[-21],
        )
    )
    checks = {
        "price_above_sma50": price > sma50,
        "price_above_sma150": price > sma150,
        "price_above_sma200": price > sma200,
        "sma50_above_sma150": sma50 > sma150,
        "sma150_above_sma200": sma150 > sma200,
        "sma200_rising": sma200 > sma200_20d_ago,
        "price_30pct_above_52w_low": price >= low_52 * 1.30,
        "price_within_25pct_of_52w_high": price >= high_52 * 0.75,
    }
    quality_points = 4 * sum(
        (
            price > sma20,
            sma20 > sma50,
            up_volume_ratio >= 0.50,
            price >= high_52 * 0.85,
        )
    )
    return {
        "return_126": return_126,
        "relative_126": relative_126,
        "up_volume_ratio_20": up_volume_ratio,
        "market_points": market_points,
        "trend_template_checks": checks,
        "quality_points": quality_points,
    }


def _mean(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items)


def _scaled(value: float, floor: float, ceiling: float, points: int) -> float:
    return max(0.0, min(float(points), (value - floor) / (ceiling - floor) * points))


def _bounded_score(value: int) -> int:
    return max(0, min(100, value))
