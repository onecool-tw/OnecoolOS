"""Fund NAV history and same-date CTA-proxy excess-return calculations."""

from __future__ import annotations

import csv
import json
from calendar import monthrange
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from onecool_os.market.etf_cta import DailyBar, ETFCTAError


FUND_WATCHLIST = {
    "A10124": ("富邦AI智能新趨勢多重資產型基金-A(美元)", "AIQ", "AI"),
    "A16075": ("群益印度中小基金-美元", "SMIN", "印度"),
    "B23554": ("施羅德環球-環球黃金美元A累積", "RING", "黃金"),
    "B15080": ("富蘭克林坦伯頓-生技領航A(acc)", "IBB", "生技"),
    "B09007": ("貝萊德世界礦業A2美元", "PICK", "礦業"),
    "B16019": ("景順環球消費趨勢基金A美元", "RXI", "消費"),
    "B23070": ("施羅德環球-環球能源A1累積", "IXC", "能源"),
}
PROXY_METHODOLOGY_CUTOVER = date(2026, 7, 20)
LEGACY_PROXY_ETFS = {
    "A10124": "QQQ",
    "B23554": "GLD",
    "B16019": "VCR",
    "B23070": "XLE",
}
NAV_FIELDS = ("date", "nav", "currency", "source")


@dataclass(frozen=True)
class FundNav:
    """One published fund share-class NAV."""

    nav_date: date
    nav: float
    currency: str = "USD"
    source: str = "anuefund_public"


@dataclass(frozen=True)
class ExcessReturn:
    """One fund-versus-CTA-proxy total-return comparison."""

    fund_code: str
    fund_name: str
    proxy_etf: str
    theme: str
    start_date: str | None
    end_date: str | None
    fund_return_1y: float | None
    proxy_return_1y: float | None
    excess_return_percentage_points: float | None
    status: str
    reason: str


@dataclass(frozen=True)
class PeriodExcessReturn:
    """One same-date excess-return measurement for a named horizon."""

    period: str
    start_date: str | None
    end_date: str | None
    fund_return: float | None
    proxy_return: float | None
    excess_return_percentage_points: float | None
    status: str
    reason: str


class AnueFundClient:
    """Read the public NAV history used by Anue Fund's own fund pages."""

    endpoint = "https://www.anuefund.com/anuefundApi/FundDetail/FundInfo"

    def __init__(
        self,
        *,
        request: Callable[[str], bytes] | None = None,
    ) -> None:
        self._request = request or _download

    def fetch_history(self, fund_code: str) -> list[FundNav]:
        query = urlencode(
            {"fundDetailEnum": "NavHIS", "FundID": fund_code}
        )
        payload = json.loads(self._request(f"{self.endpoint}?{query}"))
        return parse_anue_nav_history(payload, fund_code)


def parse_anue_nav_history(
    payload: dict[str, Any], fund_code: str
) -> list[FundNav]:
    """Validate and normalize an Anue NavHIS response."""

    data = payload.get("data")
    if not isinstance(data, dict) or data.get("fundID") != fund_code:
        raise ETFCTAError(f"Invalid Anue NAV response for {fund_code}.")
    header = data.get("hearder") or {}
    currency = _currency_code(header.get("ccy"))
    rows = data.get("navHIS")
    if not isinstance(rows, list) or not rows:
        raise ETFCTAError(f"Anue NAV history is empty for {fund_code}.")
    history = []
    for row in rows:
        nav = _positive_float(row.get("nav"), fund_code)
        history.append(
            FundNav(
                nav_date=date.fromisoformat(str(row["navDate"])[:10]),
                nav=nav,
                currency=currency,
            )
        )
    return sorted(history, key=lambda item: item.nav_date)


def merge_nav_history(
    existing: Iterable[FundNav], incoming: Iterable[FundNav]
) -> list[FundNav]:
    """Merge NAV observations by valuation date."""

    merged = {item.nav_date: item for item in existing}
    merged.update({item.nav_date: item for item in incoming})
    return [merged[key] for key in sorted(merged)]


