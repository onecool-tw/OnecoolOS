"""Transaction and ledger enumerations."""

from __future__ import annotations

from enum import StrEnum


class TransactionType(StrEnum):
    """Supported shared transaction types."""

    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    SPLIT = "SPLIT"
    MERGE = "MERGE"
    FEE = "FEE"
    TAX = "TAX"
    ADJUSTMENT = "ADJUSTMENT"


class TransactionStatus(StrEnum):
    """Supported transaction processing statuses."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class EventType(StrEnum):
    """Supported lifecycle event types."""

    PURCHASED = "PURCHASED"
    SOLD = "SOLD"
    LISTED = "LISTED"
    RESERVED = "RESERVED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    SUBMITTED_GRADING = "SUBMITTED_GRADING"
    RECEIVED_GRADING = "RECEIVED_GRADING"
    DIVIDEND_PAID = "DIVIDEND_PAID"
    SPLIT = "SPLIT"
    MERGE = "MERGE"
    LOAN_APPROVED = "LOAN_APPROVED"
    REFINANCED = "REFINANCED"
    RENOVATED = "RENOVATED"
    VALUATION_UPDATED = "VALUATION_UPDATED"
    ADJUSTMENT = "ADJUSTMENT"
