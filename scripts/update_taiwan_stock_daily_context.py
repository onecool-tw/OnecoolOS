"""Publish the Taiwan daily-report context from the latest successful caches."""

from __future__ import annotations

import json
from pathlib import Path

from onecool_os.market.taiwan_stock_intelligence import (
    update_taiwan_stock_daily_context,
)


def main() -> int:
    payload = update_taiwan_stock_daily_context(Path("."))
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
