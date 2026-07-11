"""Deterministic Research Queue engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import Any

from onecool_os.portfolio import PortfolioNavSnapshot
from onecool_os.portfolio import ValuationCoverageStatus
from onecool_os.research.enums import ResearchCapability
from onecool_os.research.enums import ResearchType
from onecool_os.research.queue.enums import ResearchQueuePriority
from onecool_os.research.queue.enums import ResearchQueueReason
from onecool_os.research.queue.enums import ResearchQueueStatus
from onecool_os.research.queue.models import ResearchQueueItem
from onecool_os.research.queue.models import ResearchQueueSnapshot
from onecool_os.sync import CollectionDifference
from onecool_os.valuation.evidence import EbaySoldEvidenceBatch
from onecool_os.valuation.evidence import EvidenceStatus
from onecool_os.valuation.enums import ValuationSource
from onecool_os.valuation.models import ValuationRecord

PRIORITY_RANK = {
    ResearchQueuePriority.CRITICAL: 0,
    ResearchQueuePriority.HIGH: 1,
    ResearchQueuePriority.MEDIUM: 2,
    ResearchQueuePriority.LOW: 3,
    ResearchQueuePriority.INFORMATIONAL: 4,
}
IDENTITY_CONFLICT_TYPES = frozenset(
    {
        "DUPLICATE_CERT",
        "DUPLICATE_ASSET",
        "GRADE_CHANGED",
        "GRADE_ISSUER_CHANGED",
    }
)
METADATA_RESEARCH_TYPES = frozenset(
    {
        "EBAY_URL_MISSING",
        "PSA_URL_MISSING",
        "TARGET_PRICE_MISSING",
        "NOTES_CHANGED",
        "MISSING_IN_ASSET_MASTER",
        "VARIETY_CHANGED",
    }
)


@dataclass(frozen=True)
class _EvidenceCounts:
    current: int = 0
    verified: int = 0
    review: int = 0
    rejected: int = 0
    no_match: int = 0


class ResearchQueueEngine:
    """Build deterministic research queue snapshots."""

    def build(
        self,
        runtime_session: Any,
        *,
        valuation_records: tuple[ValuationRecord, ...] | list[ValuationRecord] = (),
        nav_snapshots: tuple[PortfolioNavSnapshot, ...] | list[PortfolioNavSnapshot] = (),
        reference_datetime: datetime | None = None,
        generated_at: datetime | None = None,
    ) -> ResearchQueueSnapshot:
        """Build a Research Queue snapshot without mutating source data."""

        reference = reference_datetime or getattr(runtime_session, "generated_at", None) or datetime.now(UTC)
        generated = generated_at or reference
        assets = tuple(dict(asset) for asset in getattr(runtime_session, "enriched_runtime_assets", ()))
        valuations = tuple(
            valuation
            for valuation in valuation_records
            if isinstance(valuation, ValuationRecord)
        )
        evidence_batches = tuple(getattr(runtime_session, "ebay_sold_evidence_batches", ()))
        sync_differences = tuple(getattr(runtime_session, "collection_differences", lambda: ())())
        nav_lines = _nav_lines_by_asset(tuple(nav_snapshots or ()))
        items = tuple(
            sorted(
                (
                    self._build_item(
                        asset,
                        valuations,
                        evidence_batches,
                        sync_differences,
                        nav_lines,
                        reference_datetime=reference,
                        generated_at=generated,
                    )
                    for asset in assets
                ),
                key=_item_sort_key,
            )
        )
        return ResearchQueueSnapshot(
            snapshot_id=f"research-queue:{reference.isoformat()}",
            reference_datetime=reference,
            total_assets=len(assets),
            total_queue_items=len(items),
            critical_items=sum(1 for item in items if item.priority == ResearchQueuePriority.CRITICAL),
            high_items=sum(1 for item in items if item.priority == ResearchQueuePriority.HIGH),
            medium_items=sum(1 for item in items if item.priority == ResearchQueuePriority.MEDIUM),
            low_items=sum(1 for item in items if item.priority == ResearchQueuePriority.LOW),
            informational_items=sum(1 for item in items if item.priority == ResearchQueuePriority.INFORMATIONAL),
            ready_items=sum(1 for item in items if item.status == ResearchQueueStatus.READY),
            blocked_items=sum(1 for item in items if item.status == ResearchQueueStatus.BLOCKED),
            completed_items=sum(1 for item in items if item.status == ResearchQueueStatus.COMPLETED),
            items=items,
            warnings=(),
            generated_at=generated,
        )

    def _build_item(
        self,
        asset: dict[str, Any],
        valuations: tuple[ValuationRecord, ...],
        evidence_batches: tuple[EbaySoldEvidenceBatch, ...],
        sync_differences: tuple[CollectionDifference, ...],
        nav_lines: dict[str, Any],
        *,
        reference_datetime: datetime,
        generated_at: datetime,
    ) -> ResearchQueueItem:
        asset_id = _text(asset.get("asset_id"))
        cert_number = _text(asset.get("cert_number") or asset.get("serial_number"))
        asset_name = _asset_name(asset)
        asset_master = asset.get("asset_master") if isinstance(asset.get("asset_master"), dict) else {}
        asset_master_metadata = asset_master.get("metadata") if isinstance(asset_master.get("metadata"), dict) else {}
        source_url = _text(asset_master.get("ebay_sold_search_url") or asset.get("ebay_sold_search_url"))
        sync = _differences_for_asset(asset_id, cert_number, sync_differences)
        evidence = _evidence_counts(asset_id, evidence_batches)
        asset_valuations = tuple(valuation for valuation in valuations if valuation.asset_id == asset_id)
        nav_line = nav_lines.get(asset_id)
        reasons: list[ResearchQueueReason] = []
        blockers: list[str] = []
        warnings: list[str] = []

        if not asset_id or not cert_number:
            reasons.append(ResearchQueueReason.AMBIGUOUS_IDENTITY)
            blockers.append("No usable asset identity.")
        if any(item.difference_type in IDENTITY_CONFLICT_TYPES for item in sync):
            reasons.append(ResearchQueueReason.COLLECTION_SYNC_ISSUE)
            blockers.append("Critical Collection Sync identity conflict.")
        elif any(item.difference_type in METADATA_RESEARCH_TYPES for item in sync):
            reasons.append(ResearchQueueReason.COLLECTION_SYNC_ISSUE)

        if source_url and not _valid_url(source_url):
            blockers.append("Invalid source URL.")
            source_url = None
        if not source_url:
            reasons.append(ResearchQueueReason.MISSING_EBAY_SEARCH_URL)
            if not _has_query_identity(asset):
                blockers.append("Missing required search URL and no query-generation identity.")

        if evidence.review:
            reasons.append(ResearchQueueReason.EVIDENCE_NEEDS_REVIEW)
        if evidence.rejected:
            reasons.append(ResearchQueueReason.EVIDENCE_REJECTED)
        if evidence.no_match:
            reasons.append(ResearchQueueReason.NO_MATCH)

        verified_valuation = _has_verified_valuation(asset_valuations, evidence)
        any_valuation = bool(asset_valuations)
        coverage_status = _coverage_status(nav_line, verified_valuation, any_valuation)
        if coverage_status != ValuationCoverageStatus.VERIFIED.value:
            reasons.append(ResearchQueueReason.MISSING_VERIFIED_VALUATION)
        if not any_valuation:
            reasons.append(ResearchQueueReason.MISSING_ANY_VALUATION)
        if coverage_status == ValuationCoverageStatus.ESTIMATED.value:
            reasons.append(ResearchQueueReason.SUPPORTING_ESTIMATE_ONLY)
        if _multiple_eligible_valuations(asset_valuations):
            reasons.append(ResearchQueueReason.MULTIPLE_ELIGIBLE_VALUATIONS)

        if _is_core(asset):
            reasons.append(ResearchQueueReason.CORE_HOLDING_RESEARCH)
        if _is_watchlist(asset_master):
            reasons.append(ResearchQueueReason.WATCHLIST_RESEARCH)
        if asset_master.get("target_price") not in (None, "") and coverage_status != ValuationCoverageStatus.VERIFIED.value:
            reasons.append(ResearchQueueReason.TARGET_PRICE_REVIEW)
        if asset_master.get("manual_research_request") or asset_master_metadata.get("manual_research_request"):
            reasons.append(ResearchQueueReason.MANUAL_RESEARCH_REQUEST)

        reasons = list(dict.fromkeys(reasons)) or [ResearchQueueReason.OTHER]
        priority = _priority(reasons, blockers, core=_is_core(asset))
        status = _status(priority, blockers)
        latest_valuation_date = max(
            (valuation.valuation_date for valuation in asset_valuations),
            default=None,
        )
        return ResearchQueueItem(
            queue_item_id=f"research:{asset_id or cert_number}:SOLD_COMPARABLES",
            asset_id=asset_id or f"UNKNOWN-{cert_number or 'ASSET'}",
            cert_number=cert_number,
            asset_name=asset_name,
            priority=priority,
            status=status,
            reasons=tuple(reasons),
            research_type=ResearchType.SOLD_COMPARABLES,
            source_url=source_url,
            provider_capability_required=ResearchCapability.SOLD_COMPARABLES,
            blocking_reasons=tuple(dict.fromkeys(blockers)),
            current_evidence_count=evidence.current,
            verified_evidence_count=evidence.verified,
            review_evidence_count=evidence.review,
            rejected_evidence_count=evidence.rejected,
            valuation_coverage_status=coverage_status,
            latest_valuation_date=latest_valuation_date,
            last_research_date=None,
            metadata={
                "collection_type": asset.get("collection_type"),
                "watch_status": asset_master.get("watch_status"),
                "has_source_url": bool(source_url),
            },
            warnings=tuple(dict.fromkeys(warnings)),
            created_at=generated_at,
            reference_datetime=reference_datetime,
        )


def _priority(
    reasons: list[ResearchQueueReason],
    blockers: list[str],
    *,
    core: bool,
) -> ResearchQueuePriority:
    if blockers or ResearchQueueReason.AMBIGUOUS_IDENTITY in reasons:
        return ResearchQueuePriority.CRITICAL
    if any(
        reason in reasons
        for reason in (
            ResearchQueueReason.EVIDENCE_NEEDS_REVIEW,
            ResearchQueueReason.EVIDENCE_REJECTED,
            ResearchQueueReason.NO_MATCH,
            ResearchQueueReason.SUPPORTING_ESTIMATE_ONLY,
            ResearchQueueReason.MULTIPLE_ELIGIBLE_VALUATIONS,
        )
    ):
        return ResearchQueuePriority.HIGH
    if core and ResearchQueueReason.MISSING_VERIFIED_VALUATION in reasons:
        return ResearchQueuePriority.HIGH
    if any(
        reason in reasons
        for reason in (
            ResearchQueueReason.MISSING_EBAY_SEARCH_URL,
            ResearchQueueReason.WATCHLIST_RESEARCH,
            ResearchQueueReason.TARGET_PRICE_REVIEW,
            ResearchQueueReason.MANUAL_RESEARCH_REQUEST,
            ResearchQueueReason.COLLECTION_SYNC_ISSUE,
        )
    ):
        return ResearchQueuePriority.MEDIUM
    if ResearchQueueReason.MISSING_VERIFIED_VALUATION in reasons:
        return ResearchQueuePriority.LOW
    return ResearchQueuePriority.INFORMATIONAL


def _status(
    priority: ResearchQueuePriority,
    blockers: list[str],
) -> ResearchQueueStatus:
    if blockers:
        return ResearchQueueStatus.BLOCKED
    if priority == ResearchQueuePriority.INFORMATIONAL:
        return ResearchQueueStatus.COMPLETED
    return ResearchQueueStatus.READY


def _item_sort_key(item: ResearchQueueItem) -> tuple[int, int, str, str, str]:
    blocked_rank = 0 if item.status == ResearchQueueStatus.BLOCKED else 1
    return (
        PRIORITY_RANK[item.priority],
        blocked_rank,
        item.asset_name,
        item.cert_number or "",
        item.queue_item_id,
    )


def _nav_lines_by_asset(snapshots: tuple[PortfolioNavSnapshot, ...]) -> dict[str, Any]:
    return {
        line.asset_id: line
        for snapshot in snapshots
        for line in snapshot.asset_lines
    }


def _coverage_status(
    nav_line: Any,
    verified_valuation: bool,
    any_valuation: bool,
) -> str:
    if nav_line is not None:
        return nav_line.coverage_status.value
    if verified_valuation:
        return ValuationCoverageStatus.VERIFIED.value
    if any_valuation:
        return ValuationCoverageStatus.ESTIMATED.value
    return ValuationCoverageStatus.MISSING.value


def _has_verified_valuation(
    valuations: tuple[ValuationRecord, ...],
    evidence: _EvidenceCounts,
) -> bool:
    if evidence.verified:
        return True
    return any(
        valuation.source == ValuationSource.EBAY_SOLD
        and valuation.market_value is not None
        for valuation in valuations
    )


def _multiple_eligible_valuations(valuations: tuple[ValuationRecord, ...]) -> bool:
    eligible = [
        valuation
        for valuation in valuations
        if valuation.market_value is not None or valuation.estimated_value is not None
    ]
    return len(eligible) > 1


def _evidence_counts(
    asset_id: str,
    batches: tuple[EbaySoldEvidenceBatch, ...],
) -> _EvidenceCounts:
    counts = {
        "current": 0,
        "verified": 0,
        "review": 0,
        "rejected": 0,
        "no_match": 0,
    }
    for batch in batches:
        for evidence in batch.evidence:
            if evidence.asset_id != asset_id:
                continue
            counts["current"] += 1
            if evidence.status == EvidenceStatus.VERIFIED:
                counts["verified"] += 1
            elif evidence.status == EvidenceStatus.NEEDS_REVIEW:
                counts["review"] += 1
            elif evidence.status == EvidenceStatus.REJECTED:
                counts["rejected"] += 1
            elif evidence.status == EvidenceStatus.NO_MATCH:
                counts["no_match"] += 1
    return _EvidenceCounts(**counts)


def _differences_for_asset(
    asset_id: str,
    cert_number: str,
    differences: tuple[CollectionDifference, ...],
) -> tuple[CollectionDifference, ...]:
    return tuple(
        difference
        for difference in differences
        if difference.asset_id == asset_id or difference.cert_number == cert_number
    )


def _is_core(asset: dict[str, Any]) -> bool:
    collection_type = str(asset.get("collection_type") or "").strip().upper()
    asset_master = asset.get("asset_master") if isinstance(asset.get("asset_master"), dict) else {}
    watch_status = str(asset_master.get("watch_status") or "").strip().upper()
    return collection_type == "CORE" or watch_status in {"CORE", "PRIORITY", "HIGH"}


def _is_watchlist(asset_master: dict[str, Any]) -> bool:
    return str(asset_master.get("watch_status") or "").strip().upper() in {"WATCH", "WATCHLIST", "TRACK"}


def _has_query_identity(asset: dict[str, Any]) -> bool:
    required = ("year", "set", "card_number", "player", "grade_company", "grade")
    return all(_text(asset.get(field)) for field in required)


def _asset_name(asset: dict[str, Any]) -> str:
    for field_name in ("asset_name", "card_name", "name", "title"):
        value = _text(asset.get(field_name))
        if value:
            return value
    parts = [
        _text(asset.get("year")),
        _text(asset.get("set") or asset.get("brand")),
        _text(asset.get("player")),
        _text(asset.get("card_number")),
        _text(asset.get("grade_company")),
        _text(asset.get("grade")),
    ]
    return " ".join(part for part in parts if part) or _text(asset.get("asset_id")) or "Unknown Asset"


def _valid_url(value: str) -> bool:
    return value.startswith("https://") or value.startswith("http://")


def _text(value: Any) -> str:
    return str(value or "").strip()
