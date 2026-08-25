"""Refresh US quality annotations from existing validated cache files."""

from __future__ import annotations

import json
from pathlib import Path

from onecool_os.market.us_stock_quality import apply_us_super_growth_quality_gate


def _write_json(path: Path, payload: dict) -> None:
    serialized = json.dumps(
        payload, ensure_ascii=False, indent=2, allow_nan=False
    ) + "\n"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(serialized, encoding="utf-8")
    temporary.replace(path)


def update(root: Path) -> dict:
    intelligence = root / "data" / "market" / "us_stock_intelligence"
    scan_path = intelligence / "breakout_scan_latest.json"
    evidence_path = intelligence / "super_growth_evidence_latest.json"
    scan = json.loads(scan_path.read_text(encoding="utf-8"))
    evidence = (
        json.loads(evidence_path.read_text(encoding="utf-8"))
        if evidence_path.exists()
        else None
    )
    enriched = apply_us_super_growth_quality_gate(scan, evidence)
    _write_json(scan_path, enriched)

    dashboard_path = root / "data" / "market" / "dashboard" / "dashboard_latest.json"
    if dashboard_path.exists():
        dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
        dashboard["daily_top5_scan"] = enriched
        _write_json(dashboard_path, dashboard)
    return enriched


def main() -> int:
    payload = update(Path("."))
    print(json.dumps(payload, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
