"""Read-only analytics service."""

from __future__ import annotations

from pathlib import Path

from onecool_os.analytics.loader import AnalyticsImportResult
from onecool_os.analytics.loader import AnalyticsLoader
from onecool_os.analytics.models import AnalyticsSnapshot
from onecool_os.services.base import BaseService


class AnalyticsService(BaseService):
    """Stable read-only interface for analytics snapshots."""

    def __init__(self, loader: AnalyticsLoader | None = None) -> None:
        super().__init__(service_name="analytics")
        self.loader = loader or AnalyticsLoader()
        self._analytics_book: AnalyticsImportResult | None = None

    def load(self, json_path: str | Path) -> "AnalyticsService":
        """Load analytics data from JSON."""

        self._analytics_book = self.loader.load(json_path)
        self._mark_loaded(str(json_path))
        return self

    def list_snapshots(self) -> tuple[AnalyticsSnapshot, ...]:
        """Return loaded analytics snapshots."""

        self.validate_ready()
        if self._analytics_book is None:
            return ()
        return self._analytics_book.snapshots

    def get_snapshot_by_id(
        self,
        snapshot_id: str,
    ) -> AnalyticsSnapshot | None:
        """Return a snapshot by id, or None when missing."""

        self.validate_ready()
        for snapshot in self.list_snapshots():
            if snapshot.snapshot_id == snapshot_id:
                return snapshot
        return None

    def get_latest_snapshot_for_portfolio(
        self,
        portfolio_id: str,
    ) -> AnalyticsSnapshot | None:
        """Return the latest snapshot for a portfolio, or None when missing."""

        snapshots = tuple(
            sorted(
                (
                    snapshot
                    for snapshot in self.list_snapshots()
                    if snapshot.portfolio_id == portfolio_id
                ),
                key=lambda snapshot: (
                    snapshot.snapshot_date,
                    snapshot.snapshot_id,
                ),
            )
        )
        if not snapshots:
            return None
        return snapshots[-1]
