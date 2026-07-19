"""One-time historical bootstrap providers for the Market Dashboard."""

from __future__ import annotations

from datetime import date
from typing import Any

from onecool_os.market.etf_cta import DailyBar, ETFCTAError


class YahooHistoryBootstrapper:
    """Build a missing GitHub history once; never used by cache consumers."""

    provider_id = "yahoo_finance_bootstrap"

    def __init__(self, yfinance_module: Any | None = None) -> None:
        self._yfinance = yfinance_module

    def fetch_daily(self, symbol: str) -> list[DailyBar]:
        """Fetch enough raw daily history for the shared CTA engine."""

        if self._yfinance is None:
            try:
                self._yfinance = __import__("yfinance")
            except Exception as exc:  # noqa: BLE001 - provider boundary.
                raise ETFCTAError(
                    "Yahoo Finance bootstrap provider is unavailable."
                ) from exc

        try:
            frame = self._yfinance.Ticker(symbol).history(
                period="5y",
                interval="1d",
                auto_adjust=False,
                actions=False,
            )
        except Exception as exc:  # noqa: BLE001 - provider boundary.
            raise ETFCTAError(
                f"Yahoo Finance bootstrap failed for {symbol}: {exc}"
            ) from exc
        if frame is None or frame.empty:
            raise ETFCTAError(
                f"Yahoo Finance bootstrap returned no history for {symbol}."
            )

        bars = []
        for timestamp, row in frame.iterrows():
            trading_date = _as_date(timestamp)
            bars.append(
                DailyBar(
                    trading_date=trading_date,
                    open=_number(row, "Open"),
                    high=_number(row, "High"),
                    low=_number(row, "Low"),
                    close=_number(row, "Close"),
                    volume=int(_number(row, "Volume", 0.0)),
                    source=self.provider_id,
                )
            )
        bars.sort(key=lambda bar: bar.trading_date)
        if len(bars) < 260:
            raise ETFCTAError(
                f"Yahoo Finance bootstrap for {symbol} returned only "
                f"{len(bars)} observations; at least 260 are required."
            )
        return bars


def _as_date(value: Any) -> date:
    converted = getattr(value, "date", None)
    if callable(converted):
        return converted()
    return date.fromisoformat(str(value)[:10])


def _number(row: Any, key: str, default: float | None = None) -> float:
    try:
        value = row[key]
        if value is None and default is not None:
            return default
        return float(value)
    except (KeyError, TypeError, ValueError) as exc:
        if default is not None:
            return default
        raise ETFCTAError(f"Yahoo Finance bootstrap field {key} is invalid.") from exc
