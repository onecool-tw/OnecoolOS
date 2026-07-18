"""Update the GitHub-cached Onecool Market Dashboard once per week."""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

from onecool_os.market.dashboard import (
    MARKET_SYMBOLS,
    build_dashboard_payload,
    dashboard_record,
)
from onecool_os.market.etf_cta import (
    AlphaVantageClient,
    apply_corporate_actions,
    calculate_cta,
    merge_and_adjust,
    read_history,
    write_history,
)


def update(root: Path, api_key: str) -> dict:
    """Fetch 7 symbols with exactly 3 logical API calls each."""

    data_dir = root / "data" / "market" / "dashboard"
    history_dir = data_dir / "history"
    client = AlphaVantageClient(api_key)
    staged = []
    records = []

    # Fetch and calculate every symbol before replacing any successful cache.
    for config in MARKET_SYMBOLS:
        existing = read_history(history_dir / f"{config.symbol}.csv")
        daily = client.fetch_daily(
            config.provider_symbol,
            outputsize="compact" if existing else "full",
        )
        actions = client.fetch_actions(config.provider_symbol)
        combined = merge_and_adjust(existing, daily)
        history = merge_and_adjust(
            [], apply_corporate_actions(combined, actions, authoritative=True)
        )
        staged.append((config, history))
        records.append(dashboard_record(config, calculate_cta(config.symbol, history)))

    payload = build_dashboard_payload(records)
    for config, history in staged:
        write_history(history_dir / f"{config.symbol}.csv", history)
    data_dir.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    (data_dir / "dashboard_latest.json").write_text(serialized, encoding="utf-8")
    snapshot_date = max(date.fromisoformat(item.as_of) for item in records)
    snapshots = data_dir / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    (snapshots / f"{snapshot_date.isoformat()}.json").write_text(
        serialized, encoding="utf-8"
    )
    print(serialized, end="")
    return payload


if __name__ == "__main__":
    update(Path("."), os.environ.get("ALPHA_VANTAGE_API_KEY", ""))
