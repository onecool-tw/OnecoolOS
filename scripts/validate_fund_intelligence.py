"""Write a cache-only Fund Intelligence preflight result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from onecool_os.market.fund_intelligence_validation import (
    validate_fund_intelligence,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    payload = validate_fund_intelligence(Path("."))
    destination = (
        Path("data/market/fund_intelligence/validation_latest.json")
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False))
    return 1 if args.strict and payload["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
