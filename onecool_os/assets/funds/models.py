"""Funds asset models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from onecool_os.assets.base import BaseAsset, BasePosition
from onecool_os.portfolio.models import Asset, PortfolioError, Position


@dataclass(frozen=True)
class FundAsset(BaseAsset):
    """A mutual fund asset mapped to the shared Portfolio Asset model."""

    asset_id: str
    symbol: str
    name: str
    currency: str
    fund_house: str | None = None
    region: str | None = None
    theme: str | None = None
    asset_type: str = "MUTUAL_FUND"

    def __post_init__(self) -> None:
        if self.asset_type != "MUTUAL_FUND":
            raise PortfolioError(
                f"Unsupported fund asset_type: {self.asset_type}"
            )

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
class FundPosition(BasePosition):
    """A mutual fund holding."""

    asset: FundAsset
    quantity: Decimal
    average_cost: Decimal
    current_price: Decimal | None = None
    account: str | None = None
    asset_class: str | None = None
    status: str | None = None
    base_currency: str | None = None
    cost: Decimal | None = None
    notes: str = ""

    def market_value(self) -> Decimal:
        """Return current market value."""

        return self.to_position().market_value()

    def total_cost(self) -> Decimal:
        """Return total cost basis."""

        return self.to_position().total_cost()

    def unrealized_pnl(self) -> Decimal:
        """Return unrealized profit and loss."""

        return self.to_position().unrealized_pnl()

    def to_position(self) -> Position:
        """Return the shared Portfolio Position representation."""

        return Position(
            asset=self.asset.to_asset(),
            quantity=self.quantity,
            average_cost=self.average_cost,
            current_price=self.current_price,
        )
