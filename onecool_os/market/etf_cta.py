"""Deterministic ETF history and CTA calculations for Fund Watchlist."""

from __future__ import annotations

import csv
import json
import time
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


WATCHLIST_SYMBOLS = ("AIQ", "SMIN", "RING", "IBB", "PICK", "RXI", "IXC")
CONFIRMATION_SYMBOLS = ("GLD",)
COMMODITY_CONFIRMATION_SYMBOLS = ("WTI",)
EQUITY_MARKET_SYMBOLS = WATCHLIST_SYMBOLS + CONFIRMATION_SYMBOLS
MARKET_SYMBOLS = EQUITY_MARKET_SYMBOLS + COMMODITY_CONFIRMATION_SYMBOLS
RETIRED_SYMBOLS = ("SMH",)
ACTION_REFRESH_GROUPS = {
    "group_a": ("AIQ", "SMIN", "RING", "IBB", "PICK"),
    "group_b": ("RXI", "IXC", "GLD"),
}
HISTORY_FIELDS = (
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "dividend",
    "split_factor",
    "adjusted_close",
    "source",
)


class ETFCTAError(RuntimeError):
    """Raised when ETF history cannot be updated or evaluated safely."""


@dataclass(frozen=True)
class DailyBar:
    """One raw daily market observation plus corporate actions."""

    trading_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    dividend: float = 0.0
    split_factor: float = 1.0
    adjusted_close: float | None = None
    source: str = "alpha_vantage"


@dataclass(frozen=True)
class CrossSignal:
    """Current MA alignment plus an auditable most-recent crossover."""

    alignment: str
    cross_status: str
    last_cross_status: str
    last_cross_date: str | None
    periods_since_cross: int | None
    spread_pct: float
    phase: str = "UNKNOWN"


@dataclass(frozen=True)
class CTAResult:
    """Auditable CTA snapshot calculated from one adjusted-close history."""

    symbol: str
    as_of: str
    price: float
    daily_50ma: float
    daily_200ma: float
    weekly_30ma: float
    weekly_50ma: float
    cta: str
    reason: str
    price_basis: str = "locally_adjusted_close"
    daily_cross: CrossSignal | None = None
    weekly_cross: CrossSignal | None = None


class AlphaVantageClient:
    """Small Alpha Vantage client using only free-tier endpoints."""

    endpoint = "https://www.alphavantage.co/query"

    def __init__(
        self,
        api_key: str,
        *,
        request: Callable[[str], bytes] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        request_spacing_seconds: float = 13.0,
    ) -> None:
        if not api_key:
            raise ETFCTAError("ALPHA_VANTAGE_API_KEY is required.")
        self.api_key = api_key
        self._request = request or _download
        self._sleep = sleeper
        self.request_spacing_seconds = request_spacing_seconds
        self._has_requested = False

    def fetch_symbol(self, symbol: str) -> list[DailyBar]:
        """Fetch compact raw daily data and all corporate actions."""

        bars = self.fetch_daily(symbol)
        return apply_corporate_actions(
            bars, self.fetch_actions(symbol), authoritative=True
        )

    def fetch_daily(
        self, symbol: str, *, outputsize: str = "compact"
    ) -> list[DailyBar]:
        """Fetch compact raw daily data with one API request."""

        return parse_alpha_vantage_daily(
            self._query("TIME_SERIES_DAILY", symbol, outputsize=outputsize)
        )

    def fetch_actions(self, symbol: str) -> dict[date, tuple[float, float]]:
        """Fetch complete dividends and splits with two API requests."""

        return parse_alpha_vantage_actions(
            self._query("DIVIDENDS", symbol),
            self._query("SPLITS", symbol),
        )

    def fetch_wti_daily(self) -> list[DailyBar]:
        """Fetch the EIA/FRED WTI daily series with one API request."""

        return parse_alpha_vantage_wti(
            self._query("WTI", None, outputsize=None, interval="daily")
        )

    def _query(
        self,
        function: str,
        symbol: str | None,
        *,
        outputsize: str | None = "compact",
        **parameters: str,
    ) -> dict[str, Any]:
        if self._has_requested:
            self._sleep(self.request_spacing_seconds)
        self._has_requested = True
        query_parameters = {"function": function, "apikey": self.api_key}
        if symbol is not None:
            query_parameters["symbol"] = symbol
        if outputsize is not None:
            query_parameters["outputsize"] = outputsize
        query_parameters.update(parameters)
        query = urlencode(query_parameters)
        url = f"{self.endpoint}?{query}"
        payload: dict[str, Any] = {}
        last_error: Exception | None = None
        for attempt, retry_delay in enumerate((60.0, 120.0, 300.0, 0.0), 1):
            try:
                payload = json.loads(self._request(url))
                if not payload.get("Note"):
                    break
                last_error = ETFCTAError(str(payload["Note"]))
            except Exception as exc:  # noqa: BLE001 - provider boundary.
                last_error = exc
            if retry_delay:
                self._sleep(retry_delay)
        if payload.get("Note") or not payload:
            raise ETFCTAError(
                "Alpha Vantage request failed for "
                f"{symbol or 'commodity'}/{function} "
                f"after 4 attempts: {last_error}"
            ) from last_error
        message = payload.get("Error Message") or payload.get("Information")
        if message:
            raise ETFCTAError(
                "Alpha Vantage rejected "
                f"{symbol or 'commodity'}/{function}: {message}"
            )
        return payload


