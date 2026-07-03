"""Read-only ledger service."""

from __future__ import annotations

from pathlib import Path

from onecool_os.services.base import BaseService
from onecool_os.transactions.loader import LedgerImportResult
from onecool_os.transactions.loader import TransactionLoader
from onecool_os.transactions.models import Event
from onecool_os.transactions.models import Transaction


class LedgerService(BaseService):
    """Stable read-only interface for ledger data."""

    def __init__(self, loader: TransactionLoader | None = None) -> None:
        super().__init__(service_name="ledger")
        self.loader = loader or TransactionLoader()
        self._ledger: LedgerImportResult | None = None

    def load(self, json_path: str | Path) -> "LedgerService":
        """Load ledger data from JSON."""

        self._ledger = self.loader.load(json_path)
        self._mark_loaded(str(json_path))
        return self

    def list_transactions(self) -> tuple[Transaction, ...]:
        """Return loaded transactions."""

        self.validate_ready()
        return self._ledger.transactions if self._ledger else ()

    def list_events(self) -> tuple[Event, ...]:
        """Return loaded lifecycle events."""

        self.validate_ready()
        return self._ledger.events if self._ledger else ()

    def get_transaction_by_id(
        self,
        transaction_id: str,
    ) -> Transaction | None:
        """Return a transaction by id, or None when missing."""

        self.validate_ready()
        for transaction in self.list_transactions():
            if transaction.transaction_id == transaction_id:
                return transaction
        return None

    def get_event_by_id(self, event_id: str) -> Event | None:
        """Return an event by id, or None when missing."""

        self.validate_ready()
        for event in self.list_events():
            if event.event_id == event_id:
                return event
        return None
