"""Dashboard 2.0 snapshot assembly from RuntimeSession outputs."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import Any

from onecool_os.dashboard.models import DashboardSnapshot
from onecool_os.fair_value import FairValueConfidence
from onecool_os.fair_value import FairValueFreshness
from onecool_os.fair_value import FairValueLiquidity
from onecool_os.portfolio import PortfolioNavStatus
from onecool_os.research.queue.enums import ResearchQueuePriority
from onecool_os.research.queue.enums import ResearchQueueStatus
from onecool_os.valuation.integration import FairValueValuationEngine


class DashboardSnapshotBuilder:
    """Build display-only Dashboard 2.0 snapshots from runtime outputs."""

    def build(self, runtime_session: Any) -> DashboardSnapshot:
        """Build a deterministic dashboard snapshot without mutating runtime."""

        reference = runtime_session.generated_at
        fair_values = tuple(runtime_session.build_fair_value())
        valuation_result = FairValueValuationEngine().build(fair_values)
        valuation_records = tuple(valuation_result.valuation_records)
        nav_snapshots = tuple(runtime_session.build_live_portfolio_nav())
        research_snapshot = runtime_session.build_research_queue(
            valuation_records,
            nav_snapshots,
        )
        return DashboardSnapshot(
            snapshot_id=f"dashboard-2:{reference.isoformat()}",
            portfolio_summary=_portfolio_summary(runtime_session, nav_snapshots, research_snapshot),
            nav_summary=_nav_summary(nav_snapshots),
            coverage=_coverage(runtime_session, nav_snapshots, research_snapshot),
            research=_research(research_snapshot),
            evidence=_evidence(runtime_session),
            valuation=_valuation(fair_values, valuation_result),
            top_holdings=_top_holdings(nav_snapshots, fair_values),
            missing_valuation=_missing_valuation(runtime_session, nav_snapshots),
            latest_updates=_latest_updates(runtime_session, fair_values, valuation_records, research_snapshot),
            warnings=_warnings(runtime_session, fair_values, research_snapshot),
            reference_datetime=reference,
            generated_at=reference,
        )


def _portfolio_summary(
    runtime_session: Any,
    nav_snapshots: tuple[Any, ...],
    research_snapshot: Any,
) -> dict[str, Any]:
    primary = _primary_nav(nav_snapshots)
    return {
        "portfolio_status": _portfolio_status(nav_snapshots),
        "portfolio_nav_status": primary.status.value if primary else PortfolioNavStatus.INSUFFICIENT_DATA.value,
        "currency": primary.currency if primary else "N/A",
        "total_assets": len(tuple(runtime_session.enriched_runtime_assets)),
        "assets_with_market_value": sum(snapshot.assets_with_market_value for snapshot in nav_snapshots),
        "missing_value_assets": sum(snapshot.missing_value_assets for snapshot in nav_snapshots),
        "valuation_coverage": _percent_text(primary.valuation_coverage_percent if primary else Decimal("0")),
        "verified_coverage": _percent_text(primary.verified_coverage_percent if primary else Decimal("0")),
        "research_coverage": _percent_text(_research_coverage_percent(research_snapshot)),
        "last_runtime_update": runtime_session.generated_at.isoformat(),
    }


def _nav_summary(nav_snapshots: tuple[Any, ...]) -> dict[str, Any]:
    primary = _primary_nav(nav_snapshots)
    if primary is None:
        return {
            "cost_basis": "N/A",
            "market_value": "N/A",
            "unrealized_gain": "N/A",
            "roi": "N/A",
            "coverage_note": "Portfolio value is unavailable because no NAV snapshot exists.",
        }
    return {
        "cost_basis": _money_text(primary.total_cost_basis, primary.currency, primary.assets_with_cost > 0),
        "market_value": _money_text(primary.total_market_value, primary.currency, primary.assets_with_market_value > 0),
        "unrealized_gain": _money_text(primary.unrealized_gain_loss, primary.currency, primary.unrealized_gain_loss is not None),
        "roi": _percent_text(primary.roi_percent),
        "coverage_note": (
            "Portfolio value reflects valued assets only. Missing assets are excluded, not treated as zero."
            if primary.valuation_coverage_percent != Decimal("100.0000")
            else None
        ),
    }


def _coverage(
    runtime_session: Any,
    nav_snapshots: tuple[Any, ...],
    research_snapshot: Any,
) -> dict[str, Any]:
    evidence_coverage = runtime_session.ebay_evidence_coverage()
    primary = _primary_nav(nav_snapshots)
    return {
        "research_coverage": _percent_text(_research_coverage_percent(research_snapshot)),
        "evidence_coverage": _percent_text(_coverage_percent(evidence_coverage["covered_assets"], evidence_coverage["total_assets"])),
        "valuation_coverage": _percent_text(primary.valuation_coverage_percent if primary else Decimal("0")),
        "nav_coverage": _percent_text(primary.valuation_coverage_percent if primary else Decimal("0")),
        "verified_coverage": _percent_text(primary.verified_coverage_percent if primary else Decimal("0")),
    }


def _research(research_snapshot: Any) -> dict[str, Any]:
    ready_assets = tuple(
        item
        for item in research_snapshot.items
        if item.status == ResearchQueueStatus.READY
    )
    return {
        "critical": research_snapshot.critical_items,
        "high": research_snapshot.high_items,
        "medium": research_snapshot.medium_items,
        "low": research_snapshot.low_items,
        "ready": research_snapshot.ready_items,
        "blocked": research_snapshot.blocked_items,
        "completed": research_snapshot.completed_items,
        "top_5_ready_assets": [
            {
                "asset_id": item.asset_id,
                "asset_name": item.asset_name,
                "priority": item.priority.value,
                "reasons": [reason.value for reason in item.reasons],
            }
            for item in sorted(ready_assets, key=lambda item: (item.priority.value, item.asset_name, item.asset_id))[:5]
        ],
    }


def _evidence(runtime_session: Any) -> dict[str, Any]:
    verified = runtime_session.verified_ebay_sold_evidence()
    review = runtime_session.review_required_ebay_evidence()
    rejected = runtime_session.rejected_ebay_evidence()
    no_match = tuple(
        evidence
        for batch in runtime_session.ebay_sold_evidence_batches
        for evidence in batch.evidence
        if evidence.status.value == "NO_MATCH"
    )
    coverage = runtime_session.ebay_evidence_coverage()
    latest = max(
        (evidence.sold_date for batch in runtime_session.ebay_sold_evidence_batches for evidence in batch.evidence if evidence.sold_date),
        default=None,
    )
    return {
        "verified_evidence": len(verified),
        "needs_review": len(review),
        "rejected": len(rejected),
        "no_match": len(no_match),
        "evidence_coverage": _percent_text(_coverage_percent(coverage["covered_assets"], coverage["total_assets"])),
        "latest_evidence_date": latest.isoformat() if latest else None,
    }


def _valuation(fair_values: tuple[Any, ...], valuation_result: Any) -> dict[str, Any]:
    trusted = tuple(item for item in fair_values if item.fair_value is not None)
    freshness = Counter(item.freshness.value for item in fair_values)
    liquidity = Counter(item.liquidity.value for item in fair_values)
    confidence = Counter(item.confidence.value for item in fair_values)
    return {
        "onecool_fair_value_count": len(trusted),
        "valuation_record_count": len(valuation_result.valuation_records),
        "average_eqs": _average_decimal(tuple(item.eqs for item in trusted)),
        "average_confidence": _average_confidence(trusted),
        "confidence_distribution": dict(sorted(confidence.items())),
        "freshness_distribution": dict(sorted(freshness.items())),
        "liquidity_distribution": dict(sorted(liquidity.items())),
    }


def _top_holdings(nav_snapshots: tuple[Any, ...], fair_values: tuple[Any, ...]) -> tuple[dict[str, Any], ...]:
    fair_value_by_asset = {item.asset_id: item for item in fair_values}
    rows = []
    for snapshot in nav_snapshots:
        for line in snapshot.asset_lines:
            if line.market_value is None:
                continue
            fair_value = fair_value_by_asset.get(line.asset_id)
            rows.append(
                {
                    "asset": line.asset_name,
                    "asset_id": line.asset_id,
                    "fair_value": _money_text(line.market_value, snapshot.currency, True),
                    "cost": _money_text(line.cost_basis, line.cost_currency, line.cost_basis is not None),
                    "gain": _money_text(line.unrealized_gain_loss, snapshot.currency, line.unrealized_gain_loss is not None),
                    "roi": _percent_text(line.roi_percent),
                    "confidence": fair_value.confidence.value if fair_value else "N/A",
                    "eqs": _decimal_text(fair_value.eqs) if fair_value else "N/A",
                    "market_value": line.market_value,
                }
            )
    ordered = sorted(rows, key=lambda item: (-item["market_value"], item["asset"], item["asset_id"]))
    return tuple(_without_sort_value(item) for item in ordered[:10])


def _missing_valuation(runtime_session: Any, nav_snapshots: tuple[Any, ...]) -> tuple[dict[str, Any], ...]:
    valued_assets = {
        line.asset_id
        for snapshot in nav_snapshots
        for line in snapshot.asset_lines
        if line.market_value is not None
    }
    missing = []
    for asset in runtime_session.enriched_runtime_assets:
        asset_id = str(asset.get("asset_id") or "")
        if asset_id in valued_assets:
            continue
        missing.append(
            {
                "asset_id": asset_id,
                "asset": _asset_name(asset),
                "cert_number": asset.get("cert_number"),
                "core_holding": _is_core(asset),
            }
        )
    return tuple(sorted(missing, key=lambda item: (not item["core_holding"], item["asset"], item["asset_id"])))


def _latest_updates(
    runtime_session: Any,
    fair_values: tuple[Any, ...],
    valuation_records: tuple[Any, ...],
    research_snapshot: Any,
) -> tuple[dict[str, Any], ...]:
    updates = []
    for evidence in (
        evidence
        for batch in runtime_session.ebay_sold_evidence_batches
        for evidence in batch.evidence
    ):
        updates.append(_update("Evidence", evidence.asset_id, evidence.sold_date, evidence.status.value))
    for fair_value in fair_values:
        updates.append(_update("Fair Value", fair_value.asset_id, fair_value.generated_at, fair_value.confidence.value))
    for valuation in valuation_records:
        updates.append(_update("Valuation", valuation.asset_id, valuation.valuation_date, valuation.source.value))
    updates.append(_update("Research", "portfolio", research_snapshot.generated_at, "Research Queue"))
    return tuple(
        _without_sort_value(item)
        for item in sorted(updates, key=lambda item: (item["sort_datetime"], item["source"], item["asset_id"]), reverse=True)[:10]
    )


def _warnings(runtime_session: Any, fair_values: tuple[Any, ...], research_snapshot: Any) -> tuple[dict[str, Any], ...]:
    warnings = []
    for difference in runtime_session.collection_differences():
        if difference.difference_type in {"DUPLICATE_CERT", "DUPLICATE_ASSET", "GRADE_CHANGED", "GRADE_ISSUER_CHANGED"}:
            warnings.append(_warning(difference.severity, difference.difference_type, difference.asset_id, difference.description))
    for item in research_snapshot.items:
        if item.status == ResearchQueueStatus.BLOCKED:
            warnings.append(_warning("HIGH", "Research Blocked", item.asset_id, "; ".join(item.blocking_reasons) or item.asset_name))
        if any(reason.value == "MISSING_EBAY_SEARCH_URL" for reason in item.reasons):
            warnings.append(_warning("MEDIUM", "Missing URL", item.asset_id, item.asset_name))
    for fair_value in fair_values:
        if fair_value.eqs < Decimal("50"):
            warnings.append(_warning("MEDIUM", "Low EQS", fair_value.asset_id, f"EQS {fair_value.eqs}"))
        if fair_value.freshness == FairValueFreshness.STALE:
            warnings.append(_warning("MEDIUM", "Stale Evidence", fair_value.asset_id, "Fair Value evidence is stale."))
    return tuple(sorted(warnings, key=lambda item: (item["severity"], item["warning_type"], item["asset_id"])))


def _primary_nav(nav_snapshots: tuple[Any, ...]) -> Any | None:
    if not nav_snapshots:
        return None
    return sorted(nav_snapshots, key=lambda snapshot: snapshot.currency)[0]


def _portfolio_status(nav_snapshots: tuple[Any, ...]) -> str:
    if not nav_snapshots:
        return PortfolioNavStatus.INSUFFICIENT_DATA.value
    statuses = {snapshot.status for snapshot in nav_snapshots}
    if PortfolioNavStatus.CURRENCY_MISMATCH in statuses:
        return PortfolioNavStatus.CURRENCY_MISMATCH.value
    if PortfolioNavStatus.INSUFFICIENT_DATA in statuses:
        return PortfolioNavStatus.INSUFFICIENT_DATA.value
    if PortfolioNavStatus.PARTIAL in statuses:
        return PortfolioNavStatus.PARTIAL.value
    return PortfolioNavStatus.COMPLETE.value


def _research_coverage_percent(research_snapshot: Any) -> Decimal:
    if research_snapshot.total_assets <= 0:
        return Decimal("0.0000")
    covered = research_snapshot.ready_items + research_snapshot.completed_items
    return _coverage_percent(covered, research_snapshot.total_assets)


def _coverage_percent(numerator: int, denominator: int) -> Decimal:
    if denominator <= 0:
        return Decimal("0.0000")
    return ((Decimal(numerator) / Decimal(denominator)) * Decimal("100")).quantize(Decimal("0.0000"))


def _average_decimal(values: tuple[Decimal, ...]) -> str:
    if not values:
        return "N/A"
    return _decimal_text((sum(values, Decimal("0")) / Decimal(str(len(values)))).quantize(Decimal("0.01")))


def _average_confidence(fair_values: tuple[Any, ...]) -> str:
    if not fair_values:
        return "N/A"
    score = {
        FairValueConfidence.HIGH: Decimal("3"),
        FairValueConfidence.MEDIUM: Decimal("2"),
        FairValueConfidence.LOW: Decimal("1"),
        FairValueConfidence.INSUFFICIENT_DATA: Decimal("0"),
    }
    average = sum((score[item.confidence] for item in fair_values), Decimal("0")) / Decimal(str(len(fair_values)))
    if average >= Decimal("2.5"):
        return "HIGH"
    if average >= Decimal("1.5"):
        return "MEDIUM"
    if average > Decimal("0"):
        return "LOW"
    return "INSUFFICIENT_DATA"


def _asset_name(asset: dict[str, Any]) -> str:
    return " ".join(
        part
        for part in (
            str(asset.get("year") or "").strip(),
            str(asset.get("set") or "").strip(),
            str(asset.get("player") or "").strip(),
            str(asset.get("card_number") or "").strip(),
            str(asset.get("grade_company") or "").strip(),
            str(asset.get("grade") or "").strip(),
        )
        if part
    ) or str(asset.get("asset_id") or "Unknown Asset")


def _is_core(asset: dict[str, Any]) -> bool:
    value = str(asset.get("collection_type") or "").strip().upper()
    asset_master = asset.get("asset_master") if isinstance(asset.get("asset_master"), dict) else {}
    master_value = str(asset_master.get("collection_type") or "").strip().upper()
    return value == "CORE" or master_value == "CORE"


def _money_text(value: Decimal | None, currency: str, available: bool) -> str:
    if not available or value is None:
        return "N/A"
    return f"{currency} {value.quantize(Decimal('0.01'))}"


def _percent_text(value: Decimal | None) -> str:
    if value is None:
        return "N/A"
    return f"{value.quantize(Decimal('0.01'))}%"


def _decimal_text(value: Decimal | None) -> str:
    if value is None:
        return "N/A"
    return str(value.normalize())


def _update(source: str, asset_id: str, when: Any, status: str) -> dict[str, Any]:
    text = when.isoformat() if hasattr(when, "isoformat") else str(when)
    return {
        "source": source,
        "asset_id": asset_id,
        "updated_at": text,
        "status": status,
        "sort_datetime": text,
    }


def _warning(severity: str, warning_type: str, asset_id: str | None, message: str) -> dict[str, Any]:
    return {
        "severity": severity,
        "warning_type": warning_type,
        "asset_id": asset_id,
        "message": message,
    }


def _without_sort_value(item: dict[str, Any]) -> dict[str, Any]:
    result = dict(item)
    result.pop("market_value", None)
    result.pop("sort_datetime", None)
    return result
