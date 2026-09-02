#!/usr/bin/env python3
"""Persist an already-evaluated Taiwan market pressure result into daily_context.

This script is deliberately NOT a market-pressure calculation engine. The formal
Taiwan Work remains the sole evaluator of GREEN/YELLOW/RED. This adapter only
validates and atomically persists that formal result into the shared SSOT:

data/market/taiwan_stock_intelligence/daily_context_latest.json.market_pressure
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from onecool_os.market.taiwan_stock_intelligence import CONTEXT_PATH

ALLOWED_LIGHTS = {"GREEN", "YELLOW", "RED", "UNKNOWN"}
ALLOWED_STATUSES = {"CURRENT", "STALE_LAST_KNOWN", "UNKNOWN"}
REQUIRED_GREEN_INPUTS = {
    "spot",
    "futures",
    "pcr",
    "volatility",
    "institutional_flow",
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing daily context: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("DAILY_CONTEXT_NOT_OBJECT")
    return payload


def _validate_iso_date(value: Any, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field.upper()}_NOT_STRING")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field.upper()}_INVALID_DATE") from exc
    return value


def _normalize_reason(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError("REASON_MUST_BE_NONEMPTY_STRING_LIST")
    return [item.strip() for item in value]


def _normalize_mapping(value: Any, *, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{field.upper()}_MUST_BE_OBJECT")
    return dict(value)


def normalize_formal_pressure(
    incoming: Mapping[str, Any],
    previous: Mapping[str, Any] | None,
) -> dict[str, Any]:
    light = str(incoming.get("light", "UNKNOWN")).upper()
    status = str(incoming.get("status", "UNKNOWN")).upper()
    if light not in ALLOWED_LIGHTS:
        raise ValueError(f"INVALID_LIGHT:{light}")
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"INVALID_STATUS:{status}")

    as_of = _validate_iso_date(incoming.get("as_of"), field="as_of")
    reason = _normalize_reason(incoming.get("reason"))
    confirmed_inputs = _normalize_mapping(incoming.get("confirmed_inputs"), field="confirmed_inputs")
    input_data_as_of = _normalize_mapping(incoming.get("input_data_as_of"), field="input_data_as_of")

    if status == "CURRENT":
        if not as_of:
            raise ValueError("CURRENT_REQUIRES_AS_OF")
        if light == "UNKNOWN":
            raise ValueError("CURRENT_CANNOT_HAVE_UNKNOWN_LIGHT")

    # Fail closed: GREEN is only valid when all core pressure inputs are explicitly
    # confirmed. The evaluator may provide additional inputs (e.g. margin/borrow).
    if status == "CURRENT" and light == "GREEN":
        missing = sorted(
            key for key in REQUIRED_GREEN_INPUTS if confirmed_inputs.get(key) is not True
        )
        if missing:
            raise ValueError("GREEN_MISSING_CONFIRMED_INPUTS:" + ",".join(missing))

    previous_light = None
    previous_last_change_date = None
    if previous:
        prior_light = str(previous.get("light", "UNKNOWN")).upper()
        if prior_light in ALLOWED_LIGHTS:
            previous_light = prior_light
        previous_last_change_date = previous.get("last_change_date")

    changed = previous_light is not None and previous_light != light
    if previous_light is None:
        changed = False

    last_change_date = (
        as_of
        if changed
        else incoming.get("last_change_date") or previous_last_change_date
    )
    if last_change_date is not None:
        _validate_iso_date(last_change_date, field="last_change_date")

    action = (
        "ALLOW_EVALUATE_NEW_EXPOSURE"
        if status == "CURRENT" and light == "GREEN"
        else "PAUSE_NEW_EXPOSURE"
    )
    data_quality = (
        "READY"
        if status == "CURRENT"
        else "STALE"
        if status == "STALE_LAST_KNOWN"
        else "MISSING"
    )

    return {
        "as_of": as_of,
        "status": status,
        "light": light,
        "action": action,
        "reason": reason,
        "confirmed_inputs": confirmed_inputs,
        "input_data_as_of": input_data_as_of,
        "previous_light": previous_light,
        "changed": changed,
        "last_change_date": last_change_date,
        "data_quality": data_quality,
    }


def persist(root: Path, incoming: Mapping[str, Any]) -> dict[str, Any]:
    destination = root / CONTEXT_PATH
    context = _read_json(destination)
    previous = context.get("market_pressure")
    if previous is not None and not isinstance(previous, Mapping):
        raise ValueError("EXISTING_MARKET_PRESSURE_NOT_OBJECT")

    normalized = normalize_formal_pressure(incoming, previous)
    context["market_pressure_gate"] = "FORMAL_FROM_DAILY_CONTEXT"
    context["market_pressure"] = normalized

    temporary = destination.with_suffix(".market-pressure.tmp")
    temporary.write_text(
        json.dumps(context, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)

    # Read-after-write verification is intentional: consumers should never be told
    # the formal pressure was updated unless the SSOT actually contains it.
    verified = _read_json(destination).get("market_pressure")
    if verified != normalized:
        raise RuntimeError("MARKET_PRESSURE_WRITE_VERIFICATION_FAILED")
    return normalized


def _load_payload(args: argparse.Namespace) -> dict[str, Any]:
    if bool(args.payload_file) == bool(args.payload_json):
        raise ValueError("PROVIDE_EXACTLY_ONE_OF_PAYLOAD_FILE_OR_PAYLOAD_JSON")
    if args.payload_file:
        value = json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
    else:
        value = json.loads(args.payload_json)
    if not isinstance(value, dict):
        raise ValueError("PAYLOAD_MUST_BE_OBJECT")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload-file")
    parser.add_argument("--payload-json")
    args = parser.parse_args()
    normalized = persist(ROOT, _load_payload(args))
    print(json.dumps(normalized, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
