"""Low-frequency peer rankings published on Cnyes fund pages."""

from __future__ import annotations

import html
import re
from dataclasses import asdict, dataclass, replace
from datetime import date
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.parse import quote
from urllib.request import Request, urlopen

from onecool_os.market.fund_alpha import FUND_WATCHLIST


PERIOD_INDEX = {"3m": 1, "6m": 2, "1y": 4}

# Fund-platform codes are not always Cnyes page identifiers.  Keep the mapping
# explicit so a similarly named share class can never be selected implicitly.
CNYES_FUND_PAGES = {
    "A10124": ("A10124", "富邦AI智能新趨勢多重資產型基金-A(美元)"),
    "A16075": ("A16075", "群益印度中小基金-美元"),
    "B23554": ("B1MSY6T", "施羅德環球基金系列－環球黃金(美元)A-累積"),
    "B15080": ("B15,080", "富蘭克林坦伯頓全球投資系列-生技領航基金美元A(acc)股"),
    "B09007": ("B09,007", "貝萊德世界礦業基金 A2"),
    "B16019": ("B16,019", "景順環球消費趨勢基金A股 美元"),
    "B23070": ("B23,070", "施羅德環球基金系列－環球能源(美元)A1-累積"),
}

PEER_SCOPE_OVERRIDES = {
    "B09007": {
        "peer_scope": "broad_natural_resources",
        "strategy_match": "PARTIAL",
        "decision_use": "CONTEXT_ONLY",
    }
}


@dataclass(frozen=True)
class PeerRanking:
    """One published same-category ranking snapshot."""

    fund_code: str
    fund_name: str
    source: str
    source_url: str
    category: str | None
    as_of: str | None
    percentile_3m: int | None
    percentile_6m: int | None
    percentile_1y: int | None
    peer_average_3m: float | None
    peer_average_6m: float | None
    peer_average_1y: float | None
    data_quality: str
    ranking_band: str
    reason: str
    peer_scope: str = "published_category"
    strategy_match: str = "FULL"
    decision_use: str = "DECISION_SUPPORT"


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if value:
            self.parts.append(value)


class CnyesPeerRankingClient:
    """Read public, page-level Morningstar peer figures from Cnyes."""

    def __init__(self, *, request: Callable[[str], bytes] | None = None) -> None:
        self._request = request or _download

    def fetch(self, fund_code: str) -> PeerRanking:
        page_code, page_name = CNYES_FUND_PAGES[fund_code]
        url = cnyes_fund_url(page_code, page_name)
        return parse_cnyes_peer_ranking(
            self._request(url),
            fund_code=fund_code,
            source_url=url,
            page_name=page_name,
        )


def cnyes_fund_url(fund_code: str, fund_name: str) -> str:
    return f"https://fund.cnyes.com/detail/{quote(fund_name, safe='')}/{fund_code}"


def parse_cnyes_peer_ranking(
    document: bytes | str,
    *,
    fund_code: str,
    source_url: str,
    page_name: str | None = None,
) -> PeerRanking:
    """Parse only explicitly published peer values; never infer missing data."""

    raw = document.decode("utf-8", errors="replace") if isinstance(document, bytes) else document
    parser = _VisibleText()
    parser.feed(html.unescape(raw))
    text = " ".join(parser.parts)
    text = re.sub(r"\s+", " ", text)
    name = FUND_WATCHLIST[fund_code][0]
    published_name = page_name or name

    category_match = re.search(
        re.escape(published_name) + r"\s+(.{2,80}?)\s*同組基金排行",
        text,
    )
    category = (
        re.sub(r"\s+", "", category_match.group(1)).strip(" #-｜|")
        if category_match
        else None
    )
    date_matches = re.findall(r"更新日期[：:]\s*(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})", text)
    as_of = None
    if date_matches:
        year, month, day = date_matches[0]
        as_of = date(int(year), int(month), int(day)).isoformat()

    peer_section = _section(text, "同組平均", "同組排名")
    rank_section = _section(text, "贏過N%基金", "歷史淨值")
    peer_values = _numbers(peer_section)
    rank_values = [int(value) for value in re.findall(r"(-?\d+(?:\.\d+)?)\s*%", rank_section)]

    if not as_of or len(peer_values) < 5 or len(rank_values) < 5:
        raise ValueError(f"Incomplete Cnyes peer ranking for {fund_code}.")

    p3, p6, p1 = (rank_values[PERIOD_INDEX[key]] for key in ("3m", "6m", "1y"))
    if any(value < 0 or value > 100 for value in (p3, p6, p1)):
        raise ValueError(f"Invalid Cnyes percentile for {fund_code}.")
    scope = PEER_SCOPE_OVERRIDES.get(fund_code, {})
    return PeerRanking(
        fund_code=fund_code,
        fund_name=name,
        source="cnyes_morningstar_published",
        source_url=source_url,
        category=category,
        as_of=as_of,
        percentile_3m=p3,
        percentile_6m=p6,
        percentile_1y=p1,
        peer_average_3m=peer_values[PERIOD_INDEX["3m"]],
        peer_average_6m=peer_values[PERIOD_INDEX["6m"]],
        peer_average_1y=peer_values[PERIOD_INDEX["1y"]],
        data_quality="VALID" if category else "PARTIAL",
        ranking_band=ranking_band(p1),
        reason=(
            "Published Cnyes/Morningstar peer percentile; no local reconstruction."
            if category
            else "Published peer percentile; Cnyes category label unavailable."
        ),
        **scope,
    )


