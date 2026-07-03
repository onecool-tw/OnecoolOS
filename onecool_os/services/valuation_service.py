"""Read-only valuation service."""

from __future__ import annotations

from pathlib import Path

from onecool_os.services.base import BaseService
from onecool_os.valuation.loader import ValuationImportResult
from onecool_os.valuation.loader import ValuationLoader
from onecool_os.valuation.models import ValuationRecord


class ValuationService(BaseService):
    """Stable read-only interface for valuation history."""

    def __init__(self, loader: ValuationLoader | None = None) -> None:
        super().__init__(service_name="valuation")
        self.loader = loader or ValuationLoader()
        self._valuation_book: ValuationImportResult | None = None

    def load(self, json_path: str | Path) -> "ValuationService":
        """Load valuation data from JSON."""

        self._valuation_book = self.loader.load(json_path)
        self._mark_loaded(str(json_path))
        return self

    def list_valuations(self) -> tuple[ValuationRecord, ...]:
        """Return loaded valuation records."""

        self.validate_ready()
        if self._valuation_book is None:
            return ()
        return self._valuation_book.valuations

    def get_valuation_by_id(
        self,
        valuation_id: str,
    ) -> ValuationRecord | None:
        """Return a valuation by id, or None when missing."""

        self.validate_ready()
        for valuation in self.list_valuations():
            if valuation.valuation_id == valuation_id:
                return valuation
        return None

    def get_valuations_for_asset(
        self,
        asset_id: str,
    ) -> tuple[ValuationRecord, ...]:
        """Return valuations for an asset in stable date order."""

        self.validate_ready()
        return tuple(
            sorted(
                (
                    valuation
                    for valuation in self.list_valuations()
                    if valuation.asset_id == asset_id
                ),
                key=lambda valuation: (
                    valuation.valuation_date,
                    valuation.valuation_id,
                ),
            )
        )

    def get_latest_valuation_for_asset(
        self,
        asset_id: str,
    ) -> ValuationRecord | None:
        """Return the latest valuation for an asset, or None when missing."""

        valuations = self.get_valuations_for_asset(asset_id)
        if not valuations:
            return None
        return valuations[-1]
