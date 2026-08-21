"""Daily, reproducible US breakout candidate scan.

The scan is deliberately separate from the CTA engine.  It consumes adjusted
daily bars with one common cutoff, validates every candidate, and publishes a
dated Top 5 artifact.  Scores are Onecool proxies, not IBD ratings.
"""

from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from math import isfinite
from typing import Iterable

from onecool_os.market.etf_cta import DailyBar


SCAN_VERSION = "onecool_us_breakout_v1"
MIN_TECHNICAL_CONFIDENCE = 90
CANSLIM_PASS = 70
MINERVINI_PASS = 80

# A stable, liquid US leadership universe.  Membership is versioned in code so
# a historical result is reproducible and ticker mappings cannot drift silently.
US_BREAKOUT_UNIVERSE = (
    "AAPL", "ABBV", "ABNB", "ADBE", "ADI", "AMD", "AMAT", "AMGN",
    "AMZN", "ANET", "APP", "AVGO", "AXP", "BA", "BKNG", "CAT",
    "CEG", "CLS", "COIN", "COST", "CRDO", "CRWD", "CSCO", "CVX",
    "DDOG", "DE", "DELL", "DUOL", "ETN", "GE", "GEV", "GILD",
    "GOOGL", "GS", "HOOD", "IBM", "JPM", "KLAC", "LLY", "LRCX",
    "MA", "META", "MPWR", "MRVL", "MS", "MSFT", "MU", "NFLX",
    "NOW", "NVDA", "ORCL", "PANW", "PLTR", "QCOM", "RTX", "SNDK",
    "SNOW", "SPOT", "SYM", "THC", "TSM", "TSLA", "UBER", "V",
    "VRT", "WAB", "WDC", "WMT", "XYZ", "GD",
)


@dataclass(frozen=True)
class FundamentalMetrics:
    """Point-in-time fundamental inputs for the CANSLIM proxy."""

    as_of: str
    quarterly_eps_growth: float | None = None
    quarterly_revenue_growth: float | None = None
    annual_eps_growth: float | None = None
    institutional_holders_available: bool = False


@dataclass(frozen=True)
class SecurityIdentity:
    company_name: str
    security_type: str = "COMMON_STOCK"


