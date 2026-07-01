"""Securities asset models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from onecool_os.assets.base import BaseAsset, BasePosition
from onecool_os.portfolio.models import Asset, PortfolioError

SUPPORTED_SECURITY_TYPES = frozenset({"STOCK", "ETF", "OTHER"})
SUPPORTED_MARKETS = frozenset({"US", "TW", "OTHER"})
SUPPORTED_CURRENCIES = frozenset({"USD", "TWD"})


class SecurityError(PortfolioError):
    """Raised for securities model errors."""


@dataclass(frozen=True)
class SecurityAsset(BaseAsset):
    """A listed security mapped to the shared Portfolio Asset model."""

    asset_id: str
    symbol: str
    asset_type: str
    name: str
    currency: str
    market: str
    exchange: str | None = None
    country: str | None = None
    sector: str | None = None
    theme: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        asset_type = self.asset_type.upper()
        market = self.market.upper()
        currency = self.currency.upper()
        if asset_type not in SUPPORTED_SECURITY_TYPES:
            raise SecurityError(f"Unsupported security asset_type: {asset_type}")
        if market not in SUPPORTED_MARKETS:
            raise SecurityError(f"Unsupported security market: {market}")
        if currency not in SUPPORTED_CURRENCIES:
            raise SecurityError(f"Unsupported security currency: {currency}")
        if not self.symbol.strip():
            raise SecurityError("symbol must be a non-empty string.")
        if not self.name.strip():
            raise SecurityError("name must be a non-empty string.")
        object.__setattr__(self, "asset_type", asset_type)
        object.__setattr__(self, "market", market)
        object.__setattr__(self, "currency", currency)
        object.__setattr__(self, "symbol", self.symbol.strip().upper())

    def to_asset(self) -> Asset:
        """Return the shared Portfolio Asset representation."""

        return Asset(
            asset_id=self.asset_id,
            symbol=self.symbol,
            asset_type=self.asset_type,
            name=self.name,
            currency=self.currency,
        )


@dataclass(frozen=True)
class SecurityPosition(BasePosition):
    """A securities holding."""

    asset: SecurityAsset
    quantity: Decimal
    average_cost: Decimal
    purchase_date: str | None = None
    account: str | None = None
    asset_class: str | None = None
    status: str | None = None
    base_currency: str | None = None
    cost: Decimal | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if self.quantity <= Decimal("0"):
            raise SecurityError(f"Invalid quantity: {self.quantity}")
        if self.average_cost <= Decimal("0"):
            raise SecurityError(f"Invalid average_cost: {self.average_cost}")

    def total_cost(self) -> Decimal:
        """Return total cost basis."""

        return self.quantity * self.average_cost
