"""StockQ global-market rotation radar for the weekly fund report."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Callable
from urllib.parse import urljoin
from urllib.request import Request, urlopen


STOCKQ_MARKET_URL = "https://www.stockq.org/market/"
ROTATION_PERIODS = ("一個月", "三個月", "六個月")
FUND_PERIODS = ("一個月", "三個月", "六個月", "一年")
FUND_WEIGHTS = {"一個月": 0.20, "三個月": 0.30, "六個月": 0.30, "一年": 0.20}


class StockQError(RuntimeError):
    """Raised when StockQ content cannot be safely interpreted."""


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[dict[str, str | None]]]] = []
        self._table_stack: list[list[list[dict[str, str | None]]]] = []
        self._row: list[dict[str, str | None]] | None = None
        self._cell: dict[str, str | None] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            table: list[list[dict[str, str | None]]] = []
            self._table_stack.append(table)
        elif tag == "tr" and self._table_stack:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = {"text": "", "href": None}
        elif tag == "a" and self._cell is not None:
            self._cell["href"] = dict(attrs).get("href")

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell["text"] = str(self._cell["text"]) + data

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._cell["text"] = " ".join(str(self._cell["text"]).split())
            self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table_stack:
            if self._row:
                self._table_stack[-1].append(self._row)
            self._row = None
        elif tag == "table" and self._table_stack:
            table = self._table_stack.pop()
            self.tables.append(table)


@dataclass(frozen=True)
class MarketCandidate:
    market: str
    index_url: str | None
    appearances: int
    ranks: dict[str, int]
    returns: dict[str, float]
    breadth_score: int
    stage1: str


@dataclass(frozen=True)
class FundCandidate:
    name: str
    returns: dict[str, float]
    consistency_score: float


def fetch_stockq_html(url: str, timeout: int = 25) -> str:
    request = Request(url, headers={"User-Agent": "OnecoolOS/1.0 StockQ weekly radar"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_tables(html: str) -> list[list[list[dict[str, str | None]]]]:
    parser = _TableParser()
    parser.feed(html)
    return parser.tables


def _percentage(value: str) -> float | None:
    text = value.replace("%", "").replace(",", "").strip()
    if text in {"", "N/A", "N/A%", "nan"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _ranking_tables(html: str) -> dict[str, list[tuple[str, float, str | None]]]:
    results: dict[str, list[tuple[str, float, str | None]]] = {}
    for table in parse_tables(html):
        if len(table) < 3 or not table[0]:
            continue
        period = str(table[0][0]["text"]).split()[0]
        if period not in ROTATION_PERIODS or period in results:
            continue
        rows = []
        for row in table[2:]:
            if len(row) < 2:
                continue
            value = _percentage(str(row[1]["text"]))
            if value is None:
                continue
            rows.append((str(row[0]["text"]), value, row[0]["href"]))
        if rows and rows[0][1] >= 0:
            results[period] = rows
    return results


def screen_markets(html: str, *, top_n: int = 15) -> list[MarketCandidate]:
    """Stage 1: rank markets appearing in StockQ's top lists across 1M/3M/6M."""

    rankings = _ranking_tables(html)
    missing = [period for period in ROTATION_PERIODS if period not in rankings]
    if missing:
        raise StockQError(f"Missing positive ranking tables: {', '.join(missing)}")

    combined: dict[str, dict] = {}
    for period in ROTATION_PERIODS:
        for rank, (market, value, href) in enumerate(rankings[period][:top_n], 1):
            item = combined.setdefault(
                market,
                {"ranks": {}, "returns": {}, "href": href, "score": 0},
            )
            item["ranks"][period] = rank
            item["returns"][period] = value
            item["href"] = item["href"] or href
            item["score"] += top_n + 1 - rank

    candidates = []
    for market, item in combined.items():
        appearances = len(item["ranks"])
        if appearances < 2:
            continue
        candidates.append(
            MarketCandidate(
                market=market,
                index_url=urljoin(STOCKQ_MARKET_URL, item["href"])
                if item["href"]
                else None,
                appearances=appearances,
                ranks=item["ranks"],
                returns=item["returns"],
                breadth_score=item["score"],
                stage1="PASS" if appearances == len(ROTATION_PERIODS) else "WATCH",
            )
        )
    return sorted(
        candidates,
        key=lambda item: (item.appearances, item.breadth_score),
        reverse=True,
    )


def _fund_table(html: str) -> list[dict[str, str]]:
    for table in reversed(parse_tables(html)):
        if len(table) < 3:
            continue
        headers = [str(cell["text"]) for cell in table[0]]
        if headers[:1] != ["名稱"] or not all(period in headers for period in FUND_PERIODS):
            continue
        records = []
        for row in table[1:]:
            if len(row) != len(headers):
                continue
            records.append({headers[index]: str(cell["text"]) for index, cell in enumerate(row)})
        return records
    return []


def screen_funds(html: str, *, limit: int = 3) -> list[FundCandidate]:
    """Stage 2: retain related funds with positive 1M/3M/6M/1Y performance."""

    eligible: list[tuple[str, dict[str, float]]] = []
    for record in _fund_table(html):
        name = record["名稱"]
        if "指數" in name or "基金平均" in name or name.startswith("("):
            continue
        returns = {period: _percentage(record[period]) for period in FUND_PERIODS}
        if any(value is None or value <= 0 for value in returns.values()):
            continue
        eligible.append((name, {key: float(value) for key, value in returns.items()}))

    if not eligible:
        return []

    percentiles: dict[str, dict[str, float]] = {name: {} for name, _ in eligible}
    for period in FUND_PERIODS:
        ordered = sorted(value[period] for _, value in eligible)
        count = len(ordered)
        for name, returns in eligible:
            rank = ordered.index(returns[period]) + 1
            percentiles[name][period] = rank / count * 100

    results = []
    for name, returns in eligible:
        score = sum(
            percentiles[name][period] * FUND_WEIGHTS[period]
            for period in FUND_PERIODS
        )
        results.append(
            FundCandidate(
                name=name,
                returns=returns,
                consistency_score=round(score, 2),
            )
        )
    return sorted(results, key=lambda item: item.consistency_score, reverse=True)[:limit]


def build_rotation_radar(
    market_html: str,
    index_fetcher: Callable[[str], str],
    *,
    as_of: str | None = None,
) -> dict:
    markets = screen_markets(market_html)
    passed = []
    for market in markets:
        if market.stage1 != "PASS":
            continue
        funds = []
        status = "NO_ELIGIBLE_FUND"
        if market.index_url:
            funds = screen_funds(index_fetcher(market.index_url))
            status = "PASS" if funds else "NO_ELIGIBLE_FUND"
        passed.append(
            {
                **asdict(market),
                "stage2": status,
                "funds": [asdict(fund) for fund in funds],
            }
        )

    return {
        "schema_version": "1.0",
        "as_of": as_of or datetime.now(timezone.utc).date().isoformat(),
        "source": STOCKQ_MARKET_URL,
        "source_policy": "StockQ rankings and related-fund tables; no estimation",
        "rules": {
            "stage1": "Top 15 in 1M, 3M and 6M; 3/3=PASS, 2/3=WATCH",
            "stage2": "Only PASS markets; fund 1M/3M/6M/1Y must all be positive",
            "fund_score_weights": FUND_WEIGHTS,
            "decision_use": "OPPORTUNITY_RADAR_ONLY",
        },
        "passed_markets": passed,
        "watch_markets": [asdict(item) for item in markets if item.stage1 == "WATCH"],
    }
