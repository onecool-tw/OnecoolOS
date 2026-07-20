"""Update seven fund NAV histories and same-date CTA-proxy excess return."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from onecool_os.market.etf_cta import read_history
from onecool_os.market.fund_alpha import (
    FUND_WATCHLIST,
    AnueFundClient,
    alpha_payload,
    calculate_excess_return,
    completed_month_snapshots,
    merge_nav_history,
    read_nav_history,
    write_nav_history,
)


def update(root: Path) -> dict:
    """Refresh fund histories and calculate excess return from ETF data."""

    fund_dir = root / "data" / "market" / "fund_nav"
    etf_dir = root / "data" / "market" / "etf_cta" / "history"
    client = AnueFundClient()
    current = []
    monthly = {}

    for fund_code, (_, benchmark, _) in FUND_WATCHLIST.items():
        nav_path = fund_dir / "history" / f"{fund_code}.csv"
        fund_history = merge_nav_history(
            read_nav_history(nav_path), client.fetch_history(fund_code)
        )
        write_nav_history(nav_path, fund_history)

        etf_history = read_history(etf_dir / f"{benchmark}.csv")
        result = calculate_excess_return(
            fund_code, fund_history, etf_history
        )
        current.append(result)
        monthly[fund_code] = completed_month_snapshots(
            fund_code,
            fund_history,
            etf_history,
            as_of=date.fromisoformat(result.end_date)
            if result.end_date
            else date.today(),
        )

    payload = alpha_payload(current, monthly)
    fund_dir.mkdir(parents=True, exist_ok=True)
    (fund_dir / "alpha_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False))
    return payload


if __name__ == "__main__":
    update(Path("."))
