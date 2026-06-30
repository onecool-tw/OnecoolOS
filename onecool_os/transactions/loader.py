"""JSON loader for shared transaction records."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from onecool_os.transactions.models import BaseTransaction
from onecool_os.transactions.models import TransactionError
from onecool_os.transactions.registry import TransactionRegistry


class TransactionLoaderError(TransactionError):
    """Raised when transaction JSON cannot be loaded."""


@dataclass(frozen=True)
class TransactionImportResult:
    """Loaded transactions and registry projection."""

    registry: TransactionRegistry
    transactions: tuple[BaseTransaction, ...]


class TransactionLoader:
    """Load shared transaction records from JSON."""

    required_root_fields = frozenset({"transactions"})
    required_transaction_fields = frozenset(
        {
            "transaction_id",
            "date",
            "asset_id",
            "transaction_type",
            "currency",
            "amount",
        }
    )

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("onecool_os.transactions")

    def load(self, json_path: str | Path) -> TransactionImportResult:
        """Load and validate a transactions JSON file."""

        path = Path(json_path)
        self.logger.info("Starting transactions import from %s", path)
        payload = self._read_payload(path)
        self._validate_required_fields(payload, self.required_root_fields, "root")
        transactions_payload = payload["transactions"]
        if not isinstance(transactions_payload, list):
            raise TransactionLoaderError("transactions must be a list.")

        registry = TransactionRegistry()
        transactions = []
        for index, transaction_payload in enumerate(transactions_payload):
            transaction = self._load_transaction(transaction_payload, index)
            try:
                registry.register(transaction)
            except TransactionError as exc:
                raise TransactionLoaderError(str(exc)) from exc
            transactions.append(transaction)

        self.logger.info(
            "Transactions import completed with %s records.",
            len(transactions),
        )
        return TransactionImportResult(
            registry=registry,
            transactions=tuple(transactions),
        )

    def _read_payload(self, path: Path) -> dict[str, Any]:
        try:
            raw_payload = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.logger.error("Transactions JSON file cannot be read: %s", path)
            raise TransactionLoaderError(
                f"Transactions JSON file cannot be read: {path}"
            ) from exc

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            self.logger.error("Invalid transactions JSON: %s", exc.msg)
            raise TransactionLoaderError(
                f"Invalid transactions JSON: {exc.msg}"
            ) from exc

        if not isinstance(payload, dict):
            raise TransactionLoaderError(
                "Transactions JSON root must be an object."
            )
        return payload

    def _load_transaction(
        self,
        payload: Any,
        index: int,
    ) -> BaseTransaction:
        if not isinstance(payload, dict):
            raise TransactionLoaderError(
                f"transactions[{index}] must be an object."
            )
        self._validate_required_fields(
            payload,
            self.required_transaction_fields,
            f"transactions[{index}]",
        )

        try:
            return BaseTransaction(
                transaction_id=self._require_text(
                    payload["transaction_id"],
                    "transaction_id",
                ),
                date=self._parse_date(payload["date"]),
                asset_id=self._require_text(payload["asset_id"], "asset_id"),
                transaction_type=self._require_text(
                    payload["transaction_type"],
                    "transaction_type",
                ),
                currency=self._require_text(payload["currency"], "currency"),
                amount=self._parse_decimal(payload["amount"], "amount"),
                notes=self._optional_text(payload.get("notes")) or "",
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

    def _require_text(self, value: Any, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise TransactionLoaderError(
                f"{field_name} must be a non-empty string."
            )
        return value.strip()

    def _optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            return None
        return value.strip()

    def _parse_date(self, value: Any) -> date:
        if not isinstance(value, str):
            raise TransactionLoaderError(f"Invalid date: {value}")
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise TransactionLoaderError(f"Invalid date: {value}") from exc

    def _parse_decimal(self, value: Any, field_name: str) -> Decimal:
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise TransactionLoaderError(f"Invalid {field_name}: {value}") from exc

        if not decimal_value.is_finite():
            raise TransactionLoaderError(f"Invalid {field_name}: {value}")
        return decimal_value
