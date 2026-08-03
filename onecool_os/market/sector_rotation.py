"""Deterministic US sector rotation cache for Fund Intelligence."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Iterable

from onecool_os.market.etf_cta import DailyBar


SECTOR_ETFS = {
    "XLB": "Materials",
    "XLC": "Communication Services",
    "XLE": "Energy",
    "XLF": "Financials",
    "XLI": "Industrials",
    "XLK": "Technology",
    "XLP": "Consumer Staples",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
    "XLV": "Health Care",
    "XLY": "Consumer Discretionary",
}


@dataclass(frozen=True)
class SectorReturn:
    symbol: str
    sector: str
    as_of: str
    return_1w_pct: float
    return_1m_pct: float
    composite_score: float
    status: str = "VALID"


def _month_ago(value: date) -> date:
    month = value.month - 1 or 12
    year = value.year - (1 if value.month == 1 else 0)
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _close(bar: DailyBar) -> float:
    return float(bar.adjusted_close or bar.close)


def _return_at_or_before(
    bars: list[DailyBar], end: DailyBar, target: date
) -> float:
    candidates = [item for item in bars if item.trading_date <= target]
    if not candidates:
        raise ValueError(f"No sector history exists on or before {target}.")
    start = candidates[-1]
    return (_close(end) / _close(start) - 1) * 100


def calculate_sector_return(
    symbol: str, bars: Iterable[DailyBar], *, as_of: date | None = None
) -> SectorReturn:
    values = sorted(bars, key=lambda item: item.trading_date)
    if not values:
        raise ValueError(f"No sector history for {symbol}.")
    cutoff = as_of or values[-1].trading_date
    eligible = [item for item in values if item.trading_date <= cutoff]
    if not eligible:
        raise ValueError(f"No sector history for {symbol} by {cutoff}.")
    end = eligible[-1]
    one_week = _return_at_or_before(eligible, end, end.trading_date - timedelta(days=7))
    one_month = _return_at_or_before(eligible, end, _month_ago(end.trading_date))
    score = one_week * 0.4 + one_month * 0.6
    return SectorReturn(
        symbol=symbol,
        sector=SECTOR_ETFS[symbol],
        as_of=end.trading_date.isoformat(),
        return_1w_pct=round(one_week, 4),
        return_1m_pct=round(one_month, 4),
        composite_score=round(score, 4),
    )


def build_sector_rotation_payload(results: Iterable[SectorReturn]) -> dict:
    values = sorted(
        results,
        key=lambda item: (item.composite_score, item.return_1m_pct),
        reverse=True,
    )
    if {item.symbol for item in values} != set(SECTOR_ETFS):
        missing = sorted(set(SECTOR_ETFS) - {item.symbol for item in values})
        raise ValueError("US Sector Rotation is incomplete: " + ", ".join(missing))
    dates = {item.as_of for item in values}
    if len(dates) != 1:
        raise ValueError("US Sector Rotation dates are inconsistent.")
    return {
        "schema_version": "1.0",
        "module": "US Sector Rotation Monitor",
        "generated_at": datetime.now(UTC).isoformat(),
        "as_of": dates.pop(),
        "provider": "yahoo_finance_adjusted",
        "method": {
            "periods": ["1w", "1m"],
            "composite_score": "40% one-week return + 60% one-month return",
            "decision_use": "context only; never independently changes CTA or Action",
        },
        "top_sectors": [asdict(item) for item in values[:3]],
        "results": [asdict(item) for item in values],
    }
