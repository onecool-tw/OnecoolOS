"""Registry for shared transactions."""

from __future__ import annotations

from onecool_os.transactions.models import BaseTransaction
from onecool_os.transactions.models import TransactionError


class TransactionRegistry:
    """Register and retrieve immutable transaction records."""

    def __init__(self) -> None:
        self._transactions: dict[str, BaseTransaction] = {}

    def register(self, transaction: BaseTransaction) -> None:
        """Register a transaction."""

        if transaction.transaction_id in self._transactions:
            raise TransactionError(
                f"Transaction already registered: "
                f"{transaction.transaction_id}"
            )
        self._transactions[transaction.transaction_id] = transaction

    def unregister(self, transaction_id: str) -> BaseTransaction:
        """Unregister and return a transaction."""

        try:
            return self._transactions.pop(transaction_id)
        except KeyError as exc:
            raise TransactionError(
                f"Unknown transaction: {transaction_id}"
            ) from exc

    def get(self, transaction_id: str) -> BaseTransaction:
        """Return a transaction by id."""

        try:
            return self._transactions[transaction_id]
        except KeyError as exc:
            raise TransactionError(
                f"Unknown transaction: {transaction_id}"
            ) from exc

    def list(self) -> tuple[BaseTransaction, ...]:
        """Return transactions in stable transaction id order."""

        return tuple(
            self._transactions[transaction_id]
            for transaction_id in sorted(self._transactions)
        )
