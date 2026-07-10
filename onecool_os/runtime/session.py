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
    generated_at: datetime | None = None

    def __post_init__(self) -> None:
        generated_at = self.generated_at or datetime.now(UTC)
        if not isinstance(generated_at, datetime):
            raise ValueError("generated_at must be a datetime.")
        imported_records = tuple(dict(record) for record in self.imported_records)
        asset_master_records = tuple(self.asset_master_records)
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

    def with_imported_records(
        self,
        imported_records: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    ) -> RuntimeSession:
        """Return a new session after replacing imported collection records."""

        return RuntimeSession(
            imported_records=tuple(dict(record) for record in imported_records),
            asset_master_records=self.asset_master_records,
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
