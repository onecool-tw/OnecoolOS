"""Fund NAV history and same-date benchmark relative-alpha calculations."""

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
    "A10124": ("富邦AI智能新趨勢多重資產型基金-A(美元)", "QQQ", "AI"),
    "A16075": ("群益印度中小基金-美元", "SMIN", "印度"),
    "B23554": ("施羅德環球-環球黃金美元A累積", "GLD", "黃金"),
    "B15080": ("富蘭克林坦伯頓-生技領航A(acc)", "IBB", "生技"),
    "B09007": ("貝萊德世界礦業A2美元", "PICK", "礦業"),
    "B16019": ("景順環球消費趨勢基金A美元", "VCR", "消費"),
    "B23070": ("施羅德環球-環球能源A1累積", "XLE", "能源"),
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
class RelativeAlpha:
    """One fund-versus-watchlist-ETF return comparison."""

    fund_code: str
    fund_name: str
    benchmark_etf: str
    theme: str
    start_date: str | None
    end_date: str | None
    fund_return_1y: float | None
    benchmark_return_1y: float | None
    alpha_percentage_points: float | None
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


def calculate_relative_alpha(
    fund_code: str,
    fund_history: Iterable[FundNav],
    etf_history: Iterable[DailyBar],
    *,
    cutoff: date | None = None,
    max_start_gap_days: int = 10,
) -> RelativeAlpha:
    """Calculate one-year returns using identical start and end dates."""

    fund_name, benchmark, theme = FUND_WATCHLIST[fund_code]
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
        return _unknown(fund_code, "No common fund and ETF valuation date.")

    end = common[-1]
    target = _previous_year(end)
    candidates = [day for day in common if day <= target]
    if not candidates:
        return _unknown(fund_code, "No common one-year start date.", end=end)
    start = candidates[-1]
    if target - start > timedelta(days=max_start_gap_days):
        return _unknown(
            fund_code,
            "Common one-year start date is more than 10 days from target.",
            end=end,
        )

    fund_return = (funds[end] / funds[start] - 1.0) * 100.0
    etf_return = (float(etfs[end]) / float(etfs[start]) - 1.0) * 100.0
    alpha = fund_return - etf_return
    return RelativeAlpha(
        fund_code=fund_code,
        fund_name=fund_name,
        benchmark_etf=benchmark,
        theme=theme,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        fund_return_1y=round(fund_return, 4),
        benchmark_return_1y=round(etf_return, 4),
        alpha_percentage_points=round(alpha, 4),
        status="positive" if alpha > 0 else "negative" if alpha < 0 else "flat",
        reason="Fund and benchmark use identical start and end dates.",
    )


def completed_month_snapshots(
    fund_code: str,
    fund_history: Iterable[FundNav],
    etf_history: Iterable[DailyBar],
    *,
    as_of: date,
    months: int = 3,
) -> list[RelativeAlpha]:
    """Return relative alpha for the latest completed calendar months."""

    snapshots = []
    cursor = date(as_of.year, as_of.month, 1) - timedelta(days=1)
    for _ in range(months):
        snapshots.append(
            calculate_relative_alpha(
                fund_code, fund_history, etf_history, cutoff=cursor
            )
        )
        cursor = date(cursor.year, cursor.month, 1) - timedelta(days=1)
    return list(reversed(snapshots))


def consecutive_status(snapshots: Iterable[RelativeAlpha]) -> str:
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
    current: Iterable[RelativeAlpha],
    monthly: dict[str, list[RelativeAlpha]],
) -> dict[str, Any]:
    """Build one auditable JSON report without portfolio information."""

    current_list = list(current)
    return {
        "schema_version": "1.0",
        "metric": "Onecool Relative Alpha",
        "definition": "fund_1y_return - benchmark_etf_1y_total_return",
        "date_rule": "identical fund and ETF start/end dates",
        "source": {
            "fund_nav": "Anue Fund public NavHIS",
            "benchmark": "OnecoolOS locally adjusted ETF history",
        },
        "results": [
            {
                **asdict(result),
                "completed_months": [
                    asdict(item) for item in monthly[result.fund_code]
                ],
                "consecutive_status": consecutive_status(
                    monthly[result.fund_code]
                ),
            }
            for result in current_list
        ],
    }


def _unknown(
    fund_code: str, reason: str, *, end: date | None = None
) -> RelativeAlpha:
    name, benchmark, theme = FUND_WATCHLIST[fund_code]
    return RelativeAlpha(
        fund_code=fund_code,
        fund_name=name,
        benchmark_etf=benchmark,
        theme=theme,
        start_date=None,
        end_date=end.isoformat() if end else None,
        fund_return_1y=None,
        benchmark_return_1y=None,
        alpha_percentage_points=None,
        status="unknown",
        reason=reason,
    )


def _previous_year(day: date) -> date:
    try:
        return day.replace(year=day.year - 1)
    except ValueError:
        return date(day.year - 1, day.month, monthrange(day.year - 1, day.month)[1])


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
