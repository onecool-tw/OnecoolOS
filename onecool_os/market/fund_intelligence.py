"""Cache-only inputs for the scheduled Onecool Fund Intelligence report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from onecool_os.market.dashboard import load_latest_dashboard


def load_fund_intelligence_context(root: Path) -> dict[str, Any]:
    """Load Alpha and the latest successful Market Dashboard without I/O calls."""

    alpha_path = root / "data" / "market" / "fund_nav" / "alpha_latest.json"
    alpha = (
        json.loads(alpha_path.read_text(encoding="utf-8"))
        if alpha_path.exists()
        else None
    )
    fund_cta_path = root / "data" / "market" / "fund_nav" / "fund_cta_latest.json"
    fund_cta = (
        json.loads(fund_cta_path.read_text(encoding="utf-8"))
        if fund_cta_path.exists()
        else None
    )
    return {
        "schema_version": "1.1",
        "source_policy": "github_cache_only",
        "fund_alpha": alpha,
        "fund_cta": fund_cta,
        "market_dashboard": load_latest_dashboard(root),
    }
