"""Refresh seven fund NAV histories and publish the daily Fund CTA cache."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from onecool_os.market.fund_alpha import (
    FUND_WATCHLIST,
    AnueFundClient,
    merge_nav_history,
    read_nav_history,
    write_nav_history,
)
from onecool_os.market.fund_cta import calculate_fund_cta, fund_cta_payload


AUXILIARY_SYMBOLS = {
    "B23554": "GLD",
    "B23070": "WTI",
}


def update(
    root: Path,
    *,
    client: AnueFundClient | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Fetch NAV once per fund and update CTA without weekly report modules."""

    fund_dir = root / "data" / "market" / "fund_nav"
    nav_client = client or AnueFundClient()
    benchmark_path = root / "data" / "market" / "etf_cta" / "cta_latest.json"
    benchmark_payload = (
        json.loads(benchmark_path.read_text(encoding="utf-8"))
        if benchmark_path.exists()
        else {"results": []}
    )
    benchmark_records = {
        item["symbol"]: item for item in benchmark_payload.get("results", [])
    }

    # Complete all provider reads first. A single failed fund must not publish a
    # mixed-date, partially refreshed daily cache.
    histories = {}
    for fund_code in FUND_WATCHLIST:
        path = fund_dir / "history" / f"{fund_code}.csv"
        histories[fund_code] = merge_nav_history(
            read_nav_history(path),
            nav_client.fetch_history(fund_code),
        )

    results = []
    for fund_code, (_, benchmark, _) in FUND_WATCHLIST.items():
        auxiliary_symbol = AUXILIARY_SYMBOLS.get(fund_code)
        results.append(
            calculate_fund_cta(
                fund_code,
                histories[fund_code],
                benchmark_cta=(
                    benchmark_records.get(benchmark) or {}
                ).get("cta"),
                auxiliary_signal=benchmark_records.get(auxiliary_symbol or ""),
            )
        )

    for fund_code, history in histories.items():
        write_nav_history(
            fund_dir / "history" / f"{fund_code}.csv",
            history,
        )

    payload = fund_cta_payload(results)
    payload["generated_at"] = generated_at or datetime.now(timezone.utc).isoformat()
    payload["update_mode"] = "DAILY_NAV_CTA_ONLY"
    payload["nav_provider"] = "Anue Fund public NavHIS"
    fund_dir.mkdir(parents=True, exist_ok=True)
    (fund_dir / "fund_cta_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False))
    return payload


if __name__ == "__main__":
    update(Path("."))
