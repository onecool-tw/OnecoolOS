"""Refresh the StockQ rotation radar cache used by the fund weekly report."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from onecool_os.market.stockq_rotation import (
    STOCKQ_MARKET_URL,
    build_rotation_radar,
    fetch_stockq_html,
)


def update(root: Path) -> dict:
    market_html = fetch_stockq_html(STOCKQ_MARKET_URL)
    match = re.search(
        r"<b>一日</b>.*?([0-9]{2}/[0-9]{2})",
        market_html,
        flags=re.DOTALL,
    )
    as_of = None
    if match:
        month, day = match.group(1).split("/")
        as_of = f"{datetime.now(timezone.utc).year}-{month}-{day}"
    payload = build_rotation_radar(market_html, fetch_stockq_html, as_of=as_of)
    destination = root / "data" / "market" / "stockq_rotation" / "rotation_latest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False))
    return payload


if __name__ == "__main__":
    update(Path("."))
