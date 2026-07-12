"""Runtime session models for Onecool OS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import Any

from onecool_os.assets.master import AssetMasterRecord
from onecool_os.assets.master import merge_asset_master
from onecool_os.sync import CollectionDifference
from onecool_os.sync import SyncReport
from onecool_os.sync import compare_collection
from onecool_os.valuation.evidence import EbaySoldEvidence
from onecool_os.valuation.evidence import EbaySoldEvidenceBatch
from onecool_os.valuation.evidence import EvidenceStatus

METADATA_DIFFERENCE_TYPES = frozenset(
    {
        "COST_OVERRIDE",
        "EBAY_URL_MISSING",
        "PSA_URL_MISSING",
        "TARGET_PRICE_MISSING",
        "NOTES_CHANGED",
    }
)


@dataclass(frozen=True)
class RuntimeSession:
    """Runtime session with automatic collection sync integrity status."""

    imported_records: tuple[dict[str, Any], ...] = ()
    asset_master_records: tuple[AssetMasterRecord, ...] = ()
    ebay_sold_evidence_batches: tuple[EbaySoldEvidenceBatch, ...] = ()
    generated_at: datetime | None = None

    def __post_init__(self) -> None:
        generated_at = self.generated_at or datetime.now(UTC)
        if not isinstance(generated_at, datetime):
            raise ValueError("generated_at must be a datetime.")
        imported_records = tuple(dict(record) for record in self.imported_records)
        asset_master_records = tuple(self.asset_master_records)
        ebay_sold_evidence_batches = tuple(self.ebay_sold_evidence_batches)
        enriched_records = merge_asset_master(
            imported_records,
            asset_master_records,
        )
        sync_report = compare_collection(
            imported_records,
            asset_master_records,
            reference_datetime=generated_at,
        )
        object.__setattr__(self, "generated_at", generated_at)
        object.__setattr__(self, "imported_records", imported_records)
        object.__setattr__(self, "asset_master_records", asset_master_records)
        object.__setattr__(
            self,
            "ebay_sold_evidence_batches",
            ebay_sold_evidence_batches,
        )
        object.__setattr__(self, "enriched_runtime_assets", enriched_records)
        object.__setattr__(self, "sync_report", sync_report)
        object.__setattr__(
            self,
            "collection_health",
            sync_report.collection_health,
        )

    def collection_differences(self) -> tuple[CollectionDifference, ...]:
        """Return all collection sync differences."""

        return self.sync_report.differences

    def has_sync_issues(self) -> bool:
        """Return whether collection sync found any issue."""

        return bool(self.sync_report.differences or self.sync_report.warnings)

    def has_critical_sync_issues(self) -> bool:
        """Return whether collection sync found critical issues."""

        return any(
            difference.severity == "CRITICAL"
            for difference in self.sync_report.differences
        )

    def critical_sync_issues(self) -> tuple[CollectionDifference, ...]:
        """Return critical sync differences for future decision priority."""

        return self._differences_by_severity("CRITICAL")

    def high_priority_sync_issues(self) -> tuple[CollectionDifference, ...]:
        """Return high-priority sync differences for future decision priority."""

        return self._differences_by_severity("HIGH")

    def metadata_sync_issues(self) -> tuple[CollectionDifference, ...]:
        """Return metadata sync differences for future decision priority."""

        return tuple(
            difference
            for difference in self.sync_report.differences
            if difference.difference_type in METADATA_DIFFERENCE_TYPES
        )

    def verified_ebay_sold_evidence(self) -> tuple[EbaySoldEvidence, ...]:
        """Return eBay Sold evidence validated as verified."""

        return self._ebay_evidence_by_status(EvidenceStatus.VERIFIED)

    def review_required_ebay_evidence(self) -> tuple[EbaySoldEvidence, ...]:
        """Return eBay Sold evidence requiring human review."""

        return self._ebay_evidence_by_status(EvidenceStatus.NEEDS_REVIEW)

    def rejected_ebay_evidence(self) -> tuple[EbaySoldEvidence, ...]:
        """Return rejected eBay Sold evidence."""

        return self._ebay_evidence_by_status(EvidenceStatus.REJECTED)

    def ebay_evidence_coverage(self) -> dict[str, int]:
        """Return deterministic evidence coverage for imported assets."""

        imported_asset_ids = {
            str(record.get("asset_id") or "")
            for record in self.imported_records
            if record.get("asset_id")
        }
        covered_asset_ids = {
            evidence.asset_id
            for batch in self.ebay_sold_evidence_batches
            for evidence in batch.evidence
        }
        covered = len(imported_asset_ids & covered_asset_ids)
        total = len(imported_asset_ids)
        return {
            "total_assets": total,
            "covered_assets": covered,
            "missing_assets": max(total - covered, 0),
        }

    def attach_ebay_evidence_batch(
        self,
        batch: EbaySoldEvidenceBatch,
    ) -> RuntimeSession:
        """Return a new session with an additional eBay Sold evidence batch."""

        return RuntimeSession(
            imported_records=self.imported_records,
            asset_master_records=self.asset_master_records,
            ebay_sold_evidence_batches=(
                *self.ebay_sold_evidence_batches,
                batch,
            ),
            generated_at=self.generated_at,
        )

    def build_portfolio_nav(
        self,
        valuation_records: list[Any] | tuple[Any, ...] = (),
    ) -> tuple[Any, ...]:
        """Build Portfolio NAV snapshots by delegating to the NAV Engine."""

        from onecool_os.portfolio.nav import PortfolioNavEngine

        return PortfolioNavEngine().build_from_runtime_session(
            self,
            valuation_records,
        )

    def portfolio_nav_snapshots(
        self,
        valuation_records: list[Any] | tuple[Any, ...] = (),
    ) -> tuple[Any, ...]:
        """Return Portfolio NAV snapshots for this runtime session."""

        return self.build_portfolio_nav(valuation_records)

    def build_live_portfolio_nav(self) -> tuple[Any, ...]:
        """Build NAV from canonical runtime ValuationRecords by delegation."""

        return self.build_portfolio_nav(self.build_valuation_records())

    def build_fair_value(
        self,
        *,
        sample_size: int = 10,
        window_days: int = 180,
    ) -> tuple[Any, ...]:
        """Build Fair Value snapshots by delegating to the Fair Value Engine."""

        from onecool_os.fair_value import OnecoolFairValueEngine

        return OnecoolFairValueEngine().build_from_runtime_session(
            self,
            sample_size=sample_size,
            window_days=window_days,
        )

    def fair_value(
        self,
        asset_id: str,
        *,
        sample_size: int = 10,
        window_days: int = 180,
    ) -> Any:
        """Return the Fair Value snapshot for one asset, if present."""

        snapshots = self.build_fair_value(
            sample_size=sample_size,
            window_days=window_days,
        )
        for snapshot in snapshots:
            if snapshot.asset_id == asset_id:
                return snapshot
        return None

    def build_valuation_records(self) -> tuple[Any, ...]:
        """Build runtime ValuationRecords by delegating to valuation integration."""

        from onecool_os.valuation.integration import FairValueValuationEngine

        return FairValueValuationEngine().build_from_runtime_session(
            self,
        ).valuation_records

    def valuation_records(self) -> tuple[Any, ...]:
        """Return canonical runtime ValuationRecords."""

        return self.build_valuation_records()

    def valuation_record(self, asset_id: str) -> Any:
        """Return one canonical runtime ValuationRecord by asset id, if present."""

        for record in self.build_valuation_records():
            if record.asset_id == asset_id:
                return record
        return None

    def build_research_queue(
        self,
        valuation_records: list[Any] | tuple[Any, ...] = (),
        nav_snapshots: list[Any] | tuple[Any, ...] = (),
    ) -> Any:
        """Build a Research Queue snapshot by delegating to the engine."""

        from onecool_os.research.queue import ResearchQueueEngine

        return ResearchQueueEngine().build(
            self,
            valuation_records=tuple(valuation_records),
            nav_snapshots=tuple(nav_snapshots),
        )

    def research_queue_snapshot(
        self,
        valuation_records: list[Any] | tuple[Any, ...] = (),
        nav_snapshots: list[Any] | tuple[Any, ...] = (),
    ) -> Any:
        """Return the Research Queue snapshot for this runtime session."""

        return self.build_research_queue(
            valuation_records,
            nav_snapshots,
        )

    def open_research_items(
        self,
        valuation_records: list[Any] | tuple[Any, ...] = (),
        nav_snapshots: list[Any] | tuple[Any, ...] = (),
    ) -> tuple[Any, ...]:
        """Return research items that are not completed or skipped."""

        snapshot = self.build_research_queue(valuation_records, nav_snapshots)
        return tuple(
            item
            for item in snapshot.items
            if item.status.value not in {"COMPLETED", "SKIPPED"}
        )

    def ready_research_items(
        self,
        valuation_records: list[Any] | tuple[Any, ...] = (),
        nav_snapshots: list[Any] | tuple[Any, ...] = (),
    ) -> tuple[Any, ...]:
        """Return ready research queue items."""

        snapshot = self.build_research_queue(valuation_records, nav_snapshots)
        return tuple(item for item in snapshot.items if item.status.value == "READY")

    def blocked_research_items(
        self,
        valuation_records: list[Any] | tuple[Any, ...] = (),
        nav_snapshots: list[Any] | tuple[Any, ...] = (),
    ) -> tuple[Any, ...]:
        """Return blocked research queue items."""

        snapshot = self.build_research_queue(valuation_records, nav_snapshots)
        return tuple(item for item in snapshot.items if item.status.value == "BLOCKED")

    def critical_research_items(
        self,
        valuation_records: list[Any] | tuple[Any, ...] = (),
        nav_snapshots: list[Any] | tuple[Any, ...] = (),
    ) -> tuple[Any, ...]:
        """Return critical research queue items."""

        snapshot = self.build_research_queue(valuation_records, nav_snapshots)
        return tuple(item for item in snapshot.items if item.priority.value == "CRITICAL")

    def with_imported_records(
        self,
        imported_records: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    ) -> RuntimeSession:
        """Return a new session after replacing imported collection records."""

        return RuntimeSession(
            imported_records=tuple(dict(record) for record in imported_records),
            asset_master_records=self.asset_master_records,
            ebay_sold_evidence_batches=self.ebay_sold_evidence_batches,
            generated_at=self.generated_at,
        )

    def with_asset_master_records(
        self,
        asset_master_records: list[AssetMasterRecord]
        | tuple[AssetMasterRecord, ...],
    ) -> RuntimeSession:
        """Return a new session after replacing Asset Master records."""

        return RuntimeSession(
            imported_records=self.imported_records,
            asset_master_records=tuple(asset_master_records),
            ebay_sold_evidence_batches=self.ebay_sold_evidence_batches,
            generated_at=self.generated_at,
        )

    def _differences_by_severity(
        self,
        severity: str,
    ) -> tuple[CollectionDifference, ...]:
        return tuple(
            difference
            for difference in self.sync_report.differences
            if difference.severity == severity
        )

    def _ebay_evidence_by_status(
        self,
        status: EvidenceStatus,
    ) -> tuple[EbaySoldEvidence, ...]:
        return tuple(
            evidence
            for batch in self.ebay_sold_evidence_batches
            for evidence in batch.evidence
            if evidence.status == status
        )
