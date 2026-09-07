"""Fetch official TWSE data and publish the Taiwan stock research screen."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.request import Request, urlopen

from onecool_os.market.taiwan_stock_screen import build_taiwan_stock_screen_payload


TWSE = "https://openapi.twse.com.tw/v1"
ENDPOINTS = {
    "prices": f"{TWSE}/exchangeReport/STOCK_DAY_ALL",
    "valuations": f"{TWSE}/exchangeReport/BWIBBU_ALL",
    "revenues": f"{TWSE}/opendata/t187ap05_L",
}
INCOME_ENDPOINTS = tuple(
    f"{TWSE}/opendata/t187ap06_L_{suffix}"
    for suffix in ("ci", "basi", "bd", "fh", "ins", "mim")
)


def fetch_json(url: str, *, attempts: int = 3, timeout: int = 120, expected_type=list):
    """Fetch a TWSE JSON array with bounded retry for the slower MOPS feeds."""

    error = None
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": "OnecoolOS/1.0"})
            with urlopen(request, timeout=timeout) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, expected_type):
                raise ValueError(f"Unexpected TWSE response type: {url}")
            return payload
        except Exception as exc:  # noqa: BLE001 - retry the official feed.
            error = exc
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"TWSE fetch failed after {attempts} attempts: {url}: {error}")


def normalize_dated_report(payload, day, mapping):
    """Map official named columns, never infer a price or valuation."""
    if payload.get("stat") != "OK" or payload.get("date") != day.strftime("%Y%m%d"):
        raise ValueError(f"Official dated report not ready for {day}")
    tables = payload.get("tables", [payload])
    matches = [t for t in tables if set(mapping).issubset(t.get("fields", []))]
    if len(matches) != 1 or not matches[0].get("data"):
        raise ValueError("Missing or ambiguous official report columns")
    table = matches[0]
    rows = []
    for values in table["data"]:
        if len(values) != len(table["fields"]):
            raise ValueError("Malformed official report row")
        row = dict(zip(table["fields"], values))
        rows.append({"Date": day.isoformat(), **{
            target: row[source] for source, target in mapping.items()
        }})
    return rows


def fetch_dated_market(day, fetcher=fetch_json):
    query = day.strftime("%Y%m%d")
    root = "https://www.twse.com.tw/exchangeReport"
    prices = fetcher(f"{root}/MI_INDEX?response=json&date={query}&type=ALLBUT0999", expected_type=dict)
    valuations = fetcher(f"{root}/BWIBBU_d?response=json&date={query}&selectType=ALL", expected_type=dict)
    return (
        normalize_dated_report(prices, day, {
            "證券代號": "Code", "證券名稱": "Name", "收盤價": "ClosingPrice", "成交金額": "TradeValue",
        }),
        normalize_dated_report(valuations, day, {
            "證券代號": "Code", "證券名稱": "Name", "本益比": "PEratio", "股價淨值比": "PBratio",
        }),
    )


def update(data_dir: Path, *, fetcher=fetch_json, market_date=None) -> dict:
    if market_date is not None:
        prices, valuations = fetch_dated_market(market_date, fetcher)
    else:
        prices = fetcher(ENDPOINTS["prices"])
        valuations = fetcher(ENDPOINTS["valuations"])
    revenues = fetcher(ENDPOINTS["revenues"])
    income = []
    for url in INCOME_ENDPOINTS:
        income.extend(fetcher(url))
    payload = build_taiwan_stock_screen_payload(
        prices, valuations, revenues, income
    )
    payload["source_policy"] = "TWSE_DATED_REPORTS" if market_date else "TWSE_OPENAPI"
    data_dir.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        payload, indent=2, ensure_ascii=False, allow_nan=False
    ) + "\n"
    (data_dir / "screen_latest.json").write_text(serialized, encoding="utf-8")
    snapshots = data_dir / "snapshots"
    snapshots.mkdir(exist_ok=True)
    (snapshots / f"{payload['expected_as_of']}.json").write_text(
        serialized, encoding="utf-8"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/market/taiwan_stock_intelligence"),
    )
    args = parser.parse_args()
    now = datetime.now(ZoneInfo("Asia/Taipei"))
    day = now.date()
    if now.hour < 14:
        day -= timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    # If a holiday or delayed publication returns no data, fail without
    # overwriting the last successful snapshot or fabricating a new date.
    print(json.dumps(update(args.data_dir, market_date=day), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
