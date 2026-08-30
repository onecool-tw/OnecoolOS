"""Run the Onecool US-rate versus cross-asset historical study."""

from __future__ import annotations

import json
import argparse
from pathlib import Path

from onecool_os.market.rate_asset_backtest import run_backtest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cached",
        action="store_true",
        help="Recalculate from validated monthly caches without downloading sources.",
    )
    args = parser.parse_args()
    payload = run_backtest(Path("."), refresh_sources=not args.cached)
    print(
        json.dumps(
            {
                "module": payload["module"],
                "assets_valid": payload["asset_count_valid"],
                "assets_expected": payload["asset_count_expected"],
                "provider_errors": payload["provider_errors"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
