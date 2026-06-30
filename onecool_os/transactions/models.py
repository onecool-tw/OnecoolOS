"""Shared transaction domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from onecool_os.core.exceptions import OnecoolOSError


class TransactionError(OnecoolOSError):
    """Raised for transaction framework errors."""


class TransactionType(StrEnum):
    """Supported shared transaction types."""

    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    TRANSFER = "TRANSFER"
    FEE = "FEE"
    ADJUSTMENT = "ADJUSTMENT"


@dataclass(frozen=True)
class BaseTransaction:
    """Immutable shared transaction record."""

    transaction_id: str
    date: date
    asset_id: str
    transaction_type: TransactionType
    currency: str
    amount: Decimal
    notes: str = ""

    def __post_init__(self) -> None:
        transaction_id = _require_text(
            self.transaction_id,
            "transaction_id",
        )
        asset_id = _require_text(self.asset_id, "asset_id")
        currency = _require_currency(self.currency)
        transaction_type = _transaction_type(self.transaction_type)
        amount = _amount(self.amount, transaction_type)

        object.__setattr__(self, "transaction_id", transaction_id)
        object.__setattr__(self, "asset_id", asset_id)
        object.__setattr__(self, "currency", currency)
        object.__setattr__(self, "transaction_type", transaction_type)
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "notes", self.notes.strip())

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "transaction_id": self.transaction_id,
            "date": self.date.isoformat(),
            "asset_id": self.asset_id,
            "transaction_type": self.transaction_type.value,
            "currency": self.currency,
            "amount": _format_decimal(self.amount),
            "notes": self.notes,
        }


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TransactionError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _require_currency(value: str) -> str:
    if not isinstance(value, str):
        raise TransactionError("currency must be a three-letter code.")
    currency = value.strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise TransactionError(f"Invalid currency: {value}")
    return currency


def _transaction_type(value: TransactionType | str) -> TransactionType:
    try:
        return TransactionType(str(value).upper())
    except ValueError as exc:
        raise TransactionError(f"Invalid transaction_type: {value}") from exc


def _amount(value: Decimal, transaction_type: TransactionType) -> Decimal:
    amount = Decimal(str(value))
    if not amount.is_finite():
        raise TransactionError(f"Invalid amount: {value}")
    if transaction_type == TransactionType.ADJUSTMENT:
        if amount == Decimal("0"):
            raise TransactionError(f"Invalid amount: {value}")
        return amount
    if amount <= Decimal("0"):
        raise TransactionError(f"Invalid amount: {value}")
    return amount


def _format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"
