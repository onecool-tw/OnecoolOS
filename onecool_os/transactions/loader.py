"""JSON loader for shared ledger records."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from onecool_os.transactions.models import Event
from onecool_os.transactions.models import Transaction
from onecool_os.transactions.validation import TransactionError
from onecool_os.transactions.validation import optional_text
from onecool_os.transactions.validation import require_currency


class TransactionLoaderError(TransactionError):
    """Raised when ledger JSON cannot be loaded."""


@dataclass(frozen=True)
class LedgerImportResult:
    """Loaded ledger data."""

    ledger_name: str | None
    base_currency: str | None
    transactions: tuple[Transaction, ...]
    events: tuple[Event, ...]


TransactionImportResult = LedgerImportResult


class TransactionLoader:
    """Load shared transaction and event records from JSON."""

    required_transaction_fields = frozenset(
        {
            "transaction_id",
            "asset_id",
            "asset_type",
            "transaction_type",
            "trade_date",
            "currency",
            "status",
        }
    )
    legacy_transaction_fields = frozenset(
        {
            "transaction_id",
            "date",
            "asset_id",
            "transaction_type",
            "currency",
            "amount",
        }
    )
    required_event_fields = frozenset(
        {
            "event_id",
            "event_type",
            "event_date",
        }
    )

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("onecool_os.transactions")

    def load(self, json_path: str | Path) -> LedgerImportResult:
        """Load and validate a ledger JSON file."""

        path = Path(json_path)
        self.logger.info("Starting ledger import from %s", path)
        payload = self._read_payload(path)
        transactions_payload = payload.get("transactions")
        events_payload = payload.get("events", [])
        if not isinstance(transactions_payload, list):
            raise TransactionLoaderError("transactions must be a list.")
        if not isinstance(events_payload, list):
            raise TransactionLoaderError("events must be a list.")

        transactions = tuple(
            self._load_transaction(transaction_payload, index)
            for index, transaction_payload in enumerate(transactions_payload)
        )
        self._validate_duplicate_ids(
            [transaction.transaction_id for transaction in transactions],
            "transaction_id",
        )
        events = tuple(
            self._load_event(event_payload, index)
            for index, event_payload in enumerate(events_payload)
        )
        self._validate_duplicate_ids(
            [event.event_id for event in events],
            "event_id",
        )
        self.logger.info(
            "Ledger import completed with %s transactions and %s events.",
            len(transactions),
            len(events),
        )
        base_currency = payload.get("base_currency")
        return LedgerImportResult(
            ledger_name=optional_text(
                payload.get("ledger_name"),
                "ledger_name",
            ),
            base_currency=(
                require_currency(base_currency)
                if base_currency not in (None, "")
                else None
            ),
            transactions=transactions,
            events=events,
        )

    def _read_payload(self, path: Path) -> dict[str, Any]:
        try:
            raw_payload = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise TransactionLoaderError(
                f"Ledger JSON file cannot be read: {path}"
            ) from exc

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise TransactionLoaderError(
                f"Invalid ledger JSON: {exc.msg}"
            ) from exc

        if not isinstance(payload, dict):
            raise TransactionLoaderError("Ledger JSON root must be an object.")
        return payload

    def _load_transaction(self, payload: Any, index: int) -> Transaction:
        if not isinstance(payload, dict):
            raise TransactionLoaderError(
                f"transactions[{index}] must be an object."
            )
        if "trade_date" not in payload and "date" in payload:
            payload = self._legacy_transaction_payload(payload)
        self._validate_required_fields(
            payload,
            self.required_transaction_fields,
            f"transactions[{index}]",
        )

        try:
            return Transaction(
                transaction_id=payload["transaction_id"],
                asset_id=payload["asset_id"],
                asset_type=payload["asset_type"],
                portfolio_id=payload.get("portfolio_id"),
                trade_date=payload["trade_date"],
                settlement_date=payload.get("settlement_date"),
                created_at=payload.get("created_at"),
                updated_at=payload.get("updated_at"),
                transaction_type=payload["transaction_type"],
                quantity=payload.get("quantity"),
                price=payload.get("price"),
                currency=payload["currency"],
                exchange_rate=payload.get("exchange_rate"),
                fee=payload.get("fee"),
                tax=payload.get("tax"),
                shipping=payload.get("shipping"),
                insurance=payload.get("insurance"),
                other_cost=payload.get("other_cost"),
                account=payload.get("account"),
                platform=payload.get("platform"),
                broker=payload.get("broker"),
                status=payload["status"],
                note=payload.get("note") or payload.get("notes"),
                tags=payload.get("tags"),
            )
        except TransactionError as exc:
            raise TransactionLoaderError(str(exc)) from exc

    def _legacy_transaction_payload(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._validate_required_fields(
            payload,
            self.legacy_transaction_fields,
            "legacy transaction",
        )
        return {
            "transaction_id": payload["transaction_id"],
            "asset_id": payload["asset_id"],
            "asset_type": payload.get("asset_type", "OTHER"),
            "trade_date": payload["date"],
            "transaction_type": payload["transaction_type"],
            "currency": payload["currency"],
            "status": payload.get("status", "COMPLETED"),
            "price": payload["amount"],
            "note": payload.get("notes"),
        }

    def _load_event(self, payload: Any, index: int) -> Event:
        if not isinstance(payload, dict):
            raise TransactionLoaderError(f"events[{index}] must be an object.")
        self._validate_required_fields(
            payload,
            self.required_event_fields,
            f"events[{index}]",
        )
        try:
            return Event(
                event_id=payload["event_id"],
                event_type=payload["event_type"],
                asset_id=payload.get("asset_id"),
                asset_type=payload.get("asset_type"),
                related_transaction_id=payload.get("related_transaction_id"),
                event_date=payload["event_date"],
                status=payload.get("status"),
                payload=payload.get("payload"),
                note=payload.get("note"),
                tags=payload.get("tags"),
            )
        except TransactionError as exc:
            raise TransactionLoaderError(str(exc)) from exc

    def _validate_required_fields(
        self,
        payload: dict[str, Any],
        required_fields: frozenset[str],
        location: str,
    ) -> None:
        missing_fields = sorted(required_fields - payload.keys())
        if missing_fields:
            fields = ", ".join(missing_fields)
            raise TransactionLoaderError(
                f"Missing required field in {location}: {fields}"
            )

    def _validate_duplicate_ids(
        self,
        values: list[str],
        field_name: str,
    ) -> None:
        seen: set[str] = set()
        for value in values:
            if value in seen:
                raise TransactionLoaderError(
                    f"Duplicate {field_name}: {value}"
                )
            seen.add(value)
