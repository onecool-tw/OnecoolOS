"""Preflight validation for committed Onecool Fund Intelligence inputs."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from math import isfinite
from pathlib import Path
from typing import Any


REQUIRED_DASHBOARD_SYMBOLS = {
    "SPY", "QQQ", "RUSSELL_2000", "0050", "VIX", "DXY", "US30Y", "BTC"
}
REQUIRED_FINITE_FIELDS = {
    "current_price", "sma50", "sma200", "weekly_ma30", "weekly_ma50"
}


def _read(root: Path, relative: str) -> dict[str, Any] | None:
    path = root / relative
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _issue(code: str, module: str, detail: str) -> dict[str, str]:
    return {"code": code, "module": module, "detail": detail}


def _business_days_between(start: date, end: date) -> int:
    if start >= end:
        return 0
    return sum(
        1
        for offset in range(1, (end - start).days + 1)
        if date.fromordinal(start.toordinal() + offset).weekday() < 5
    )


def validate_fund_intelligence(root: Path, *, today: date | None = None) -> dict:
    """Validate cache coverage without querying any external provider."""

    now = today or date.today()
    issues: list[dict[str, str]] = []

    dashboard = _read(root, "data/market/dashboard/dashboard_latest.json")
    if not dashboard:
        issues.append(_issue("MISSING_CACHE", "Market Dashboard", "cache missing"))
    else:
        records = {item.get("symbol"): item for item in dashboard.get("results", [])}
        for symbol in sorted(REQUIRED_DASHBOARD_SYMBOLS):
            item = records.get(symbol)
            if not item:
                issues.append(_issue("MISSING_SYMBOL", "Market Dashboard", symbol))
                continue
            invalid = [
                field for field in REQUIRED_FINITE_FIELDS
                if not isinstance(item.get(field), (int, float))
                or not isfinite(float(item[field]))
            ]
            if invalid:
                issues.append(
                    _issue(
                        "NON_FINITE_VALUE", "Market Dashboard",
                        f"{symbol}: {', '.join(sorted(invalid))}",
                    )
                )

    for relative, module in (
        ("data/market/fund_nav/fund_cta_latest.json", "Fund CTA"),
        ("data/market/fund_nav/alpha_latest.json", "Onecool Excess Return"),
        ("data/market/fund_nav/peer_ranking_latest.json", "Peer Ranking"),
    ):
        payload = _read(root, relative)
        if not payload:
            issues.append(_issue("MISSING_CACHE", module, "cache missing"))
        elif len(payload.get("results", [])) != 7:
            issues.append(_issue("INCOMPLETE_COVERAGE", module, "expected 7 funds"))

    peer = _read(root, "data/market/fund_nav/peer_ranking_latest.json") or {}
    for item in peer.get("results", []):
        if item.get("data_quality") in {"UNKNOWN", "STALE"}:
            issues.append(
                _issue(
                    "PEER_RANKING_UNAVAILABLE", "Peer Ranking",
                    f"{item.get('fund_code')}: {item.get('data_quality')}",
                )
            )

    ai = _read(root, "data/market/ai_revolution/ai_revolution_latest.json")
    if not ai:
        issues.append(_issue("MISSING_CACHE", "AI Revolution", "cache missing"))
    else:
        if ai.get("companies_official_evidence_valid") != 6:
            issues.append(
                _issue("INCOMPLETE_COVERAGE", "AI Revolution", "official evidence below 6/6")
            )
        if ai.get("review_required"):
            issues.append(
                _issue("REVIEW_REQUIRED", "AI Revolution", "current revisions are unreviewed")
            )

    sector = _read(root, "data/market/sector_rotation/rotation_latest.json")
    if not sector:
        issues.append(_issue("MISSING_CACHE", "US Sector Rotation", "cache missing"))
    elif len(sector.get("results", [])) != 11:
        issues.append(_issue("INCOMPLETE_COVERAGE", "US Sector Rotation", "expected 11 ETFs"))

    rotation = _read(root, "data/market/stockq_rotation/rotation_latest.json")
    if not rotation:
        issues.append(_issue("MISSING_CACHE", "Global Rotation", "cache missing"))
    else:
        for market in rotation.get("passed_markets", []):
            for period in ("1w", "1m"):
                status = (market.get("twd_returns", {}).get(period) or {}).get("status")
                if status != "VALID":
                    issues.append(
                        _issue(
                            "TWD_CONVERSION_UNAVAILABLE", "Global Rotation",
                            f"{market.get('market')} {period}: {status or 'UNKNOWN'}",
                        )
                    )

    etf = _read(root, "data/market/etf_cta/cta_latest.json") or {}
    wti = next((x for x in etf.get("results", []) if x.get("symbol") == "WTI"), None)
    if not wti or not wti.get("as_of"):
        issues.append(_issue("MISSING_SYMBOL", "ETF CTA", "WTI"))
    else:
        lag = _business_days_between(date.fromisoformat(wti["as_of"]), now)
        if lag > 2:
            issues.append(_issue("STALE_WTI", "ETF CTA", f"WTI is {lag} business days old"))

    if now.day <= 7:
        cycle = _read(
            root,
            "data/market/fundamental_cycle/fundamental_cycle_latest.json",
        )
        if not cycle:
            issues.append(
                _issue("MISSING_CACHE", "Fundamental Cycle", "monthly cache missing")
            )
        else:
            if cycle.get("decision_authority") != "CONTEXT_ONLY":
                issues.append(
                    _issue(
                        "INVALID_AUTHORITY",
                        "Fundamental Cycle",
                        "must remain context only",
                    )
                )
            if cycle.get("phase") not in {
                "RECOVERY", "GROWTH", "BOOM", "RECESSION", "DIVERGENT", "UNKNOWN"
            }:
                issues.append(
                    _issue("INVALID_PHASE", "Fundamental Cycle", "unsupported phase")
                )
            generated_at = cycle.get("generated_at")
            try:
                generated_month = datetime.fromisoformat(generated_at).date().replace(day=1)
            except (TypeError, ValueError):
                generated_month = None
            if generated_month != now.replace(day=1):
                issues.append(
                    _issue("STALE_CACHE", "Fundamental Cycle", "not refreshed this month")
                )

    generated = datetime.now(UTC).isoformat()
    return {
        "schema_version": "1.0",
        "module": "Onecool Fund Intelligence Data Validation",
        "generated_at": generated,
        "status": "PASS" if not issues else "CONDITIONAL_PASS",
        "issue_count": len(issues),
        "issues": issues,
    }
