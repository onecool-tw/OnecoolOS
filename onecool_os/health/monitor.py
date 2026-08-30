"""Unified health checks for the scheduled OnecoolOS data pipeline.

This module only evaluates data readiness.  It does not change CTA signals,
rankings, or investment decisions.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo


READY = "READY"
PARTIAL = "PARTIAL"
BLOCKED = "BLOCKED"
_ORDER = {READY: 0, PARTIAL: 1, BLOCKED: 2}


@dataclass(frozen=True)
class ModuleHealth:
    module_id: str
    label: str
    scope: str
    critical: bool
    status: str
    reason: str
    observed_as_of: str | None
    recovery_workflow: str | None
    retryable: bool
    impacted_reports: list[str]


def _load(root: Path, relative: str) -> dict[str, Any] | None:
    path = root / relative
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def _date(value: Any) -> date | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None


def _business_lag(observed: date, today: date) -> int:
    if observed >= today:
        return 0
    cursor = observed + timedelta(days=1)
    lag = 0
    while cursor <= today:
        if cursor.weekday() < 5:
            lag += 1
        cursor += timedelta(days=1)
    return lag


def _max_date(values: Iterable[Any]) -> date | None:
    parsed = [item for item in (_date(value) for value in values) if item]
    return max(parsed) if parsed else None


def _module(
    module_id: str,
    label: str,
    scope: str,
    critical: bool,
    status: str,
    reason: str,
    observed: date | None,
    recovery: str | None,
    reports: list[str],
    *,
    retryable: bool = True,
) -> ModuleHealth:
    return ModuleHealth(
        module_id=module_id,
        label=label,
        scope=scope,
        critical=critical,
        status=status,
        reason=reason,
        observed_as_of=observed.isoformat() if observed else None,
        recovery_workflow=recovery,
        retryable=retryable and bool(recovery),
        impacted_reports=reports,
    )


def _daily_check(
    root: Path,
    today: date,
    *,
    module_id: str,
    label: str,
    scope: str,
    relative: str,
    date_field: str,
    status_field: str | None,
    good_statuses: set[str],
    recovery: str,
    reports: list[str],
    max_business_lag: int = 2,
) -> ModuleHealth:
    payload = _load(root, relative)
    if payload is None:
        return _module(module_id, label, scope, True, BLOCKED, "cache missing or invalid", None, recovery, reports)
    observed = _date(payload.get(date_field))
    if observed is None:
        return _module(module_id, label, scope, True, BLOCKED, f"{date_field} missing", None, recovery, reports)
    if _business_lag(observed, today) > max_business_lag:
        return _module(module_id, label, scope, True, BLOCKED, "data is stale", observed, recovery, reports)
    if status_field and str(payload.get(status_field, "")).upper() not in good_statuses:
        return _module(module_id, label, scope, True, BLOCKED, f"{status_field} is not ready", observed, recovery, reports)
    return _module(module_id, label, scope, True, READY, "current", observed, recovery, reports)


def _weekly_check(
    root: Path,
    today: date,
    *,
    module_id: str,
    label: str,
    relative: str,
    observed: date | None,
    status: str = READY,
    max_age_days: int = 10,
    critical: bool = False,
    recovery: str | None = "update-fund-weekly-analytics.yml",
    reason: str = "current",
) -> ModuleHealth:
    reports = ["基金週報"]
    if _load(root, relative) is None:
        return _module(module_id, label, "weekly", critical, BLOCKED if critical else PARTIAL, "cache missing or invalid", None, recovery, reports)
    if observed is None:
        return _module(module_id, label, "weekly", critical, BLOCKED if critical else PARTIAL, "data date missing", None, recovery, reports)
    if (today - observed).days > max_age_days:
        return _module(module_id, label, "weekly", critical, BLOCKED if critical else PARTIAL, "data is stale", observed, recovery, reports)
    return _module(module_id, label, "weekly", critical, status, reason, observed, recovery, reports, retryable=status == BLOCKED)


def build_health_report(root: str | Path, *, now: datetime | None = None) -> dict[str, Any]:
    """Evaluate all scheduled caches and return a serialisable report."""
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    taipei_now = now.astimezone(ZoneInfo("Asia/Taipei"))
    today = taipei_now.date()
    modules: list[ModuleHealth] = []

    dashboard = _daily_check(
        root, today, module_id="market_dashboard", label="Market Dashboard", scope="morning",
        relative="data/market/dashboard/dashboard_latest.json", date_field="expected_as_of",
        status_field="data_status", good_statuses={READY}, recovery="update-market-dashboard.yml",
        reports=["Market Dashboard", "美股日報"],
    )
    modules.append(dashboard)
    dashboard_as_of = dashboard.observed_as_of
    for module_id, label, filename in (
        ("us_breakout_scan", "US Breakout Scan", "breakout_scan_latest.json"),
        ("us_portfolio_scores", "US Portfolio Scores", "portfolio_scores_latest.json"),
    ):
        item = _daily_check(
            root, today, module_id=module_id, label=label, scope="morning",
            relative=f"data/market/us_stock_intelligence/{filename}", date_field="expected_as_of",
            status_field="data_status", good_statuses={READY}, recovery="update-market-dashboard.yml",
            reports=["美股日報"],
        )
        if item.status == READY and dashboard_as_of and item.observed_as_of != dashboard_as_of:
            item = _module(module_id, label, "morning", True, BLOCKED, "date does not match Market Dashboard", _date(item.observed_as_of), "update-market-dashboard.yml", ["美股日報"])
        modules.append(item)

    etf = _load(root, "data/market/etf_cta/cta_latest.json")
    etf_rows = etf.get("data_status", []) if etf else []
    etf_date = _max_date(row.get("as_of") for row in etf_rows if isinstance(row, dict))
    etf_bad = [row.get("symbol") for row in etf_rows if isinstance(row, dict) and row.get("status") != "CURRENT"]
    if not etf_rows or not etf_date or _business_lag(etf_date, today) > 2:
        modules.append(_module("etf_cta", "ETF CTA", "morning", True, BLOCKED, "cache missing, invalid, or stale", etf_date, "update-etf-cta.yml", ["基金日報", "基金週報"]))
    elif etf_bad:
        status = PARTIAL if set(etf_bad) <= {"WTI"} else BLOCKED
        modules.append(_module("etf_cta", "ETF CTA", "morning", True, status, f"non-current symbols: {', '.join(etf_bad)}", etf_date, "update-etf-cta.yml", ["基金日報", "基金週報"], retryable=status == BLOCKED))
    else:
        modules.append(_module("etf_cta", "ETF CTA", "morning", True, READY, "all symbols current", etf_date, "update-etf-cta.yml", ["基金日報", "基金週報"]))

    fund = _load(root, "data/market/fund_nav/fund_cta_latest.json")
    fund_results = fund.get("results", []) if fund else []
    fund_date = _max_date(row.get("fund_nav_as_of") for row in fund_results if isinstance(row, dict))
    fund_generated = _date(fund.get("generated_at")) if fund else None
    if len(fund_results) < 7 or not fund_date or _business_lag(fund_date, today) > 2:
        modules.append(_module("fund_nav_cta", "Fund NAV CTA", "morning", True, BLOCKED, "seven-fund cache missing, incomplete, or stale", fund_date, "update-fund-nav-cta.yml", ["基金日報", "基金週報"]))
    elif fund_generated != today:
        modules.append(_module("fund_nav_cta", "Fund NAV CTA", "morning", True, BLOCKED, "daily generation timestamp is missing or stale", fund_generated, "update-fund-nav-cta.yml", ["基金日報", "基金週報"]))
    else:
        refresh_status = str((fund.get("nav_refresh") or {}).get("status", "READY")).upper()
        status = PARTIAL if refresh_status not in {"READY", "CURRENT", "COMPLETE"} else READY
        modules.append(_module("fund_nav_cta", "Fund NAV CTA", "morning", True, status, "current" if status == READY else f"NAV refresh {refresh_status}", fund_date, "update-fund-nav-cta.yml", ["基金日報", "基金週報"], retryable=False))

    modules.append(_daily_check(
        root, today, module_id="taiwan_market_cta", label="Taiwan 0050/2330 CTA", scope="asia",
        relative="data/market/taiwan_cta/cta_latest.json", date_field="data_cutoff",
        status_field=None, good_statuses=set(), recovery="update-taiwan-cta.yml", reports=["台股日報"],
    ))
    modules.append(_daily_check(
        root, today, module_id="taiwan_stock_screen", label="Taiwan Stock Screen", scope="asia",
        relative="data/market/taiwan_stock_intelligence/screen_latest.json", date_field="expected_as_of",
        status_field="data_status", good_statuses={READY}, recovery="update-taiwan-stock-screen.yml", reports=["台股日報"],
    ))

    tw_cta = _load(root, "data/market/taiwan_stock_intelligence/cta/cta_latest.json")
    coverage = tw_cta.get("coverage", {}) if tw_cta else {}
    requested = int(tw_cta.get("requested_count", 0)) if tw_cta else 0
    covered = sum(int(coverage.get(key, 0)) for key in ("current", "stale_last_known", "unknown"))
    tw_cta_date = _date(tw_cta.get("screen_as_of")) if tw_cta else None
    if requested < 200 or covered < requested or not tw_cta_date or _business_lag(tw_cta_date, today) > 2:
        modules.append(_module("taiwan_candidate_cta", "Taiwan 200-stock CTA", "asia", True, BLOCKED, "coverage incomplete or stale", tw_cta_date, "update-taiwan-stock-screen.yml", ["台股日報"]))
    elif int(coverage.get("unknown", 0)) or int(coverage.get("stale_last_known", 0)):
        reason = f"current {coverage.get('current', 0)}, stale {coverage.get('stale_last_known', 0)}, unknown {coverage.get('unknown', 0)}"
        modules.append(_module("taiwan_candidate_cta", "Taiwan 200-stock CTA", "asia", True, PARTIAL, reason, tw_cta_date, "update-taiwan-stock-screen.yml", ["台股日報"], retryable=False))
    else:
        modules.append(_module("taiwan_candidate_cta", "Taiwan 200-stock CTA", "asia", True, READY, "200 stocks current", tw_cta_date, "update-taiwan-stock-screen.yml", ["台股日報"]))

    modules.append(_daily_check(
        root, today, module_id="taiwan_daily_context", label="Taiwan Daily Context", scope="asia",
        relative="data/market/taiwan_stock_intelligence/daily_context_latest.json", date_field="screen_as_of",
        status_field="display_status", good_statuses={"CURRENT"}, recovery="update-taiwan-stock-screen.yml", reports=["台股日報"],
    ))

    # Weekly context modules are advisory unless the final validation explicitly fails.
    weekly_specs = [
        ("macro_regime", "Macro Regime", "data/market/macro_regime/macro_regime_latest.json", "generated_at", 10),
        ("fund_alpha", "Fund Alpha", "data/market/fund_nav/alpha_latest.json", "result_end_date", 10),
        ("peer_ranking", "Peer Ranking", "data/market/fund_nav/peer_ranking_latest.json", "generated_at", 10),
        ("stockq_rotation", "StockQ Rotation", "data/market/stockq_rotation/rotation_latest.json", "as_of", 10),
        ("sector_rotation", "Sector Rotation", "data/market/sector_rotation/rotation_latest.json", "as_of", 10),
        ("fundamental_cycle", "Fundamental Cycle", "data/market/fundamental_cycle/fundamental_cycle_latest.json", "generated_at", 40),
    ]
    for module_id, label, relative, field, max_age in weekly_specs:
        payload = _load(root, relative)
        if field == "result_end_date":
            observed = _max_date(row.get("end_date") for row in (payload or {}).get("results", []) if isinstance(row, dict))
        else:
            observed = _date((payload or {}).get(field))
        modules.append(_weekly_check(root, today, module_id=module_id, label=label, relative=relative, observed=observed, max_age_days=max_age))

    ai = _load(root, "data/market/ai_revolution/ai_revolution_latest.json")
    ai_date = _date((ai or {}).get("generated_at"))
    ai_status = READY
    ai_reason = "current and reviewed"
    if ai and (ai.get("cache_status") != "VALID" or ai.get("review_required")):
        ai_status = PARTIAL
        ai_reason = "official evidence requires manual review"
    modules.append(_weekly_check(root, today, module_id="ai_revolution", label="AI Revolution", relative="data/market/ai_revolution/ai_revolution_latest.json", observed=ai_date, status=ai_status, reason=ai_reason, recovery=None))

    validation = _load(root, "data/market/fund_intelligence/validation_latest.json")
    validation_date = _date((validation or {}).get("generated_at"))
    raw_validation = str((validation or {}).get("status", "FAIL")).upper()
    validation_status = READY if raw_validation == "PASS" else PARTIAL if raw_validation == "CONDITIONAL_PASS" else BLOCKED
    modules.append(_weekly_check(
        root, today, module_id="fund_validation", label="Fund Intelligence Validation",
        relative="data/market/fund_intelligence/validation_latest.json", observed=validation_date,
        status=validation_status, critical=True, recovery="update-fund-weekly-analytics.yml" if validation_status == BLOCKED else None,
        reason=f"validation {raw_validation}",
    ))

    full_status = max((item.status for item in modules), key=lambda value: _ORDER[value])
    scope_status: dict[str, str] = {}
    for scope in ("morning", "asia", "weekly"):
        scoped = [item.status for item in modules if item.scope == scope]
        scope_status[scope] = max(scoped, key=lambda value: _ORDER[value]) if scoped else READY
    issues = [asdict(item) for item in modules if item.status != READY]
    recoveries = sorted({item.recovery_workflow for item in modules if item.status == BLOCKED and item.retryable and item.recovery_workflow})
    fingerprint_body = json.dumps([(item["module_id"], item["status"], item["reason"]) for item in issues], ensure_ascii=False, sort_keys=True)
    return {
        "schema_version": "1.0",
        "module": "Onecool Unified Schedule Health",
        "generated_at": now.astimezone(timezone.utc).isoformat(),
        "taipei_date": today.isoformat(),
        "status": full_status,
        "scope_status": scope_status,
        "action_readiness": "SAFE" if full_status == READY else "LIMITED" if full_status == PARTIAL else "UNSAFE_FOR_AFFECTED_REPORTS",
        "counts": {state.lower(): sum(item.status == state for item in modules) for state in (READY, PARTIAL, BLOCKED)},
        "modules": [asdict(item) for item in modules],
        "issues": issues,
        "recovery_workflows": recoveries,
        "issue_fingerprint": hashlib.sha256(fingerprint_body.encode("utf-8")).hexdigest(),
        "policy": "Health monitoring only; never changes CTA, rankings, or investment decisions.",
    }


def write_health_report(report: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
