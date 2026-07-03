"""Dashboard view builder."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from onecool_os.dashboard.analytics_view import DashboardAnalyticsView
from onecool_os.dashboard.models import DashboardSection
from onecool_os.dashboard.models import DashboardView
from onecool_os.services import AnalyticsService
from onecool_os.services import LedgerService
from onecool_os.services import PortfolioService
from onecool_os.services import ServiceError
from onecool_os.services import ValuationService


class DashboardBuilder:
    """Build display-only dashboard views from services."""

    def __init__(
        self,
        portfolio_service: PortfolioService | None = None,
        analytics_service: AnalyticsService | None = None,
        valuation_service: ValuationService | None = None,
        ledger_service: LedgerService | None = None,
    ) -> None:
        self.portfolio_service = portfolio_service or PortfolioService()
        self.analytics_service = analytics_service or AnalyticsService()
        self.valuation_service = valuation_service or ValuationService()
        self.ledger_service = ledger_service or LedgerService()

    def build(
        self,
        dashboard_id: str = "dashboard-demo",
        dashboard_name: str = "Onecool Dashboard",
        base_currency: str = "TWD",
    ) -> DashboardView:
        """Build a dashboard view from service outputs."""

        generated_at = datetime.now(tz=UTC)
        return DashboardView(
            dashboard_id=dashboard_id,
            dashboard_name=dashboard_name,
            base_currency=base_currency,
            generated_at=generated_at,
            portfolio_summary=self._portfolio_section(generated_at),
            analytics_summary=self._analytics_section(generated_at),
            valuation_summary=self._valuation_section(generated_at),
            ledger_summary=self._ledger_section(generated_at),
            note="Display-only dashboard view.",
            tags=["dashboard", "display-only"],
        )

    @classmethod
    def demo(cls) -> DashboardView:
        """Build a dashboard view from bundled example files."""

        builder = cls(
            portfolio_service=PortfolioService().load(
                "data/portfolio/portfolio.example.json"
            ),
            analytics_service=AnalyticsService().load(
                "data/analytics/analytics.example.json"
            ),
            valuation_service=ValuationService().load(
                "data/valuation/valuation.example.json"
            ),
            ledger_service=LedgerService().load(
                "data/transactions/ledger.example.json"
            ),
        )
        return builder.build()

    def _portfolio_section(self, generated_at: datetime) -> DashboardSection:
        return DashboardSection(
            section_id="portfolio-summary",
            title="Portfolio Summary",
            content=self._safe_content(
                "portfolio",
                lambda: {
                    "summary": self.portfolio_service.get_summary(),
                    "holding_count": len(
                        self.portfolio_service.list_holdings()
                    ),
                },
            ),
            source_service="portfolio",
            generated_at=generated_at,
        )

    def _analytics_section(self, generated_at: datetime) -> DashboardSection:
        return DashboardSection(
            section_id="analytics-summary",
            title="Analytics Summary",
            content=self._safe_content(
                "analytics",
                lambda: self._latest_analytics_content(),
            ),
            source_service="analytics",
            generated_at=generated_at,
        )

    def _valuation_section(self, generated_at: datetime) -> DashboardSection:
        return DashboardSection(
            section_id="valuation-summary",
            title="Valuation Summary",
            content=self._safe_content(
                "valuation",
                lambda: {
                    "valuation_count": len(
                        self.valuation_service.list_valuations()
                    ),
                },
            ),
            source_service="valuation",
            generated_at=generated_at,
        )

    def _ledger_section(self, generated_at: datetime) -> DashboardSection:
        return DashboardSection(
            section_id="ledger-summary",
            title="Ledger Summary",
            content=self._safe_content(
                "ledger",
                lambda: {
                    "transaction_count": len(
                        self.ledger_service.list_transactions()
                    ),
                    "event_count": len(self.ledger_service.list_events()),
                },
            ),
            source_service="ledger",
            generated_at=generated_at,
        )

    def _latest_analytics_content(self) -> dict[str, Any]:
        snapshots = self.analytics_service.list_snapshots()
        latest_snapshot = snapshots[-1] if snapshots else None
        return {
            "snapshot_count": len(snapshots),
            "latest_snapshot": (
                latest_snapshot.to_dict() if latest_snapshot else None
            ),
            "analytics_view": DashboardAnalyticsView.from_snapshot(
                latest_snapshot
            ).to_dict(),
        }

    def _safe_content(
        self,
        service_name: str,
        factory: Any,
    ) -> dict[str, Any]:
        try:
            content = factory()
        except ServiceError as exc:
            return {
                "status": "unavailable",
                "service": service_name,
                "error": str(exc),
            }
        return {
            "status": "ready",
            "service": service_name,
            **content,
        }
