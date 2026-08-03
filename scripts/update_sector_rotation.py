"""Refresh the committed US Sector Rotation cache."""

from __future__ import annotations

import json
from pathlib import Path

from onecool_os.market.history_bootstrap import YahooHistoryBootstrapper
from onecool_os.market.sector_rotation import (
    SECTOR_ETFS,
    build_sector_rotation_payload,
    calculate_sector_return,
)


def update(
    root: Path, *, bootstrapper: YahooHistoryBootstrapper | None = None
) -> dict:
    provider = bootstrapper or YahooHistoryBootstrapper()
    results = [
        calculate_sector_return(
            symbol, provider.fetch_adjusted_daily(symbol)
        )
        for symbol in SECTOR_ETFS
    ]
    payload = build_sector_rotation_payload(results)
    destination = (
        root / "data" / "market" / "sector_rotation" / "rotation_latest.json"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False))
    return payload


if __name__ == "__main__":
    update(Path("."))
