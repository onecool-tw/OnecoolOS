"""Cache-only context for the Onecool Taiwan stock daily report."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

MASTER_PROMPT_VERSION = "v1.4 Taiwan Broad Screen with Formal Market Pressure"
MASTER_PROMPT_PATH = Path("config/taiwan_stock_intelligence_master_prompt.md")
SCREEN_PATH = Path("data/market/taiwan_stock_intelligence/screen_latest.json")
STOCK_CTA_PATH = Path("data/market/taiwan_stock_intelligence/cta/cta_latest.json")
CONTEXT_PATH = Path("data/market/taiwan_stock_intelligence/daily_context_latest.json")


def _read(root: Path, relative: Path | str) -> dict[str, Any] | None:
    path = root / relative
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _business_day_lag(start: date, end: date) -> int:
    if start >= end:
        return 0
    return sum(
        1
        for offset in range(1, (end - start).days + 1)
        if date.fromordinal(start.toordinal() + offset).weekday() < 5
    )


def _weekly_alignment(item: Mapping[str, Any] | None) -> str:
    if not item:
        return "UNKNOWN"
    alignment = (item.get("weekly_cross") or {}).get("alignment")
    if alignment in {"GOLDEN", "DEATH"}:
        return str(alignment)
    fast = item.get("weekly_30ma", item.get("weekly_ma30"))
    slow = item.get("weekly_50ma", item.get("weekly_ma50"))
    if not isinstance(fast, (int, float)) or not isinstance(slow, (int, float)):
        return "UNKNOWN"
    return "GOLDEN" if fast > slow else "DEATH" if fast < slow else "NEUTRAL"


def _default_market_pressure() -> dict[str, Any]:
    return {
        "as_of": None,
        "status": "UNKNOWN",
        "light": "UNKNOWN",
        "action": "PAUSE_NEW_EXPOSURE",
        "reason": ["formal_market_pressure_not_persisted_yet"],
        "confirmed_inputs": {},
        "input_data_as_of": {},
        "previous_light": None,
        "changed": False,
        "last_change_date": None,
        "data_quality": "MISSING",
    }


def _normalize_market_pressure(item: Mapping[str, Any] | None) -> dict[str, Any]:
    """Preserve a formally persisted pressure result; otherwise fail closed."""

    if not item:
        return _default_market_pressure()

    light = str(item.get("light", "UNKNOWN")).upper()
    status = str(item.get("status", "UNKNOWN")).upper()
    if light not in {"GREEN", "YELLOW", "RED", "UNKNOWN"}:
        light = "UNKNOWN"
    if status not in {"CURRENT", "STALE_LAST_KNOWN", "UNKNOWN"}:
        status = "UNKNOWN"

    normalized = _default_market_pressure()
    normalized.update({
        "as_of": item.get("as_of"),
        "status": status,
        "light": light,
        "action": item.get("action") or (
            "ALLOW_EVALUATE_NEW_EXPOSURE"
            if light == "GREEN" and status == "CURRENT"
            else "PAUSE_NEW_EXPOSURE"
        ),
        "reason": list(item.get("reason") or []),
        "confirmed_inputs": dict(item.get("confirmed_inputs") or {}),
        "input_data_as_of": dict(item.get("input_data_as_of") or {}),
        "previous_light": item.get("previous_light"),
        "changed": bool(item.get("changed", False)),
        "last_change_date": item.get("last_change_date"),
        "data_quality": item.get("data_quality") or (
            "READY" if status == "CURRENT" else "STALE" if status == "STALE_LAST_KNOWN" else "MISSING"
        ),
    })
    if status != "CURRENT" or light != "GREEN":
        normalized["action"] = "PAUSE_NEW_EXPOSURE"
    return normalized


def load_master_prompt(root: Path) -> dict[str, str]:
    content = (root / MASTER_PROMPT_PATH).read_text(encoding="utf-8")
    if f"版本：{MASTER_PROMPT_VERSION}" not in content:
        raise ValueError("TAIWAN_PROMPT_VERSION_MISMATCH")
    return {
        "version": MASTER_PROMPT_VERSION,
        "sha256": sha256(content.encode("utf-8")).hexdigest(),
        "content": content,
    }


def build_taiwan_stock_daily_context(
    root: Path,
    *,
    today: date | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Expose the latest successful screen with explicit CTA/action gates."""

    current_date = today or date.today()
    screen = _read(root, SCREEN_PATH)
    stock_cta = _read(root, STOCK_CTA_PATH) or {}
    previous_context = _read(root, CONTEXT_PATH) or {}
    market_pressure = _normalize_market_pressure(previous_context.get("market_pressure"))
    stock_cta_items = {
        str(item.get("symbol")): item for item in stock_cta.get("results", [])
    }
    taiwan_cta = _read(root, "data/market/taiwan_cta/cta_latest.json") or {}
    cta_items = {
        str(item.get("symbol")): item for item in taiwan_cta.get("results", [])
    }
    weekly_0050 = _weekly_alignment(cta_items.get("0050"))

    if not screen:
        lag = None
        display_status = "MISSING"
        top5: list[dict[str, Any]] = []
        screen_as_of = None
    else:
        screen_as_of = screen.get("expected_as_of")
        try:
            lag = _business_day_lag(date.fromisoformat(screen_as_of), current_date)
        except (TypeError, ValueError):
            lag = None
        display_status = "CURRENT" if lag is not None and lag <= 1 else "STALE"
        top5 = [dict(item) for item in screen.get("top5", [])]

    if display_status != "CURRENT":
        eligibility = "WATCH_ONLY_STALE_OR_MISSING_SCREEN"
    elif weekly_0050 == "DEATH":
        eligibility = "WATCH_ONLY_0050_WEEKLY_BEARISH"
    elif weekly_0050 == "GOLDEN":
        eligibility = "REQUIRES_INDIVIDUAL_CTA_AND_PRESSURE_GREEN"
    else:
        eligibility = "WATCH_ONLY_0050_CTA_UNKNOWN"

    for item in top5:
        item["candidate_role"] = "RESEARCH_PRIORITY_ONLY"
        item["individual_cta_required"] = True
        individual = stock_cta_items.get(str(item.get("symbol")))
        item["individual_cta"] = _individual_cta_context(individual)
        item["action_eligibility"] = _individual_action_eligibility(
            eligibility, individual
        )

    timestamp = generated_at or datetime.now(UTC)
    return {
        "schema_version": "1.3",
        "module": "Onecool Taiwan Stock Daily Context",
        "generated_at": timestamp.isoformat(),
        "source_policy": "LATEST_SUCCESSFUL_SCREEN_WITH_EXPLICIT_DATE",
        "screen_as_of": screen_as_of,
        "screen_business_day_lag": lag,
        "display_status": display_status,
        "screen_data_status": (screen or {}).get("data_status", "MISSING"),
        "0050_weekly_alignment": weekly_0050,
        "market_pressure_gate": "FORMAL_FROM_DAILY_CONTEXT",
        "market_pressure": market_pressure,
        "candidate_action_gate": eligibility,
        "candidate_cta_cache": {
            "screen_as_of": stock_cta.get("screen_as_of"),
            "generated_at": stock_cta.get("generated_at"),
            "requested_count": stock_cta.get("requested_count", 0),
            "coverage": stock_cta.get("coverage", {
                "current": 0, "stale_last_known": 0, "unknown": 0,
            }),
            "ranking_authority": "NONE",
        },
        "optional_quality_research": {
            "framework": "SUPER_GROWTH_QUALITY",
            "authority": "NONE",
            "application": "MANUAL_ON_REQUEST_ONLY",
            "policy": "NEVER_BLOCK_OR_PROMOTE_A_TAIWAN_CANDIDATE_AUTOMATICALLY",
        },
        "top5": top5,
        "authority_order": [
            "WEEKLY_CTA", "DAILY_CTA", "MARKET_PRESSURE",
            "TAIWAN_CANDIDATE_POOL", "MACRO_CONFIRMATION",
        ],
        "decision_authority": "RESEARCH_PRIORITY_ONLY",
        "stale_policy": "DISPLAY_LATEST_WITH_AS_OF; NEVER_TRADE_FROM_STALE_SCREEN",
        "master_prompt": load_master_prompt(root),
    }