def parse_alpha_vantage(
    daily_payload: dict[str, Any],
    dividend_payload: dict[str, Any],
    split_payload: dict[str, Any],
) -> list[DailyBar]:
    """Normalize Alpha Vantage raw daily and corporate-action responses."""

    return apply_corporate_actions(
        parse_alpha_vantage_daily(daily_payload),
        parse_alpha_vantage_actions(dividend_payload, split_payload),
    )


def parse_alpha_vantage_daily(daily_payload: dict[str, Any]) -> list[DailyBar]:
    """Normalize one Alpha Vantage raw daily response."""

    series = daily_payload.get("Time Series (Daily)")
    if not isinstance(series, dict) or not series:
        raise ETFCTAError("Alpha Vantage daily response contains no time series.")
    bars = []
    for day, values in series.items():
        bars.append(
            DailyBar(
                trading_date=date.fromisoformat(day),
                open=_float(values.get("1. open")),
                high=_float(values.get("2. high")),
                low=_float(values.get("3. low")),
                close=_float(values.get("4. close")),
                volume=int(_float(values.get("5. volume"), 0.0)),
            )
        )
    return sorted(bars, key=lambda bar: bar.trading_date)


def parse_alpha_vantage_wti(payload: dict[str, Any]) -> list[DailyBar]:
    """Normalize the WTI daily commodity series without futures-roll artifacts."""

    observations = payload.get("data")
    if not isinstance(observations, list) or not observations:
        raise ETFCTAError("Alpha Vantage WTI response contains no observations.")
    bars = []
    for item in observations:
        raw_value = item.get("value")
        if not item.get("date") or raw_value in {None, "."}:
            continue
        value = _float(raw_value)
        bars.append(
            DailyBar(
                trading_date=date.fromisoformat(item["date"]),
                open=value,
                high=value,
                low=value,
                close=value,
                volume=0,
                adjusted_close=value,
                source="alpha_vantage_wti_eia_fred",
            )
        )
    if not bars:
        raise ETFCTAError("Alpha Vantage WTI response has no valid values.")
    return sorted(bars, key=lambda bar: bar.trading_date)


def parse_alpha_vantage_actions(
    dividend_payload: dict[str, Any], split_payload: dict[str, Any]
) -> dict[date, tuple[float, float]]:
    """Normalize full corporate-action responses by effective date."""

    dividends = {
        date.fromisoformat(item["ex_dividend_date"]): _float(
            item.get("amount"), 0.0
        )
        for item in dividend_payload.get("data", [])
        if item.get("ex_dividend_date")
    }
    splits = {
        date.fromisoformat(item["effective_date"]): _float(
            item.get("split_factor"), 1.0
        )
        for item in split_payload.get("data", [])
        if item.get("effective_date")
    }
    return {
        day: (dividends.get(day, 0.0), splits.get(day, 1.0))
        for day in dividends.keys() | splits.keys()
    }


