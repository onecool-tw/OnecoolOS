"""Portfolio domain models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from onecool_os.core.exceptions import OnecoolOSError


class PortfolioError(OnecoolOSError):
    """Raised for portfolio model errors."""


class AssetType(StrEnum):
    """Supported normalized asset categories."""

    ETF = "ETF"
    MUTUAL_FUND = "MUTUAL_FUND"
    STOCK = "STOCK"
    SPORTS_CARD = "SPORTS_CARD"
    REAL_ESTATE = "REAL_ESTATE"
    GOLD = "GOLD"
    CASH = "CASH"
    CRYPTO = "CRYPTO"
    OTHER = "OTHER"


@dataclass(frozen=True)
class Asset:
    """A generic asset shared by future asset classes."""

    asset_id: str
    symbol: str
    asset_type: str
    name: str
    currency: str

    def __post_init__(self) -> None:
        """Validate and normalize asset type."""

        normalized_type = self.asset_type.upper()
        if normalized_type not in AssetType:
            raise PortfolioError(f"Unsupported asset_type: {self.asset_type}")
        object.__setattr__(self, "asset_type", normalized_type)
        object.__setattr__(self, "symbol", self.symbol.upper())


@dataclass
class Position:
    """A holding in an asset."""

    asset: Asset
    quantity: Decimal
    average_cost: Decimal
    current_price: Decimal | None = None

    def market_value(self) -> Decimal:
        """Return current market value."""

        price = self.current_price if self.current_price is not None else Decimal("0")
        return self.quantity * price

    def total_cost(self) -> Decimal:
        """Return total cost basis."""

        return self.quantity * self.average_cost

    def unrealized_pnl(self) -> Decimal:
        """Return unrealized profit and loss."""

        return self.market_value() - self.total_cost()


class Portfolio:
    """A lightweight in-memory portfolio."""

    def __init__(self, portfolio_id: str, name: str) -> None:
        self.portfolio_id = portfolio_id
        self.name = name
        self._positions: dict[str, Position] = {}

    def add_position(self, position: Position) -> None:
        """Add or replace a position by asset id."""

        self._positions[position.asset.asset_id] = position

    def remove_position(self, asset_id: str) -> Position:
        """Remove and return a position by asset id."""

        try:
            return self._positions.pop(asset_id)
        except KeyError as exc:
            raise PortfolioError(f"Unknown asset_id: {asset_id}") from exc

    def list_positions(self) -> tuple[Position, ...]:
        """Return positions in stable asset id order."""

        return tuple(
            self._positions[asset_id]
            for asset_id in sorted(self._positions)
        )

    def total_market_value(self) -> Decimal:
        """Return total current market value."""

        return sum(
            (position.market_value() for position in self._positions.values()),
            Decimal("0"),
        )

    def total_cost(self) -> Decimal:
        """Return total cost basis."""

        return sum(
            (position.total_cost() for position in self._positions.values()),
            Decimal("0"),
        )
