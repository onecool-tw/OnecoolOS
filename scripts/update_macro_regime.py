"""Refresh the deterministic weekly Market Regime cache."""

from __future__ import annotations

import json
from pathlib import Path

from onecool_os.market.macro_regime import update_macro_regime_cache


def main() -> int:
    payload = update_macro_regime_cache(Path("."))
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