def apply_corporate_actions(
    bars: Iterable[DailyBar],
    actions: dict[date, tuple[float, float]],
    *,
    authoritative: bool = False,
) -> list[DailyBar]:
    """Apply action records, optionally clearing stale provider actions."""

    updated = []
    for bar in bars:
        action = actions.get(bar.trading_date)
        if action is None and not authoritative:
            updated.append(bar)
            continue
        dividend, split_factor = action or (0.0, 1.0)
        updated.append(
            DailyBar(
                **{
                    **asdict(bar),
                    "dividend": dividend,
                    "split_factor": split_factor,
                    "adjusted_close": None,
                }
            )
        )
    return updated


def has_new_price_anomaly(
    existing: Iterable[DailyBar],
    incoming: Iterable[DailyBar],
    *,
    threshold: float = 0.35,
) -> bool:
    """Flag a large raw-close move on newly received market dates."""

    old = sorted(existing, key=lambda bar: bar.trading_date)
    new = sorted(incoming, key=lambda bar: bar.trading_date)
    if not old or not new:
        return False
    latest_old = old[-1].trading_date
    combined = {bar.trading_date: bar for bar in old}
    combined.update({bar.trading_date: bar for bar in new})
    ordered = [combined[day] for day in sorted(combined)]
    for previous, current in zip(ordered, ordered[1:]):
        if current.trading_date <= latest_old or previous.close <= 0:
            continue
        if abs(current.close / previous.close - 1.0) > threshold:
            return True
    return False


def merge_and_adjust(
    existing: Iterable[DailyBar], incoming: Iterable[DailyBar]
) -> list[DailyBar]:
    """Merge by market date and recalculate one adjusted-close history."""

    merged = {bar.trading_date: bar for bar in existing}
    merged.update({bar.trading_date: bar for bar in incoming})
    bars = [merged[key] for key in sorted(merged)]
    if not bars:
        return []

    adjusted: list[DailyBar | None] = [None] * len(bars)
    factor = 1.0
    for index in range(len(bars) - 1, -1, -1):
        bar = bars[index]
        adjusted[index] = DailyBar(
            **{
                **asdict(bar),
                "adjusted_close": bar.close * factor,
            }
        )
        if index == 0:
            continue
        if bar.split_factor <= 0:
            raise ETFCTAError(
                f"Invalid split factor on {bar.trading_date}: {bar.split_factor}"
            )
        previous_close = bars[index - 1].close
        factor /= _effective_split_factor(
            previous_close, bar.close, bar.split_factor
        )
        if bar.dividend:
            if previous_close <= bar.dividend:
                raise ETFCTAError(
                    f"Invalid dividend adjustment on {bar.trading_date}."
                )
            factor *= (previous_close - bar.dividend) / previous_close
    return [bar for bar in adjusted if bar is not None]


def _effective_split_factor(
    previous_close: float, current_close: float, split_factor: float
) -> float:
    """Avoid applying a split twice when the provider already adjusted OHLC."""

    if split_factor == 1.0 or previous_close <= 0 or current_close <= 0:
        return split_factor
    raw_gap = abs(current_close / previous_close - 1.0)
    split_adjusted_gap = abs(
        current_close * split_factor / previous_close - 1.0
    )
    return 1.0 if raw_gap <= split_adjusted_gap else split_factor