def calculate_excess_return(
    fund_code: str,
    fund_history: Iterable[FundNav],
    etf_history: Iterable[DailyBar],
    *,
    cutoff: date | None = None,
    max_start_gap_days: int = 10,
) -> ExcessReturn:
    """Calculate one-year excess return using identical start and end dates."""

    period = calculate_period_excess_return(
        fund_code,
        fund_history,
        etf_history,
        months=12,
        period="1y",
        cutoff=cutoff,
        max_start_gap_days=max_start_gap_days,
    )
    fund_name, benchmark, theme = FUND_WATCHLIST[fund_code]
    return ExcessReturn(
        fund_code=fund_code,
        fund_name=fund_name,
        proxy_etf=benchmark,
        theme=theme,
        start_date=period.start_date,
        end_date=period.end_date,
        fund_return_1y=period.fund_return,
        proxy_return_1y=period.proxy_return,
        excess_return_percentage_points=(
            period.excess_return_percentage_points
        ),
        status=period.status,
        reason=period.reason,
    )


def calculate_period_excess_return(
    fund_code: str,
    fund_history: Iterable[FundNav],
    etf_history: Iterable[DailyBar],
    *,
    months: int,
    period: str,
    cutoff: date | None = None,
    max_start_gap_days: int = 10,
) -> PeriodExcessReturn:
    """Calculate excess return for one horizon on identical valuation dates."""

    if months <= 0:
        raise ValueError("months must be positive")

    funds = {item.nav_date: item.nav for item in fund_history}
    etfs = {
        item.trading_date: item.adjusted_close
        for item in etf_history
        if item.adjusted_close is not None
    }
    common = sorted(funds.keys() & etfs.keys())
    if cutoff is not None:
        common = [day for day in common if day <= cutoff]
    if not common:
        return _unknown_period(
            period, "No common fund and ETF valuation date."
        )

    end = common[-1]
    target = _previous_months(end, months)
    candidates = [day for day in common if day <= target]
    if not candidates:
        return _unknown_period(
            period,
            f"No common {period} start date.",
            end=end,
        )
    start = candidates[-1]
    if target - start > timedelta(days=max_start_gap_days):
        return _unknown_period(
            period,
            f"Common {period} start date is more than "
            f"{max_start_gap_days} days from target.",
            end=end,
        )

    fund_return = (funds[end] / funds[start] - 1.0) * 100.0
    etf_return = (float(etfs[end]) / float(etfs[start]) - 1.0) * 100.0
    excess_return = fund_return - etf_return
    return PeriodExcessReturn(
        period=period,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        fund_return=round(fund_return, 4),
        proxy_return=round(etf_return, 4),
        excess_return_percentage_points=round(excess_return, 4),
        status=(
            "positive"
            if excess_return > 0
            else "negative"
            if excess_return < 0
            else "flat"
        ),
        reason="Fund and CTA proxy use identical start and end dates.",
    )


def completed_month_snapshots(
    fund_code: str,
    fund_history: Iterable[FundNav],
    etf_history: Iterable[DailyBar],
    *,
    as_of: date,
    months: int = 3,
) -> list[ExcessReturn]:
    """Return excess return for completed months using the current proxy.

    A proxy methodology cutover must not discard comparable history when the
    current proxy has sufficient local price data.  Each snapshot is therefore
    backfilled using only the current proxy and identical fund/ETF dates; legacy
    proxy results are never spliced into this sequence.
    """

    snapshots = []
    cursor = date(as_of.year, as_of.month, 1) - timedelta(days=1)
    while len(snapshots) < months:
        snapshots.append(
            calculate_excess_return(
                fund_code, fund_history, etf_history, cutoff=cursor
            )
        )
        cursor = date(cursor.year, cursor.month, 1) - timedelta(days=1)
    return list(reversed(snapshots))


# Backward-compatible import for callers migrating from schema 1.0. New code
# should use calculate_excess_return; the returned fields follow schema 2.0.
calculate_relative_alpha = calculate_excess_return


def consecutive_status(snapshots: Iterable[ExcessReturn]) -> str:
    """Classify three completed months without treating unknown as negative."""

    statuses = [snapshot.status for snapshot in snapshots]
    if len(statuses) < 3 or "unknown" in statuses:
        return "insufficient_data"
    if all(status == "positive" for status in statuses):
        return "positive_3_months"
    if all(status == "negative" for status in statuses):
        return "negative_3_months"
    return "mixed"