US_SECURITY_MASTER = {
    "AAPL": SecurityIdentity("Apple Inc."),
    "ABBV": SecurityIdentity("AbbVie Inc."),
    "ABNB": SecurityIdentity("Airbnb, Inc."),
    "ADBE": SecurityIdentity("Adobe Inc."),
    "ADI": SecurityIdentity("Analog Devices, Inc."),
    "AMD": SecurityIdentity("Advanced Micro Devices, Inc."),
    "AMAT": SecurityIdentity("Applied Materials, Inc."),
    "AMGN": SecurityIdentity("Amgen Inc."),
    "AMZN": SecurityIdentity("Amazon.com, Inc."),
    "ANET": SecurityIdentity("Arista Networks, Inc."),
    "APP": SecurityIdentity("AppLovin Corporation"),
    "AVGO": SecurityIdentity("Broadcom Inc."),
    "AXP": SecurityIdentity("American Express Company"),
    "BA": SecurityIdentity("The Boeing Company"),
    "BKNG": SecurityIdentity("Booking Holdings Inc."),
    "CAT": SecurityIdentity("Caterpillar Inc."),
    "CEG": SecurityIdentity("Constellation Energy Corporation"),
    "CLS": SecurityIdentity("Celestica Inc.", "FOREIGN_ORDINARY"),
    "COIN": SecurityIdentity("Coinbase Global, Inc."),
    "COST": SecurityIdentity("Costco Wholesale Corporation"),
    "CRDO": SecurityIdentity("Credo Technology Group Holding Ltd.", "FOREIGN_ORDINARY"),
    "CRWD": SecurityIdentity("CrowdStrike Holdings, Inc."),
    "CSCO": SecurityIdentity("Cisco Systems, Inc."),
    "CVX": SecurityIdentity("Chevron Corporation"),
    "DDOG": SecurityIdentity("Datadog, Inc."),
    "DE": SecurityIdentity("Deere & Company"),
    "DELL": SecurityIdentity("Dell Technologies Inc."),
    "DUOL": SecurityIdentity("Duolingo, Inc."),
    "ETN": SecurityIdentity("Eaton Corporation plc", "FOREIGN_ORDINARY"),
    "GE": SecurityIdentity("GE Aerospace"),
    "GEV": SecurityIdentity("GE Vernova Inc."),
    "GILD": SecurityIdentity("Gilead Sciences, Inc."),
    "GOOGL": SecurityIdentity("Alphabet Inc. Class A"),
    "GS": SecurityIdentity("The Goldman Sachs Group, Inc."),
    "HOOD": SecurityIdentity("Robinhood Markets, Inc."),
    "IBM": SecurityIdentity("International Business Machines Corporation"),
    "JPM": SecurityIdentity("JPMorgan Chase & Co."),
    "KLAC": SecurityIdentity("KLA Corporation"),
    "LLY": SecurityIdentity("Eli Lilly and Company"),
    "LRCX": SecurityIdentity("Lam Research Corporation"),
    "MA": SecurityIdentity("Mastercard Incorporated"),
    "META": SecurityIdentity("Meta Platforms, Inc."),
    "MPWR": SecurityIdentity("Monolithic Power Systems, Inc."),
    "MRVL": SecurityIdentity("Marvell Technology, Inc.", "FOREIGN_ORDINARY"),
    "MS": SecurityIdentity("Morgan Stanley"),
    "MSFT": SecurityIdentity("Microsoft Corporation"),
    "MU": SecurityIdentity("Micron Technology, Inc."),
    "NFLX": SecurityIdentity("Netflix, Inc."),
    "NOW": SecurityIdentity("ServiceNow, Inc."),
    "NVDA": SecurityIdentity("NVIDIA Corporation"),
    "ORCL": SecurityIdentity("Oracle Corporation"),
    "PANW": SecurityIdentity("Palo Alto Networks, Inc."),
    "PLTR": SecurityIdentity("Palantir Technologies Inc."),
    "QCOM": SecurityIdentity("QUALCOMM Incorporated"),
    "RTX": SecurityIdentity("RTX Corporation"),
    "SNDK": SecurityIdentity("Sandisk Corporation"),
    "SNOW": SecurityIdentity("Snowflake Inc."),
    "SPOT": SecurityIdentity("Spotify Technology S.A.", "FOREIGN_ORDINARY"),
    "SYM": SecurityIdentity("Symbotic Inc."),
    "THC": SecurityIdentity("Tenet Healthcare Corporation"),
    "TSM": SecurityIdentity("Taiwan Semiconductor Manufacturing Co., Ltd.", "ADR"),
    "TSLA": SecurityIdentity("Tesla, Inc."),
    "UBER": SecurityIdentity("Uber Technologies, Inc."),
    "V": SecurityIdentity("Visa Inc."),
    "VRT": SecurityIdentity("Vertiv Holdings Co"),
    "WAB": SecurityIdentity("Westinghouse Air Brake Technologies Corporation"),
    "WDC": SecurityIdentity("Western Digital Corporation"),
    "WMT": SecurityIdentity("Walmart Inc."),
    "XYZ": SecurityIdentity("Block, Inc."),
    "GD": SecurityIdentity("General Dynamics Corporation"),
}


