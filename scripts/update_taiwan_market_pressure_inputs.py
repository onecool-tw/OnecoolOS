#!/usr/bin/env python3
"""Refresh official margin and VIX inputs; never calculate a pressure light."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from onecool_os.market.taiwan_calendar import latest_twse_session
from onecool_os.market.taiwan_market_inputs import (
    collect_market_pressure_inputs,
    write_market_pressure_inputs,
)


def expected_as_of(root: Path, explicit: str | None, *, now: datetime | None = None) -> str:
    """Use the completed TWSE session, independent of the last valid Screen.

    A failed Screen refresh must not make the pressure-input adapter request
    yesterday's VIX and margin data indefinitely.
    """
    if explicit:
        return explicit
    now = now or datetime.now(ZoneInfo("Asia/Taipei"))
    day = now.date()
    if now.hour < 14:
        day -= timedelta(days=1)
    return latest_twse_session(day).isoformat()


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
