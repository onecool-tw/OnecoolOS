"""Shared transaction and ledger domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from onecool_os.transactions.enums import EventType
from onecool_os.transactions.enums import TransactionStatus
from onecool_os.transactions.enums import TransactionType
from onecool_os.transactions.validation import TransactionError
from onecool_os.transactions.validation import optional_text
from onecool_os.transactions.validation import parse_enum
from onecool_os.transactions.validation import parse_date
from onecool_os.transactions.validation import parse_non_negative_decimal
from onecool_os.transactions.validation import parse_optional_date
from onecool_os.transactions.validation import parse_optional_datetime
from onecool_os.transactions.validation import parse_optional_decimal
from onecool_os.transactions.validation import parse_tags
from onecool_os.transactions.validation import require_currency
from onecool_os.transactions.validation import require_text


@dataclass(frozen=True)
class Transaction:
    """Shared immutable financial transaction record."""

    transaction_id: str
    asset_id: str
    asset_type: str
    transaction_type: TransactionType | str
    trade_date: date | str
    currency: str
    status: TransactionStatus | str
    portfolio_id: str | None = None
    settlement_date: date | str | None = None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None
    quantity: Decimal | str | int | float | None = None
    price: Decimal | str | int | float | None = None
    exchange_rate: Decimal | str | int | float | None = None
    fee: Decimal | str | int | float | None = None
    tax: Decimal | str | int | float | None = None
    shipping: Decimal | str | int | float | None = None
    insurance: Decimal | str | int | float | None = None
    other_cost: Decimal | str | int | float | None = None
    account: str | None = None
    platform: str | None = None
    broker: str | None = None
    note: str | None = None
    tags: list[str] | tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "transaction_id",
            require_text(self.transaction_id, "transaction_id"),
        )
        object.__setattr__(
            self,
            "asset_id",
            require_text(self.asset_id, "asset_id"),
        )
        object.__setattr__(
            self,
            "asset_type",
            require_text(self.asset_type, "asset_type"),
        )
        object.__setattr__(
            self,
            "transaction_type",
            parse_enum(
                TransactionType,
                self.transaction_type,
                "transaction_type",
            ),
        )
        object.__setattr__(
            self,
            "trade_date",
            self.trade_date
            if isinstance(self.trade_date, date)
            else parse_date(self.trade_date, "trade_date"),
        )
        object.__setattr__(self, "currency", require_currency(self.currency))
        object.__setattr__(
            self,
            "status",
            parse_enum(TransactionStatus, self.status, "status"),
        )
        object.__setattr__(
            self,
            "portfolio_id",
            optional_text(self.portfolio_id, "portfolio_id"),
        )
        object.__setattr__(
            self,
            "settlement_date",
            parse_optional_date(self.settlement_date, "settlement_date"),
        )
        object.__setattr__(
            self,
            "created_at",
            parse_optional_datetime(self.created_at, "created_at"),
        )
        object.__setattr__(
            self,
            "updated_at",
            parse_optional_datetime(self.updated_at, "updated_at"),
        )
        for field_name in ("quantity", "price", "exchange_rate"):
            object.__setattr__(
                self,
                field_name,
                parse_optional_decimal(getattr(self, field_name), field_name),
            )
        for field_name in (
            "fee",
            "tax",
            "shipping",
            "insurance",
            "other_cost",
        ):
            object.__setattr__(
                self,
                field_name,
                parse_non_negative_decimal(
                    getattr(self, field_name),
                    field_name,
                ),
            )
        for field_name in ("account", "platform", "broker", "note"):
            object.__setattr__(
                self,
                field_name,
                optional_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(self, "tags", parse_tags(self.tags))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "transaction_id": self.transaction_id,
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "portfolio_id": self.portfolio_id,
            "trade_date": self.trade_date.isoformat(),
            "settlement_date": _format_optional_date(self.settlement_date),
            "created_at": _format_optional_datetime(self.created_at),
            "updated_at": _format_optional_datetime(self.updated_at),
            "transaction_type": self.transaction_type.value,
            "quantity": _format_optional_decimal(self.quantity),
            "price": _format_optional_decimal(self.price),
            "currency": self.currency,
            "exchange_rate": _format_optional_decimal(self.exchange_rate),
            "fee": _format_optional_decimal(self.fee),
            "tax": _format_optional_decimal(self.tax),
            "shipping": _format_optional_decimal(self.shipping),
            "insurance": _format_optional_decimal(self.insurance),
            "other_cost": _format_optional_decimal(self.other_cost),
            "account": self.account,
            "platform": self.platform,
            "broker": self.broker,
            "status": self.status.value,
            "note": self.note,
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class Event:
    """Shared immutable asset lifecycle event record."""

    event_id: str
    event_type: EventType | str
    event_date: date | str
    asset_id: str | None = None
    asset_type: str | None = None
    related_transaction_id: str | None = None
    status: str | None = None
    payload: dict[str, Any] | None = None
    note: str | None = None
    tags: list[str] | tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "event_id",
            require_text(self.event_id, "event_id"),
        )
        object.__setattr__(
            self,
            "event_type",
            parse_enum(EventType, self.event_type, "event_type"),
        )
        object.__setattr__(
            self,
            "event_date",
            self.event_date
            if isinstance(self.event_date, date)
            else parse_date(self.event_date, "event_date"),
        )
        for field_name in (
            "asset_id",
            "asset_type",
            "related_transaction_id",
            "status",
            "note",
        ):
            object.__setattr__(
                self,
                field_name,
                optional_text(getattr(self, field_name), field_name),
            )
        if self.payload is not None and not isinstance(self.payload, dict):
            raise TransactionError("payload must be a dictionary.")
        object.__setattr__(self, "tags", parse_tags(self.tags))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "related_transaction_id": self.related_transaction_id,
            "event_date": self.event_date.isoformat(),
            "status": self.status,
            "payload": self.payload,
            "note": self.note,
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class BaseTransaction:
    """Backward-compatible minimal transaction record."""

    transaction_id: str
    date: date
    asset_id: str
    transaction_type: TransactionType | str
    currency: str
    amount: Decimal
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "transaction_id",
            require_text(self.transaction_id, "transaction_id"),
        )
        object.__setattr__(
            self,
            "asset_id",
            require_text(self.asset_id, "asset_id"),
        )
        object.__setattr__(
            self,
            "transaction_type",
            parse_enum(
                TransactionType,
                self.transaction_type,
                "transaction_type",
            ),
        )
        object.__setattr__(self, "currency", require_currency(self.currency))
        amount = Decimal(str(self.amount))
        if not amount.is_finite():
            raise TransactionError(f"Invalid amount: {self.amount}")
        if self.transaction_type != TransactionType.ADJUSTMENT and amount <= 0:
            raise TransactionError(f"Invalid amount: {self.amount}")
        if self.transaction_type == TransactionType.ADJUSTMENT and amount == 0:
            raise TransactionError(f"Invalid amount: {self.amount}")
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


def _format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def _format_optional_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _format_decimal(value)


def _format_optional_date(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _format_optional_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
