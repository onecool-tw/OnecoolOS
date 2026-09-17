#!/usr/bin/env python3
"""Refresh official margin and VIX inputs; never calculate a pressure light."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from onecool_os.market.taiwan_market_inputs import (
    collect_market_pressure_inputs,
    write_market_pressure_inputs,
)


def expected_as_of(root: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    screen = root / "data/market/taiwan_stock_intelligence/screen_latest.json"
    if screen.exists():
        value = json.loads(screen.read_text(encoding="utf-8")).get("expected_as_of")
        if value:
            return str(value)
    return datetime.now(ZoneInfo("Asia/Taipei")).date().isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--as-of")
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--interval-seconds", type=int, default=0)
    args = parser.parse_args()
    as_of = expected_as_of(args.root, args.as_of)
    payload = collect_market_pressure_inputs(
        as_of, attempts=args.attempts, interval_seconds=args.interval_seconds
    )
    write_market_pressure_inputs(args.root, payload)
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
