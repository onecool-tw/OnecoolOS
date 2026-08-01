"""Refresh seven fund NAV histories and publish the daily Fund CTA cache."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from onecool_os.market.etf_cta import ETFCTAError
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
    """Refresh each fund independently and retain valid NAV on failures."""

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

    histories: dict[str, Any] = {}
    refresh_by_fund: dict[str, dict[str, Any]] = {}
    failed_reads = 0
    missing_history = []

    for fund_code in FUND_WATCHLIST:
        path = fund_dir / "history" / f"{fund_code}.csv"
        existing = read_nav_history(path)
        previous_date = existing[-1].nav_date if existing else None
        try:
            incoming = nav_client.fetch_history(fund_code)
            history = merge_nav_history(existing, incoming)
            latest_date = history[-1].nav_date if history else None
            status = (
                "UPDATED"
                if latest_date is not None
                and (previous_date is None or latest_date > previous_date)
                else "NO_NEW_NAV"
            )
            refresh_by_fund[fund_code] = {
                "status": status,
                "provider_read": "SUCCESS",
                "previous_nav_date": (
                    previous_date.isoformat() if previous_date else None
                ),
                "effective_nav_date": (
                    latest_date.isoformat() if latest_date else None
                ),
                "error": None,
            }
        except Exception as exc:  # provider errors must remain fund-scoped
            failed_reads += 1
            history = existing
            latest_date = history[-1].nav_date if history else None
            refresh_by_fund[fund_code] = {
                "status": "FALLBACK_EXISTING",
                "provider_read": "FAILED",
                "previous_nav_date": (
                    previous_date.isoformat() if previous_date else None
                ),
                "effective_nav_date": (
                    latest_date.isoformat() if latest_date else None
                ),
                "error": f"{type(exc).__name__}: {exc}",
            }
            print(
                f"::warning::NAV refresh failed for {fund_code}; "
                f"using {latest_date or 'no existing NAV'}: {exc}"
            )
        histories[fund_code] = history
        if not history:
            missing_history.append(fund_code)

    if failed_reads == len(FUND_WATCHLIST):
        raise ETFCTAError(
            "All seven fund NAV provider reads failed; no cache was published."
        )
    if missing_history:
        raise ETFCTAError(
            "No valid existing NAV history for: " + ", ".join(missing_history)
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
    for item in payload["results"]:
        item["nav_refresh"] = refresh_by_fund[item["fund_code"]]
    payload["generated_at"] = generated_at or datetime.now(timezone.utc).isoformat()
    payload["update_mode"] = "DAILY_NAV_CTA_ONLY"
    payload["nav_provider"] = "Anue Fund public NavHIS"
    payload["nav_refresh"] = {
        "status": "PARTIAL" if failed_reads else "COMPLETE",
        "successful_provider_reads": len(FUND_WATCHLIST) - failed_reads,
        "failed_provider_reads": failed_reads,
        "funds": refresh_by_fund,
    }
    fund_dir.mkdir(parents=True, exist_ok=True)
    (fund_dir / "fund_cta_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False))
    return payload


if __name__ == "__main__":
    update(Path("."))