def build_breakout_scan_payload(
    histories: dict[str, list[DailyBar]],
    fundamentals: dict[str, FundamentalMetrics],
    *,
    spy_history: list[DailyBar],
    expected_as_of: str,
    universe: Iterable[str] = US_BREAKOUT_UNIVERSE,
) -> dict:
    """Validate, score, rank, and return at most five candidates."""

    expected = date.fromisoformat(expected_as_of)
    universe = tuple(dict.fromkeys(universe))
    _validate_spy(spy_history, expected)
    results = []
    exclusions = []
    for symbol in universe:
        history = histories.get(symbol, [])
        confidence, reasons = technical_confidence(history, expected)
        fundamental = fundamentals.get(symbol)
        if confidence < MIN_TECHNICAL_CONFIDENCE or fundamental is None:
            exclusions.append({
                "symbol": symbol,
                "technical_confidence": confidence,
                "reason": (
                    "; ".join(reasons)
                    if confidence < MIN_TECHNICAL_CONFIDENCE
                    else "fundamental validation unavailable"
                ),
            })
            continue
        if date.fromisoformat(fundamental.as_of) > expected:
            exclusions.append({
                "symbol": symbol,
                "technical_confidence": confidence,
                "reason": "fundamental cutoff is after price cutoff",
            })
            continue
        metrics = _technical_metrics(history, spy_history)
        identity = US_SECURITY_MASTER.get(
            symbol, SecurityIdentity(symbol, "UNMAPPED_TEST_SYMBOL")
        )
        canslim = _canslim_score(metrics, fundamental)
        minervini = _minervini_score(metrics)
        status, trigger, breakout_quality = _candidate_state(metrics)
        rank_score = round(canslim * 0.45 + minervini * 0.45 + breakout_quality, 2)
        results.append({
            "symbol": symbol,
            "company_name": identity.company_name,
            "security_type": identity.security_type,
            "price_as_of": expected_as_of,
            "fundamentals_as_of": fundamental.as_of,
            "price_basis": "adjusted_close",
            "technical_confidence": confidence,
            "canslim_score": canslim,
            "minervini_score": minervini,
            "rank_score": rank_score,
            "status": status,
            "trigger": trigger,
            "formal_breakout": status == "BREAKOUT",
            "passes_dual_system": (
                canslim >= CANSLIM_PASS and minervini >= MINERVINI_PASS
            ),
        })

    if not results:
        raise ValueError(
            "Technical Data Validation Failed: no candidate has complete "
            "same-cutoff price and fundamental data"
        )
    ranked = sorted(
        results,
        key=lambda item: (
            item["formal_breakout"], item["passes_dual_system"],
            item["rank_score"], item["symbol"],
        ),
        reverse=True,
    )
    top5 = [item for item in ranked if item["status"] != "NOT_READY"][:5]
    return {
        "schema_version": "1.0",
        "scan_version": SCAN_VERSION,
        "classification": "Onecool proxy scores; not IBD official ratings",
        "expected_as_of": expected_as_of,
        "data_status": "READY",
        "price_basis": "adjusted_close",
        "universe_size": len(universe),
        "validated_count": len(results),
        "minimum_technical_confidence": MIN_TECHNICAL_CONFIDENCE,
        "formal_breakout_count": sum(item["formal_breakout"] for item in results),
        "top5": top5,
        "exclusions": exclusions,
    }


def fetch_yahoo_breakout_inputs(
    yfinance_module,
    *,
    expected_as_of: str,
    spy_history: list[DailyBar],
    universe: Iterable[str] = US_BREAKOUT_UNIVERSE,
    fundamental_shortlist_size: int = 10,
) -> tuple[dict[str, list[DailyBar]], dict[str, FundamentalMetrics]]:
    """Batch-download prices, then fetch fundamentals only for leaders.

    The two-stage design keeps the scheduled job API-safe: all symbols receive
    the same batch price cutoff, while only the strongest technical candidates
    incur a fundamentals request.
    """

    expected = date.fromisoformat(expected_as_of)
    symbols = tuple(dict.fromkeys(universe))
    frame = yfinance_module.download(
        list(symbols),
        period="2y",
        interval="1d",
        auto_adjust=True,
        actions=False,
        group_by="ticker",
        threads=True,
        progress=False,
    )
    histories = {
        symbol: _bars_from_download(frame, symbol, expected)
        for symbol in symbols
    }
    spy = spy_history
    _validate_spy(spy, expected)
    leaders = []
    for symbol in universe:
        history = histories.get(symbol, [])
        confidence, _ = technical_confidence(history, expected)
        if confidence < MIN_TECHNICAL_CONFIDENCE:
            continue
        metrics = _technical_metrics(history, spy)
        leaders.append((
            _minervini_score(metrics),
            metrics["price"] / metrics["high52"],
            symbol,
        ))
    shortlist = [
        symbol for _, _, symbol in sorted(leaders, reverse=True)
    ][:fundamental_shortlist_size]
    fundamentals = {}
    # Yahoo's quote-summary endpoint is materially slower than price download.
    # Bound the number of calls and issue them concurrently after pre-screening.
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(
                _fetch_fundamental, yfinance_module, symbol, expected
            ): symbol
            for symbol in shortlist
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                fundamental = future.result()
            except Exception:  # noqa: BLE001 - exclude only the failed symbol.
                continue
            if fundamental is not None:
                fundamentals[symbol] = fundamental
    return histories, fundamentals