def refresh_peer_rankings(
    client: CnyesPeerRankingClient,
    previous_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Refresh seven records, preserving the last success on source failure."""

    previous = {
        item.get("fund_code"): item
        for item in (previous_payload or {}).get("results", [])
    }
    results: list[PeerRanking] = []
    for fund_code, (fund_name, _, _) in FUND_WATCHLIST.items():
        try:
            results.append(client.fetch(fund_code))
        except Exception as exc:  # One page must not erase six valid records.
            old = previous.get(fund_code)
            if old and old.get("data_quality") != "UNKNOWN":
                results.append(
                    replace(
                        _record_from_dict(old),
                        data_quality="STALE",
                        reason=f"Refresh failed; retained last success: {type(exc).__name__}.",
                    )
                )
            else:
                results.append(
                    PeerRanking(
                        fund_code=fund_code,
                        fund_name=fund_name,
                        source="cnyes_morningstar_published",
                        source_url=cnyes_fund_url(*CNYES_FUND_PAGES[fund_code]),
                        category=None,
                        as_of=None,
                        percentile_3m=None,
                        percentile_6m=None,
                        percentile_1y=None,
                        peer_average_3m=None,
                        peer_average_6m=None,
                        peer_average_1y=None,
                        data_quality="UNKNOWN",
                        ranking_band="UNKNOWN",
                        reason=f"No valid published ranking: {type(exc).__name__}.",
                        **PEER_SCOPE_OVERRIDES.get(fund_code, {}),
                    )
                )
    return peer_ranking_payload(results)


def peer_ranking_payload(results: list[PeerRanking]) -> dict[str, Any]:
    return {
        "schema_version": "1.1",
        "metric": "Onecool Peer Ranking",
        "source_policy": {
            "ssot": "Cnyes published Morningstar peer ranking",
            "funddj": "cross_check_only_not_mixed",
            "missing": "Unknown; no imputation",
        },
        "periods": ["3m", "6m", "1y"],
        "decision_role": "third_layer_manager_selection_quality",
        "scope_policy": {
            "FULL": "published category is suitable for decision support",
            "PARTIAL": "broader category is context only and cannot trigger an action",
        },
        "results": [asdict(item) for item in results],
    }


def ranking_band(percentile: int | None) -> str:
    if percentile is None:
        return "UNKNOWN"
    if percentile >= 75:
        return "LEADING"
    if percentile >= 50:
        return "ABOVE_AVERAGE"
    if percentile >= 25:
        return "BELOW_AVERAGE"
    return "WEAK"


def _section(text: str, start: str, end: str) -> str:
    match = re.search(re.escape(start) + r"(.*?)" + re.escape(end), text)
    return match.group(1) if match else ""


def _numbers(value: str) -> list[float]:
    return [float(item) for item in re.findall(r"(?<![\w])(-?\d+(?:\.\d+)?)\s*%?", value)]


def _record_from_dict(value: dict[str, Any]) -> PeerRanking:
    fields = PeerRanking.__dataclass_fields__
    return PeerRanking(**{key: value.get(key) for key in fields})


def _download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "OnecoolOS/1.0 peer-ranking"})
    with urlopen(request, timeout=60) as response:  # noqa: S310 - fixed Cnyes host.
        return response.read()
