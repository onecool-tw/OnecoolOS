"""Fetch official TWSE data and publish the Taiwan stock research screen."""

from __future__ import annotations

import argparse
import json
import time
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


def fetch_json(url: str, *, attempts: int = 3, timeout: int = 120) -> list[dict]:
    """Fetch a TWSE JSON array with bounded retry for the slower MOPS feeds."""

    error = None
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": "OnecoolOS/1.0"})
            with urlopen(request, timeout=timeout) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, list):
                raise ValueError(f"TWSE response is not a list: {url}")
            return payload
        except Exception as exc:  # noqa: BLE001 - retry the official feed.
            error = exc
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"TWSE fetch failed after {attempts} attempts: {url}: {error}")


def update(data_dir: Path, *, fetcher=fetch_json) -> dict:
    prices = fetcher(ENDPOINTS["prices"])
    valuations = fetcher(ENDPOINTS["valuations"])
    revenues = fetcher(ENDPOINTS["revenues"])
    income = []
    for url in INCOME_ENDPOINTS:
        income.extend(fetcher(url))
    payload = build_taiwan_stock_screen_payload(
        prices, valuations, revenues, income
    )
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
    print(json.dumps(update(args.data_dir), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
