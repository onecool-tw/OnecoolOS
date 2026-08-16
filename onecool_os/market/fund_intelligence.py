"""Cache-only inputs for the scheduled Onecool Fund Intelligence report."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from onecool_os.market.dashboard import load_latest_dashboard

MASTER_PROMPT_VERSION = "v1.1 Freeze"
MASTER_PROMPT_PATH = Path("config/fund_intelligence_master_prompt.md")


def load_master_prompt(root: Path) -> dict[str, str]:
    """Load and fingerprint the only production Fund Intelligence prompt."""

    path = root / MASTER_PROMPT_PATH
    content = path.read_text(encoding="utf-8")
    if f"版本：{MASTER_PROMPT_VERSION}" not in content:
        raise ValueError("PROMPT_VERSION_MISMATCH")
    return {
        "version": MASTER_PROMPT_VERSION,
        "sha256": sha256(content.encode("utf-8")).hexdigest(),
        "content": content,
    }


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
    peer_path = root / "data" / "market" / "fund_nav" / "peer_ranking_latest.json"
    peer_ranking = (
        json.loads(peer_path.read_text(encoding="utf-8"))
        if peer_path.exists()
        else None
    )
    rotation_path = (
        root / "data" / "market" / "stockq_rotation" / "rotation_latest.json"
    )
    rotation_radar = (
        json.loads(rotation_path.read_text(encoding="utf-8"))
        if rotation_path.exists()
        else None
    )
    sector_path = (
        root / "data" / "market" / "sector_rotation" / "rotation_latest.json"
    )
    sector_rotation = (
        json.loads(sector_path.read_text(encoding="utf-8"))
        if sector_path.exists()
        else None
    )
    ai_path = (
        root / "data" / "market" / "ai_revolution" / "ai_revolution_latest.json"
    )
    ai_revolution = (
        json.loads(ai_path.read_text(encoding="utf-8"))
        if ai_path.exists()
        else None
    )
    validation_path = (
        root / "data" / "market" / "fund_intelligence" / "validation_latest.json"
    )
    validation = (
        json.loads(validation_path.read_text(encoding="utf-8"))
        if validation_path.exists()
        else None
    )
    return {
        "schema_version": "1.4",
        "source_policy": "github_cache_only",
        "master_prompt": load_master_prompt(root),
        "fund_alpha": alpha,
        "fund_cta": fund_cta,
        "peer_ranking": peer_ranking,
        "stockq_rotation_radar": rotation_radar,
        "sector_rotation": sector_rotation,
        "ai_revolution": ai_revolution,
        "data_validation": validation,
        "market_dashboard": load_latest_dashboard(root),
    }