def _fetch_fundamental(yfinance_module, symbol: str, expected: date):
    info = yfinance_module.Ticker(symbol).info or {}
    most_recent_quarter = info.get("mostRecentQuarter")
    if not most_recent_quarter:
        return None
    fundamental_date = datetime.fromtimestamp(
        float(most_recent_quarter), tz=timezone.utc
    ).date()
    eps_growth = _optional_number(info.get("earningsQuarterlyGrowth"))
    revenue_growth = _optional_number(info.get("revenueGrowth"))
    annual_growth = _optional_number(info.get("earningsGrowth"))
    if any(
        value is None
        for value in (eps_growth, revenue_growth, annual_growth)
    ):
        return None
    if fundamental_date > expected:
        return None
    return FundamentalMetrics(
        as_of=fundamental_date.isoformat(),
        quarterly_eps_growth=eps_growth,
        quarterly_revenue_growth=revenue_growth,
        annual_eps_growth=annual_growth,
        institutional_holders_available=(
            _optional_number(info.get("heldPercentInstitutions")) is not None
        ),
    )


def _bars_from_download(frame, symbol: str, expected: date) -> list[DailyBar]:
    if frame is None or getattr(frame, "empty", True):
        return []
    columns = getattr(frame, "columns", ())
    try:
        symbol_frame = frame[symbol] if getattr(columns, "nlevels", 1) > 1 else frame
    except (KeyError, TypeError):
        return []
    bars = []
    for timestamp, row in symbol_frame.iterrows():
        trading_date = (
            timestamp.date() if callable(getattr(timestamp, "date", None))
            else date.fromisoformat(str(timestamp)[:10])
        )
        if trading_date > expected:
            continue
        try:
            values = [float(row[key]) for key in ("Open", "High", "Low", "Close")]
            volume = int(float(row["Volume"]))
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if not all(isfinite(value) and value > 0 for value in values):
            continue
        bars.append(DailyBar(
            trading_date=trading_date,
            open=values[0],
            high=values[1],
            low=values[2],
            close=values[3],
            volume=max(0, volume),
            adjusted_close=values[3],
            source="yahoo_finance_adjusted_batch",
        ))
    bars.sort(key=lambda bar: bar.trading_date)
    return bars