def calculate_cta(symbol: str, bars: Iterable[DailyBar]) -> CTAResult:
    """Calculate the fixed Onecool CTA rule from adjusted closes."""

    history = sorted(bars, key=lambda bar: bar.trading_date)
    if len(history) < 200:
        raise ETFCTAError(f"{symbol} needs at least 200 daily observations.")
    if any(bar.adjusted_close is None for bar in history):
        raise ETFCTAError(f"{symbol} history contains unadjusted observations.")
    closes = [float(bar.adjusted_close) for bar in history]
    weekly_points = _weekly_last_points(history)
    weekly = [value for _, value in weekly_points]
    if len(weekly) < 50:
        raise ETFCTAError(f"{symbol} needs at least 50 weekly observations.")

    price = closes[-1]
    d50 = _mean(closes[-50:])
    d200 = _mean(closes[-200:])
    w30 = _mean(weekly[-30:])
    w50 = _mean(weekly[-50:])
    daily_cross = _detect_cross(
        [bar.trading_date for bar in history], closes, 50, 200,
        confirmed_through=5, active_through=60,
    )
    weekly_cross = _detect_cross(
        [point_date for point_date, _ in weekly_points], weekly, 30, 50,
        confirmed_through=4, active_through=52,
    )

    signal, reason = cross_priority_cta(daily_cross, weekly_cross)

    return CTAResult(
        symbol=symbol,
        as_of=history[-1].trading_date.isoformat(),
        price=round(price, 6),
        daily_50ma=round(d50, 6),
        daily_200ma=round(d200, 6),
        weekly_30ma=round(w30, 6),
        weekly_50ma=round(w50, 6),
        cta=signal,
        reason=reason,
        daily_cross=daily_cross,
        weekly_cross=weekly_cross,
    )


