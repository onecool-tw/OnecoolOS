"""Fail a scheduled refresh if Taiwan daily inputs are not synchronized."""
import json
from pathlib import Path


def main():
    data = json.loads(Path("data/market/taiwan_stock_intelligence/daily_context_latest.json").read_text())
    readiness = data.get("report_readiness", {})
    print(json.dumps(readiness, ensure_ascii=False))
    return 0 if readiness.get("status") == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