def _optional_number(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def technical_confidence(bars: list[DailyBar], expected: date) -> tuple[int, list[str]]:
    """Return a data-validation confidence score, not an attractiveness score."""

    score = 10  # symbol mapping is fixed by the versioned universe.
    reasons = []
    if len(bars) >= 252:
        score += 20
    else:
        reasons.append("fewer than 252 observations")
    if bars and bars[-1].trading_date == expected:
        score += 20
    else:
        reasons.append("price cutoff mismatch")
    dates = [bar.trading_date for bar in bars]
    if dates and dates == sorted(set(dates)):
        score += 15
    else:
        reasons.append("duplicate or unsorted dates")
    valid = bool(bars) and all(
        all(isfinite(float(value)) and float(value) > 0 for value in (
            bar.open, bar.high, bar.low, bar.close, bar.adjusted_close
        )) and bar.volume >= 0
        for bar in bars
    )
    if valid:
        score += 20
    else:
        reasons.append("invalid OHLCV or adjusted close")
    if len(bars) >= 50:
        dollar_volume = _mean(
            float(bar.adjusted_close) * bar.volume for bar in bars[-50:]
        )
        if dollar_volume >= 20_000_000:
            score += 15
        else:
            reasons.append("50-day dollar liquidity below $20m")
    else:
        reasons.append("liquidity cannot be calculated")
    return score, reasons


def _validate_spy(bars: list[DailyBar], expected: date) -> None:
    score, reasons = technical_confidence(bars, expected)
    if score < MIN_TECHNICAL_CONFIDENCE:
        raise ValueError("SPY validation failed: " + "; ".join(reasons))


def _technical_metrics(history: list[DailyBar], spy: list[DailyBar]) -> dict:
    closes = [float(bar.adjusted_close) for bar in history]
    volumes = [bar.volume for bar in history]
    spy_closes = [float(bar.adjusted_close) for bar in spy]
    price = closes[-1]
    sma20 = _mean(closes[-20:])
    sma50 = _mean(closes[-50:])
    sma150 = _mean(closes[-150:])
    sma200 = _mean(closes[-200:])
    high52 = max(closes[-252:])
    low52 = min(closes[-252:])
    average_volume50 = _mean(volumes[-50:])
    volume_ratio = volumes[-1] / average_volume50 if average_volume50 else 0.0
    return126 = price / closes[-127] - 1
    spy_return126 = spy_closes[-1] / spy_closes[-127] - 1
    relative126 = (1 + return126) / (1 + spy_return126) - 1
    up_volume = sum(
        volumes[index]
        for index in range(len(closes) - 19, len(closes))
        if closes[index] > closes[index - 1]
    )
    total_volume = sum(volumes[-19:])
    checks = {
        "price_above_sma50": price > sma50,
        "price_above_sma150": price > sma150,
        "price_above_sma200": price > sma200,
        "sma50_above_sma150": sma50 > sma150,
        "sma150_above_sma200": sma150 > sma200,
        "sma200_rising": sma200 > _mean(closes[-220:-20]),
        "price_30pct_above_52w_low": price >= low52 * 1.30,
        "price_within_25pct_of_52w_high": price >= high52 * 0.75,
    }
    spy50 = _mean(spy_closes[-50:])
    spy200 = _mean(spy_closes[-200:])
    market_points = 5 * sum((
        spy_closes[-1] > spy50,
        spy_closes[-1] > spy200,
        spy50 > spy200,
        spy_closes[-1] > spy_closes[-21],
    ))
    return {
        "price": price,
        "sma20": sma20,
        "sma50": sma50,
        "high52": high52,
        "return126": return126,
        "relative126": relative126,
        "up_volume_ratio": up_volume / total_volume if total_volume else 0.5,
        "volume_ratio": volume_ratio,
        "checks": checks,
        "market_points": market_points,
    }


def _canslim_score(metrics: dict, fundamental: FundamentalMetrics) -> int:
    score = 0.0
    score += _scaled(fundamental.quarterly_eps_growth, 0.0, 0.50, 20)
    score += _scaled(fundamental.quarterly_revenue_growth, 0.0, 0.30, 10)
    score += _scaled(fundamental.annual_eps_growth, 0.0, 0.40, 15)
    score += _scaled(metrics["return126"], -0.20, 0.40, 10)
    score += metrics["up_volume_ratio"] * 10
    score += _scaled(metrics["relative126"], -0.20, 0.20, 10)
    score += 5 if fundamental.institutional_holders_available else 0
    score += metrics["market_points"]
    return _bounded(round(score))


def _minervini_score(metrics: dict) -> int:
    score = 8 * sum(metrics["checks"].values())
    score += _scaled(metrics["relative126"], -0.20, 0.20, 20)
    score += 4 * sum((
        metrics["price"] > metrics["sma20"],
        metrics["sma20"] > metrics["sma50"],
        metrics["up_volume_ratio"] >= 0.50,
        metrics["price"] >= metrics["high52"] * 0.85,
    ))
    return _bounded(round(score))


def _candidate_state(metrics: dict) -> tuple[str, str, int]:
    distance = metrics["price"] / metrics["high52"] - 1
    if distance >= -0.005 and metrics["volume_ratio"] >= 1.5:
        return "BREAKOUT", "維持突破區且成交量至少為50日均量1.5倍", 10
    if distance >= -0.05 and sum(metrics["checks"].values()) >= 7:
        return "WAIT", "突破52週高點且成交量至少為50日均量1.5倍", 5
    return "NOT_READY", "進入距52週高點5%以內並通過至少7項Trend Template", 0


def _scaled(value: float | None, floor: float, ceiling: float, points: int) -> float:
    if value is None or not isfinite(float(value)):
        return 0.0
    return max(0.0, min(float(points), (value - floor) / (ceiling - floor) * points))


def _mean(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items)


def _bounded(value: int) -> int:
    return max(0, min(100, value))