def read_history(path: Path) -> list[DailyBar]:
    """Read one symbol's committed CSV history."""

    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            DailyBar(
                trading_date=date.fromisoformat(row["date"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
                dividend=float(row["dividend"]),
                split_factor=float(row["split_factor"]),
                adjusted_close=float(row["adjusted_close"]),
                source=row["source"],
            )
            for row in csv.DictReader(handle)
        ]


def write_history(path: Path, bars: Iterable[DailyBar]) -> None:
    """Write stable, reviewable CSV history."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HISTORY_FIELDS)
        writer.writeheader()
        for bar in bars:
            writer.writerow(
                {
                    "date": bar.trading_date.isoformat(),
                    "open": _format(bar.open),
                    "high": _format(bar.high),
                    "low": _format(bar.low),
                    "close": _format(bar.close),
                    "volume": bar.volume,
                    "dividend": _format(bar.dividend),
                    "split_factor": _format(bar.split_factor),
                    "adjusted_close": _format(bar.adjusted_close),
                    "source": bar.source,
                }
            )


def _weekly_last_closes(history: list[DailyBar]) -> list[float]:
    return [value for _, value in _weekly_last_points(history)]


def _weekly_last_points(history: list[DailyBar]) -> list[tuple[date, float]]:
    """Return the final published observation and value for each ISO week."""

    weekly: dict[tuple[int, int], tuple[date, float]] = {}
    for bar in history:
        iso = bar.trading_date.isocalendar()
        weekly[(iso.year, iso.week)] = (
            bar.trading_date,
            float(bar.adjusted_close),
        )
    return list(weekly.values())


def _detect_cross(
    dates: list[date], values: list[float], short_window: int, long_window: int,
    *, confirmed_through: int, active_through: int,
) -> CrossSignal:
    """Detect a real MA crossing; alignment alone is never called a new cross."""

    short_ma = _moving_average_series(values, short_window)
    long_ma = _moving_average_series(values, long_window)
    latest_short = short_ma[-1]
    latest_long = long_ma[-1]
    if latest_short is None or latest_long is None:
        raise ETFCTAError("Insufficient observations for crossover detection.")

    if latest_short > latest_long:
        alignment = "GOLDEN"
    elif latest_short < latest_long:
        alignment = "DEATH"
    else:
        alignment = "EQUAL"

    crossings: list[tuple[int, str]] = []
    for index in range(1, len(values)):
        previous_short = short_ma[index - 1]
        previous_long = long_ma[index - 1]
        current_short = short_ma[index]
        current_long = long_ma[index]
        if None in (previous_short, previous_long, current_short, current_long):
            continue
        if previous_short <= previous_long and current_short > current_long:
            crossings.append((index, "GOLDEN"))
        elif previous_short >= previous_long and current_short < current_long:
            crossings.append((index, "DEATH"))

    latest_index = len(values) - 1
    current_cross = (
        crossings[-1][1]
        if crossings and crossings[-1][0] == latest_index
        else "NONE"
    )
    if crossings:
        cross_index, last_cross = crossings[-1]
        last_cross_date = dates[cross_index].isoformat()
        periods_since_cross = latest_index - cross_index
    else:
        last_cross = "NONE"
        last_cross_date = None
        periods_since_cross = None

    return CrossSignal(
        alignment=alignment,
        cross_status=current_cross,
        last_cross_status=last_cross,
        last_cross_date=last_cross_date,
        periods_since_cross=periods_since_cross,
        spread_pct=round((latest_short / latest_long - 1.0) * 100, 6),
        phase=_cross_phase(
            periods_since_cross, confirmed_through, active_through
        ),
    )


def _cross_phase(
    periods_since_cross: int | None,
    confirmed_through: int,
    active_through: int,
) -> str:
    """Classify crossover recency without mistaking alignment for a new event."""

    if periods_since_cross is None:
        return "UNKNOWN"
    if periods_since_cross == 0:
        return "NEW"
    if periods_since_cross <= confirmed_through:
        return "CONFIRMED"
    if periods_since_cross <= active_through:
        return "ACTIVE"
    return "AGING"


def cross_priority_cta(
    daily: CrossSignal, weekly: CrossSignal
) -> tuple[str, str]:
    """Apply the Onecool rule: weekly crossover first, daily as confirmation.

    Daily signals may confirm a weekly signal or soften it by one level, but
    never reverse it on their own.  An aging weekly golden cross is HOLD until
    refreshed by daily strength; an active weekly death cross remains SELL.
    """

    if weekly.cross_status == "GOLDEN":
        return "BUY", "New weekly golden cross; weekly trend has priority."
    if weekly.cross_status == "DEATH":
        return "SELL", "New weekly death cross; weekly trend has priority."

    if weekly.alignment == "GOLDEN":
        if daily.cross_status == "DEATH" or daily.alignment == "DEATH":
            return "WATCH", "Weekly golden trend remains, but daily trend weakened."
        if weekly.phase in {"CONFIRMED", "ACTIVE"}:
            return "BUY", "Weekly golden cross remains confirmed or active."
        if daily.cross_status == "GOLDEN" or daily.phase in {"CONFIRMED", "ACTIVE"}:
            return "BUY", "Aging weekly golden trend was refreshed by daily strength."
        return "HOLD", "Weekly golden trend is aging without a fresh daily cross."

    if weekly.alignment == "DEATH":
        if daily.cross_status == "GOLDEN":
            return "WATCH", "Daily golden cross cannot override the weekly death trend."
        if weekly.phase in {"NEW", "CONFIRMED", "ACTIVE"}:
            return "SELL", "Weekly death cross remains confirmed or active."
        return "WATCH", "Weekly death trend is aging; no reversal is confirmed."

    if daily.cross_status == "DEATH" or daily.alignment == "DEATH":
        return "WATCH", "Weekly trend is neutral and daily trend is weak."
    return "HOLD", "No decisive weekly crossover is active."


def _moving_average_series(
    values: list[float], window: int
) -> list[float | None]:
    """Return an aligned simple-moving-average series in linear time."""

    result: list[float | None] = [None] * len(values)
    running = 0.0
    for index, value in enumerate(values):
        running += value
        if index >= window:
            running -= values[index - window]
        if index >= window - 1:
            result[index] = running / window
    return result


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _float(value: Any, default: float | None = None) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        if default is not None:
            return default
        raise ETFCTAError(f"Invalid numeric market value: {value!r}") from exc


def _format(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.8f}".rstrip("0").rstrip(".")


def _download(url: str) -> bytes:
    with urlopen(url, timeout=30) as response:  # noqa: S310 - fixed HTTPS host.
        return response.read()
