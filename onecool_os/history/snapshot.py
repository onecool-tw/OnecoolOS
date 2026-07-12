"""Portfolio history snapshot builder."""

from __future__ import annotations

import hashlib
from datetime import UTC
from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from onecool_os.history.enums import HistoryRecordStatus
from onecool_os.history.enums import HistorySnapshotType
from onecool_os.history.models import AssetHistoryLine
from onecool_os.history.models import PortfolioHistorySnapshot
from onecool_os.history.serialization import canonical_json

PROJECT_TIMEZONE = "Asia/Taipei"


class PortfolioHistorySnapshotBuilder:
    """Build immutable history snapshots from existing RuntimeSession outputs."""

    def build(
        self,
        runtime_session: Any,
        *,
        snapshot_type: HistorySnapshotType | str = HistorySnapshotType.PORTFOLIO_DAILY,
        reference_datetime: datetime | None = None,
        source_commit: str | None = None,
        runtime_version: str | None = None,
        timezone_name: str = PROJECT_TIMEZONE,
    ) -> PortfolioHistorySnapshot:
        """Build a history snapshot without mutating runtime."""

        reference = _with_timezone(reference_datetime or runtime_session.generated_at, timezone_name)
        fair_values = tuple(runtime_session.build_fair_value())
        valuation_records = tuple(runtime_session.valuation_records())
        nav_snapshots = tuple(runtime_session.build_live_portfolio_nav())
        research_snapshot = runtime_session.research_queue_snapshot(
            valuation_records,
            nav_snapshots,
        )
        dashboard_snapshot = runtime_session.dashboard_snapshot()
        fingerprint = _fingerprint(
            runtime_session,
            fair_values,
            valuation_records,
            nav_snapshots,
            research_snapshot,
            reference,
            dashboard_snapshot,
        )
        snapshot_date = reference.date()
        asset_lines = _asset_lines(runtime_session, nav_snapshots, fair_values, reference)
        warnings = tuple(
            dict.fromkeys(
                warning
                for line in asset_lines
                for warning in line.warnings
            )
        )
        total_cost = {snapshot.currency: snapshot.total_cost_basis for snapshot in nav_snapshots}
        total_market = {snapshot.currency: snapshot.total_market_value for snapshot in nav_snapshots}
        unrealized = {
            snapshot.currency: snapshot.unrealized_gain_loss or Decimal("0")
            for snapshot in nav_snapshots
        }
        roi = {
            snapshot.currency: snapshot.roi_percent or Decimal("0")
            for snapshot in nav_snapshots
        }
        status_by_currency = {
            snapshot.currency: snapshot.status.value
            for snapshot in nav_snapshots
        }
        primary = sorted(nav_snapshots, key=lambda item: item.currency)[0] if nav_snapshots else None
        return PortfolioHistorySnapshot(
            history_snapshot_id=f"portfolio-history:{snapshot_date.isoformat()}:{fingerprint[:16]}",
            snapshot_type=snapshot_type,
            snapshot_date=snapshot_date,
            reference_datetime=reference,
            generated_at=reference,
            runtime_version=runtime_version,
            source_commit=source_commit,
            currencies=tuple(sorted(status_by_currency)) or ("USD",),
            total_assets=len(asset_lines),
            collection_health=getattr(runtime_session, "collection_health", None),
            collection_difference_count=len(runtime_session.collection_differences()),
            research_queue_total=research_snapshot.total_queue_items,
            research_queue_ready=research_snapshot.ready_items,
            research_queue_blocked=research_snapshot.blocked_items,
            evidence_verified_count=len(runtime_session.verified_ebay_sold_evidence()),
            evidence_review_count=len(runtime_session.review_required_ebay_evidence()),
            evidence_rejected_count=len(runtime_session.rejected_ebay_evidence()),
            evidence_no_match_count=_no_match_count(runtime_session),
            fair_value_count=sum(1 for item in fair_values if item.fair_value is not None),
            valuation_record_count=len(valuation_records),
            total_cost_basis_by_currency=total_cost,
            total_market_value_by_currency=total_market,
            unrealized_gain_loss_by_currency=unrealized,
            roi_percent_by_currency=roi,
            valuation_coverage_percent=primary.valuation_coverage_percent if primary else Decimal("0"),
            verified_coverage_percent=primary.verified_coverage_percent if primary else Decimal("0"),
            nav_status_by_currency=status_by_currency or {"USD": HistoryRecordStatus.INSUFFICIENT_DATA.value},
            missing_value_assets=sum(snapshot.missing_value_assets for snapshot in nav_snapshots),
            warning_count=len(warnings),
            asset_lines=asset_lines,
            warnings=warnings,
            status=_history_status(nav_snapshots),
            fingerprint=fingerprint,
        )


