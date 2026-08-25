"""Refresh the monthly fundamental-cycle cache from official FRED series."""

from pathlib import Path

from onecool_os.market.fundamental_cycle import update_fundamental_cycle_cache


if __name__ == "__main__":
    payload = update_fundamental_cycle_cache(Path("."))
    print(
        "Fundamental Cycle: "
        f"{payload['phase']} / {payload['confidence']} / {payload['data_status']}"
    )
