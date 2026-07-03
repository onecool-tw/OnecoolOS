"""Read-only portfolio aggregation service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from onecool_os.portfolio.loader import PortfolioLoader
from onecool_os.portfolio.models import Holding
from onecool_os.portfolio.models import Portfolio
from onecool_os.services.base import BaseService


class PortfolioService(BaseService):
    """Stable read-only interface for portfolio aggregation."""

    def __init__(self, loader: PortfolioLoader | None = None) -> None:
        super().__init__(service_name="portfolio")
        self.loader = loader or PortfolioLoader()
        self._portfolio: Portfolio | None = None

    def load(self, json_path: str | Path) -> "PortfolioService":
        """Load portfolio data from JSON."""

        self._portfolio = self.loader.load(json_path)
        self._mark_loaded(str(json_path))
        return self

    def list_holdings(self) -> tuple[Holding, ...]:
        """Return loaded aggregation holdings."""

        self.validate_ready()
        if self._portfolio is None:
            return ()
        return self._portfolio.list_holdings()

    def get_holding_by_asset_id(self, asset_id: str) -> Holding | None:
        """Return a holding by asset id, or None when missing."""

        self.validate_ready()
        for holding in self.list_holdings():
            if holding.asset_id == asset_id:
                return holding
        return None

    def get_summary(self) -> dict[str, Any]:
        """Return a JSON-safe portfolio summary."""

        self.validate_ready()
        if self._portfolio is None:
            return {}
        payload = self._portfolio.to_dict()
        return {
            key: value
            for key, value in payload.items()
            if key != "holdings"
        }