def _asset_lines(
    runtime_session: Any,
    nav_snapshots: tuple[Any, ...],
    fair_values: tuple[Any, ...],
    reference: datetime,
) -> tuple[AssetHistoryLine, ...]:
    fair_value_by_asset = {item.asset_id: item for item in fair_values}
    nav_line_by_asset = {
        line.asset_id: line
        for snapshot in nav_snapshots
        for line in snapshot.asset_lines
    }
    lines = []
    for asset in sorted(runtime_session.enriched_runtime_assets, key=lambda item: str(item.get("asset_id") or "")):
        asset_id = str(asset.get("asset_id") or "")
        nav_line = nav_line_by_asset.get(asset_id)
        fair_value = fair_value_by_asset.get(asset_id)
        lines.append(
            AssetHistoryLine(
                asset_id=asset_id,
                cert_number=str(asset.get("cert_number") or "") or None,
                asset_name=_asset_name(asset),
                grade_issuer=str(asset.get("grade_company") or asset.get("grade_issuer") or "") or None,
                grade=str(asset.get("grade") or "") or None,
                cost_basis=getattr(nav_line, "cost_basis", None),
                cost_currency=getattr(nav_line, "cost_currency", None),
                market_value=getattr(nav_line, "market_value", None),
                market_currency=getattr(nav_line, "market_currency", None),
                unrealized_gain_loss=getattr(nav_line, "unrealized_gain_loss", None),
                roi_percent=getattr(nav_line, "roi_percent", None),
                valuation_source=getattr(nav_line, "valuation_source", None),
                valuation_record_id=getattr(nav_line, "valuation_record_id", None),
                fair_value_snapshot_id=(
                    f"onecool-fair-value:{asset_id}:{fair_value.reference_datetime.isoformat()}"
                    if fair_value
                    else None
                ),
                evidence_quality_score=getattr(fair_value, "eqs", None),
                valuation_confidence=fair_value.confidence.value if fair_value else None,
                freshness_status=fair_value.freshness.value if fair_value else None,
                liquidity_level=fair_value.liquidity.value if fair_value else None,
                latest_sold_date=getattr(fair_value, "latest_sold_date", None),
                valuation_coverage_status=(
                    nav_line.coverage_status.value if nav_line else "MISSING"
                ),
                warnings=getattr(nav_line, "warnings", ()),
                reference_datetime=reference,
            )
        )
    return tuple(lines)


def _fingerprint(
    runtime_session: Any,
    fair_values: tuple[Any, ...],
    valuation_records: tuple[Any, ...],
    nav_snapshots: tuple[Any, ...],
    research_snapshot: Any,
    reference: datetime,
    dashboard_snapshot: Any,
) -> str:
    payload = {
        "asset_ids": sorted(str(asset.get("asset_id") or "") for asset in runtime_session.enriched_runtime_assets),
        "valuation_record_ids": sorted(record.valuation_id for record in valuation_records),
        "fair_value_ids": sorted(f"{item.asset_id}:{item.reference_datetime.isoformat()}:{item.fair_value}" for item in fair_values),
        "evidence_ids": sorted(
            evidence.evidence_id
            for batch in runtime_session.ebay_sold_evidence_batches
            for evidence in batch.evidence
        ),
        "nav_snapshot_ids": sorted(snapshot.snapshot_id for snapshot in nav_snapshots),
        "research_queue_snapshot_id": research_snapshot.snapshot_id,
        "sync_report": {
            "health": runtime_session.collection_health,
            "differences": [item.to_dict() for item in runtime_session.collection_differences()],
        },
        "dashboard_snapshot_id": dashboard_snapshot.snapshot_id,
        "reference_datetime": reference.isoformat(),
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _history_status(nav_snapshots: tuple[Any, ...]) -> HistoryRecordStatus:
    statuses = {snapshot.status.value for snapshot in nav_snapshots}
    if not statuses or "INSUFFICIENT_DATA" in statuses:
        return HistoryRecordStatus.INSUFFICIENT_DATA
    if "PARTIAL" in statuses:
        return HistoryRecordStatus.PARTIAL
    if "COMPLETE" in statuses:
        return HistoryRecordStatus.COMPLETE
    return HistoryRecordStatus.INVALID


def _no_match_count(runtime_session: Any) -> int:
    return sum(
        1
        for batch in runtime_session.ebay_sold_evidence_batches
        for evidence in batch.evidence
        if evidence.status.value == "NO_MATCH"
    )


def _asset_name(asset: dict[str, Any]) -> str:
    parts = [
        str(asset.get("year") or "").strip(),
        str(asset.get("set") or "").strip(),
        str(asset.get("player") or asset.get("subject") or "").strip(),
        str(asset.get("card_number") or "").strip(),
        str(asset.get("grade_company") or asset.get("grade_issuer") or "").strip(),
        str(asset.get("grade") or "").strip(),
    ]
    return " ".join(part for part in parts if part) or str(asset.get("asset_id") or "Unknown Asset")


def _with_timezone(value: datetime, timezone_name: str) -> datetime:
    timezone = ZoneInfo(timezone_name)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(timezone)
