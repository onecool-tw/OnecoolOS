"""Fail a scheduled refresh if Taiwan daily inputs are not synchronized."""
import json
from pathlib import Path


def main():
    data = json.loads(Path("data/market/taiwan_stock_intelligence/daily_context_latest.json").read_text())
    readiness = data.get("report_readiness", {})
    pressure_inputs = data.get("market_pressure_input_readiness", {})
    result = {"report_readiness": readiness, "market_pressure_input_readiness": pressure_inputs}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if (readiness.get("status") == "READY" and pressure_inputs.get("status") == "READY") else 1


if __name__ == "__main__":
    raise SystemExit(main())