def read_nav_history(path: Path) -> list[FundNav]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            FundNav(
                nav_date=date.fromisoformat(row["date"]),
                nav=float(row["nav"]),
                currency=row["currency"],
                source=row["source"],
            )
            for row in csv.DictReader(handle)
        ]


def write_nav_history(path: Path, history: Iterable[FundNav]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=NAV_FIELDS)
        writer.writeheader()
        for item in history:
            writer.writerow(
                {
                    "date": item.nav_date.isoformat(),
                    "nav": _format(item.nav),
                    "currency": item.currency,
                    "source": item.source,
                }
            )


def alpha_payload(
    current: Iterable[ExcessReturn],
    monthly: dict[str, list[ExcessReturn]],
    periods: dict[str, dict[str, PeriodExcessReturn]] | None = None,
) -> dict[str, Any]:
    """Build one auditable schema-2 report without portfolio information."""

    current_list = list(current)
    return {
        "schema_version": "2.1",
        "metric": "Onecool Excess Return",
        "definition": "fund_period_return - cta_proxy_etf_period_total_return",
        "periods": ["3m", "6m", "1y"],
        "date_rule": "identical fund and CTA proxy start/end dates",
        "methodology_cutover_date": PROXY_METHODOLOGY_CUTOVER.isoformat(),
        "source": {
            "fund_nav": "Anue Fund public NavHIS",
            "benchmark": "OnecoolOS locally adjusted ETF history",
        },
        "results": [
            {
                **asdict(result),
                "legacy_proxy_etf": LEGACY_PROXY_ETFS.get(result.fund_code),
                "proxy_changed_at": (
                    PROXY_METHODOLOGY_CUTOVER.isoformat()
                    if result.fund_code in LEGACY_PROXY_ETFS
                    else None
                ),
                "completed_months_methodology": (
                    "backfilled_new_benchmark"
                    if result.fund_code in LEGACY_PROXY_ETFS
                    else "continuous_current_benchmark"
                ),
                "completed_months": [
                    asdict(item) for item in monthly[result.fund_code]
                ],
                "consecutive_status": consecutive_status(
                    monthly[result.fund_code]
                ),
                "period_returns": {
                    name: asdict(value)
                    for name, value in (periods or {})
                    .get(result.fund_code, {})
                    .items()
                },
            }
            for result in current_list
        ],
    }


def _unknown(
    fund_code: str, reason: str, *, end: date | None = None
) -> ExcessReturn:
    name, benchmark, theme = FUND_WATCHLIST[fund_code]
    return ExcessReturn(
        fund_code=fund_code,
        fund_name=name,
        proxy_etf=benchmark,
        theme=theme,
        start_date=None,
        end_date=end.isoformat() if end else None,
        fund_return_1y=None,
        proxy_return_1y=None,
        excess_return_percentage_points=None,
        status="unknown",
        reason=reason,
    )


def _unknown_period(
    period: str, reason: str, *, end: date | None = None
) -> PeriodExcessReturn:
    return PeriodExcessReturn(
        period=period,
        start_date=None,
        end_date=end.isoformat() if end else None,
        fund_return=None,
        proxy_return=None,
        excess_return_percentage_points=None,
        status="unknown",
        reason=reason,
    )


def _previous_months(day: date, months: int) -> date:
    total_months = day.year * 12 + day.month - 1 - months
    year, zero_based_month = divmod(total_months, 12)
    month = zero_based_month + 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def _currency_code(value: Any) -> str:
    text = str(value or "").strip()
    mapping = {"美元": "USD", "USD": "USD"}
    if text not in mapping:
        raise ETFCTAError(f"Unsupported fund NAV currency: {text!r}")
    return mapping[text]


def _positive_float(value: Any, fund_code: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ETFCTAError(f"Invalid NAV for {fund_code}: {value!r}") from exc
    if number <= 0:
        raise ETFCTAError(f"Non-positive NAV for {fund_code}: {number}")
    return number


def _format(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")


def _download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "OnecoolOS/1.0"})
    with urlopen(request, timeout=60) as response:  # noqa: S310 - fixed host.
        return response.read()
