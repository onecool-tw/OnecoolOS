"""Cash / FX asset models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from onecool_os.portfolio.models import Asset, PortfolioError


class CashError(PortfolioError):
    """Raised for cash model errors."""


@dataclass(frozen=True)
class CashAsset:
    """A cash account mapped to the shared Portfolio Asset model."""

    asset_id: str
    name: str
    currency: str
    account_type: str
    institution: str | None = None
    country: str | None = None
    asset_type: str = "CASH"

    def __post_init__(self) -> None:
        if self.asset_type != "CASH":
            raise CashError(f"Unsupported cash asset_type: {self.asset_type}")
        _validate_currency(self.currency)

    def to_asset(self) -> Asset:
        """Return the shared Portfolio Asset representation."""

        return Asset(
            asset_id=self.asset_id,
            symbol=self.currency,
            asset_type=self.asset_type,
            name=self.name,
            currency=self.currency,
        )


@dataclass(frozen=True)
class CashPosition:
    """A cash balance with optional base currency conversion."""

    asset: CashAsset
    amount: Decimal
    currency: str
    fx_rate_to_base: Decimal | None = None
    base_currency: str = "TWD"
    notes: str = ""

    def __post_init__(self) -> None:
        _validate_currency(self.currency)
        _validate_currency(self.base_currency)
        if self.amount < Decimal("0"):
            raise CashError(f"Invalid amount: {self.amount}")
        if self.fx_rate_to_base is not None and self.fx_rate_to_base <= Decimal("0"):
            raise CashError(f"Invalid fx_rate_to_base: {self.fx_rate_to_base}")

    def market_value(self) -> Decimal:
        """Return cash value in its native currency."""

        return self.amount

    def market_value_base(self) -> Decimal:
        """Return cash value converted to base currency."""

        if self.currency == self.base_currency:
            return self.amount
        if self.fx_rate_to_base is None:
            return Decimal("0")
        return self.amount * self.fx_rate_to_base

    def unrealized_pnl(self) -> Decimal:
        """Return placeholder PnL until valuation is implemented."""

        return Decimal("0")


def _validate_currency(value: str) -> None:
    if len(value) != 3 or not value.isalpha() or not value.isupper():
        raise CashError(f"Invalid currency: {value}")
