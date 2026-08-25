"""Deterministic market-implied regime and macro-confirmation context.

The module reuses committed CTA caches.  It does not fetch data, size a
position, or override the weekly-first Onecool CTA hierarchy.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping


CACHE_PATH = Path("data/market/macro_regime/macro_regime_latest.json")
SNAPSHOT_DIR = Path("data/market/macro_regime/snapshots")


def _records(payload: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    return {
        str(item.get("symbol")): item
        for item in (payload or {}).get("results", [])
        if item.get("symbol")
    }


def _weekly_alignment(item: Mapping[str, Any] | None) -> str:
    if not item:
        return "UNKNOWN"
    alignment = (item.get("weekly_cross") or {}).get("alignment")
    if alignment in {"GOLDEN", "DEATH"}:
        return str(alignment)
    fast = item.get("weekly_ma30", item.get("weekly_30ma"))
    slow = item.get("weekly_ma50", item.get("weekly_50ma"))
    if not isinstance(fast, (int, float)) or not isinstance(slow, (int, float)):
        return "UNKNOWN"
    if fast > slow:
        return "GOLDEN"
    if fast < slow:
        return "DEATH"
    return "NEUTRAL"


def _pair_state(left: str, right: str, positive: str, negative: str) -> str:
    if "UNKNOWN" in {left, right}:
        return "UNKNOWN"
    if left == right == "DEATH":
        return positive
    if left == right == "GOLDEN":
        return negative
    return "MIXED"


def _fundamental_bias(fundamental_cycle: Mapping[str, Any] | None) -> str:
    phase = (fundamental_cycle or {}).get("phase")
    if phase in {"RECOVERY", "GROWTH", "BOOM"}:
        return "POSITIVE"
    if phase == "RECESSION":
        return "NEGATIVE"
    if phase == "DIVERGENT":
        return "MIXED"
    return "UNKNOWN"


def _macro_confirmation(market_bias: str, fundamental_bias: str) -> tuple[str, str]:
    if market_bias == fundamental_bias == "POSITIVE":
        return "ALIGNED_POSITIVE", "提高多頭信心；實際行動仍依CTA"
    if market_bias == "POSITIVE" and fundamental_bias == "NEGATIVE":
        return "MARKET_LEADS_DIVERGENT", "CTA照常；新增部位採保守節奏"
    if market_bias == "NEGATIVE" and fundamental_bias == "POSITIVE":
        return "FUNDAMENTALS_LEAD_DIVERGENT", "等待週線CTA翻多；不得提前重押"
    if market_bias == fundamental_bias == "NEGATIVE":
        return "ALIGNED_DEFENSIVE", "降低新增風險曝險；不得由總經單獨賣出"
    if "UNKNOWN" in {market_bias, fundamental_bias}:
        return "UNKNOWN", "資料不足；維持CTA原判斷"
    return "MIXED_DIVERGENT", "方向分歧；維持CTA原判斷"


def build_macro_regime_payload(
    dashboard: Mapping[str, Any],
    etf_cta: Mapping[str, Any],
    fundamental_cycle: Mapping[str, Any] | None,
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Calculate the frozen Market Regime and its fundamental confirmation."""

    items = _records(dashboard)
    etf_items = _records(etf_cta)
    alignments = {
        symbol: _weekly_alignment(items.get(symbol))
        for symbol in ("SPY", "QQQ", "RUSSELL_2000", "0050", "VIX", "DXY", "US30Y", "BTC")
    }
    alignments["WTI"] = _weekly_alignment(etf_items.get("WTI"))

    liquidity = _pair_state(
        alignments["DXY"], alignments["US30Y"], "SUPPORTIVE", "RESTRICTIVE"
    )

    growth_inputs = [alignments[symbol] for symbol in ("SPY", "QQQ", "RUSSELL_2000")]
    if "UNKNOWN" in growth_inputs:
        growth = "UNKNOWN"
    elif growth_inputs.count("GOLDEN") >= 2:
        growth = "EXPANDING"
    elif growth_inputs.count("DEATH") >= 2:
        growth = "WEAKENING"
    else:
        growth = "MIXED"

    inflation = _pair_state(
        alignments["WTI"], alignments["US30Y"], "EASING", "PRESSURE"
    )

    risk_inputs = [alignments[symbol] for symbol in ("SPY", "QQQ", "BTC")]
    if "UNKNOWN" in risk_inputs or alignments["VIX"] == "UNKNOWN":
        risk_appetite = "UNKNOWN"
    elif risk_inputs.count("GOLDEN") >= 2 and alignments["VIX"] == "DEATH":
        risk_appetite = "STRONG"
    elif risk_inputs.count("DEATH") >= 2 and alignments["VIX"] == "GOLDEN":
        risk_appetite = "WEAK"
    else:
        risk_appetite = "MIXED"

    if liquidity == "SUPPORTIVE" and risk_appetite == "STRONG":
        scenario = "A LIQUIDITY RISK-ON"
    elif growth == "EXPANDING" and risk_appetite == "STRONG":
        scenario = "B GROWTH EXPANSION"
    elif inflation == "PRESSURE" and growth != "WEAKENING":
        scenario = "C INFLATION / LATE CYCLE"
    elif liquidity == "RESTRICTIVE" and risk_appetite == "WEAK":
        scenario = "D DEFENSIVE STRESS"
    elif "UNKNOWN" in {liquidity, growth, inflation, risk_appetite}:
        scenario = "UNKNOWN"
    else:
        scenario = "MIXED / DIVERGENT"

    market_bias = (
        "POSITIVE" if scenario.startswith(("A ", "B "))
        else "NEGATIVE" if scenario.startswith("D ")
        else "MIXED" if scenario != "UNKNOWN"
        else "UNKNOWN"
    )
    fundamental_bias = _fundamental_bias(fundamental_cycle)
    confirmation, guidance = _macro_confirmation(market_bias, fundamental_bias)

    taiwan_weekly = alignments["0050"]
    if taiwan_weekly == "GOLDEN" and confirmation == "ALIGNED_POSITIVE":
        taiwan_posture = "CTA_BULLISH_NORMAL"
    elif taiwan_weekly == "GOLDEN":
        taiwan_posture = "CTA_BULLISH_CAUTIOUS_NEW_EXPOSURE"
    elif taiwan_weekly == "DEATH" and confirmation == "ALIGNED_DEFENSIVE":
        taiwan_posture = "CTA_BEARISH_DEFENSIVE"
    elif taiwan_weekly == "DEATH":
        taiwan_posture = "WATCH_ONLY_WAIT_WEEKLY_CTA"
    else:
        taiwan_posture = "UNKNOWN"

    timestamp = generated_at or datetime.now(UTC)
    source_dates = {
        symbol: (items.get(symbol) or etf_items.get(symbol) or {}).get("as_of")
        for symbol in alignments
    }
    known = sum(value != "UNKNOWN" for value in alignments.values())
    return {
        "schema_version": "1.0",
        "module": "Onecool Deterministic Macro Regime",
        "generated_at": timestamp.isoformat(),
        "data_status": "READY" if known == len(alignments) else "PARTIAL",
        "decision_authority": "CONTEXT_ONLY",
        "authority_order": [
            "WEEKLY_CTA", "DAILY_CTA", "MARKET_PRESSURE",
            "TAIWAN_CANDIDATE_POOL", "MACRO_CONFIRMATION",
        ],
        "weekly_alignments": alignments,
        "source_as_of": source_dates,
        "market_regime": {
            "liquidity": liquidity,
            "market_implied_growth": growth,
            "inflation": inflation,
            "risk_appetite": risk_appetite,
            "primary_scenario": scenario,
            "market_bias": market_bias,
        },
        "fundamental_cycle": {
            "phase": (fundamental_cycle or {}).get("phase", "UNKNOWN"),
            "confidence": (fundamental_cycle or {}).get("confidence", "LOW"),
            "bias": fundamental_bias,
            "as_of": (fundamental_cycle or {}).get("data_as_of"),
        },
        "macro_confirmation": confirmation,
        "operating_guidance": guidance,
        "taiwan_operating_posture": taiwan_posture,
        "allocation_policy": "QUALITATIVE_ONLY_NO_PERCENTAGES",
        "cta_override_allowed": False,
    }


def update_macro_regime_cache(root: Path) -> dict[str, Any]:
    """Read committed inputs and atomically publish one weekly regime cache."""

    def read(relative: str) -> dict[str, Any] | None:
        path = root / relative
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    dashboard = read("data/market/dashboard/dashboard_latest.json")
    etf_cta = read("data/market/etf_cta/cta_latest.json")
    if not dashboard or not etf_cta:
        raise ValueError("Market Dashboard and ETF CTA caches are required")
    payload = build_macro_regime_payload(
        dashboard,
        etf_cta,
        read("data/market/fundamental_cycle/fundamental_cycle_latest.json"),
    )
    destination = root / CACHE_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(serialized, encoding="utf-8")
    temporary.replace(destination)
    snapshot_date = payload["generated_at"][:10]
    snapshot = root / SNAPSHOT_DIR / f"{snapshot_date}.json"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(serialized, encoding="utf-8")
    return payload


def load_macro_regime(root: Path) -> dict[str, Any] | None:
    path = root / CACHE_PATH
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