def update_taiwan_stock_daily_context(root: Path) -> dict[str, Any]:
    payload = build_taiwan_stock_daily_context(root)
    destination = root / CONTEXT_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return payload


def load_taiwan_stock_daily_context(root: Path) -> dict[str, Any] | None:
    return _read(root, CONTEXT_PATH)


def _individual_cta_context(item: Mapping[str, Any] | None) -> dict[str, Any]:
    if not item:
        return {
            "update_status": "UNKNOWN",
            "as_of": None,
            "state": "UNKNOWN",
            "cta": "UNKNOWN",
            "daily_cross": None,
            "weekly_cross": None,
            "reason": "Symbol is not available in the background CTA cache.",
        }
    return {
        key: item.get(key)
        for key in (
            "update_status", "as_of", "state", "cta", "reason",
            "source_data_as_of", "weekly_data_as_of",
            "daily_50ma", "daily_200ma", "weekly_30ma", "weekly_50ma",
            "daily_cross", "weekly_cross", "last_attempt_at", "error",
        )
    }


def _individual_action_eligibility(
    market_gate: str, item: Mapping[str, Any] | None
) -> str:
    if market_gate != "REQUIRES_INDIVIDUAL_CTA_AND_PRESSURE_GREEN":
        return market_gate
    if not item or item.get("update_status") == "UNKNOWN":
        return "WATCH_ONLY_INDIVIDUAL_CTA_UNKNOWN"
    if item.get("update_status") != "CURRENT":
        return "WATCH_ONLY_INDIVIDUAL_CTA_STALE"
    return str(item.get("action", "WATCH_ONLY_INDIVIDUAL_CTA_UNKNOWN"))
