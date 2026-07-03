"""Portfolio domain models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from onecool_os.portfolio.validation import PortfolioError
from onecool_os.portfolio.validation import optional_text
from onecool_os.portfolio.validation import parse_non_negative_decimal
from onecool_os.portfolio.validation import parse_optional_non_negative_decimal
from onecool_os.portfolio.validation import parse_optional_non_negative_int
from onecool_os.portfolio.validation import parse_tags
from onecool_os.portfolio.validation import require_currency
from onecool_os.portfolio.validation import require_text


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

        price = (
            self.current_price
            if self.current_price is not None
            else Decimal("0")
        )
        return self.quantity * price

    def total_cost(self) -> Decimal:
        """Return total cost basis."""

        return self.quantity * self.average_cost

    def unrealized_pnl(self) -> Decimal:
        """Return unrealized profit and loss."""

        return self.market_value() - self.total_cost()


@dataclass(frozen=True)
class Holding:
    """Portfolio aggregation holding reference."""

    asset_id: str
    asset_type: str
    quantity: Decimal
    average_cost: Decimal | None = None
    market_value: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "asset_id",
            require_text(self.asset_id, "asset_id"),
        )
        object.__setattr__(
            self,
            "asset_type",
            require_text(self.asset_type, "asset_type").upper(),
        )
        object.__setattr__(
            self,
            "quantity",
            parse_non_negative_decimal(self.quantity, "quantity"),
        )
        object.__setattr__(
            self,
            "average_cost",
            parse_optional_non_negative_decimal(
                self.average_cost,
                "average_cost",
            ),
        )
        object.__setattr__(
            self,
            "market_value",
            parse_optional_non_negative_decimal(
                self.market_value,
                "market_value",
            ),
        )

    def to_dict(self) -> dict[str, str | None]:
        """Return a JSON-safe representation."""

        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "quantity": _format_decimal(self.quantity),
            "average_cost": _format_optional_decimal(self.average_cost),
            "market_value": _format_optional_decimal(self.market_value),
        }


class Portfolio:
    """Portfolio aggregation model.

    Portfolio aggregates Assets, Ledger, and Valuation inputs. It does not own
    transaction history, valuation history, or asset identity.
    """

    def __init__(
        self,
        portfolio_id: str,
        name: str | None = None,
        portfolio_name: str | None = None,
        base_currency: str = "TWD",
        total_assets: int | None = None,
        total_market_value: Decimal | str | int | float | None = None,
        total_cost: Decimal | str | int | float | None = None,
        cash_balance: Decimal | str | int | float | None = None,
        note: str | None = None,
        tags: list[str] | tuple[str, ...] | None = None,
        holdings: list[Holding] | tuple[Holding, ...] | None = None,
    ) -> None:
        self.portfolio_id = require_text(portfolio_id, "portfolio_id")
        resolved_name = portfolio_name if portfolio_name is not None else name
        self.name = require_text(resolved_name, "portfolio_name")
        self.portfolio_name = self.name
        self.base_currency = require_currency(base_currency)
        self.total_assets = parse_optional_non_negative_int(
            total_assets,
            "total_assets",
        )
        self._total_market_value = parse_optional_non_negative_decimal(
            total_market_value,
            "total_market_value",
        )
        self._total_cost = parse_optional_non_negative_decimal(
            total_cost,
            "total_cost",
        )
        self.cash_balance = parse_optional_non_negative_decimal(
            cash_balance,
            "cash_balance",
        )
        self.note = optional_text(note, "note")
        self.tags = parse_tags(tags)
        self._holdings: dict[str, Holding] = {}
        self._positions: dict[str, Position] = {}
        for holding in holdings or ():
            self.add_holding(holding)

    def add_holding(self, holding: Holding) -> None:
        """Add or replace an aggregation holding by asset id."""

        self._holdings[holding.asset_id] = holding

    def list_holdings(self) -> tuple[Holding, ...]:
        """Return aggregation holdings in stable asset id order."""

        return tuple(
            self._holdings[asset_id]
            for asset_id in sorted(self._holdings)
        )

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

        if self._total_market_value is not None:
            return self._total_market_value
        if self._holdings:
            return sum(
                (
                    holding.market_value
                    for holding in self._holdings.values()
                    if holding.market_value is not None
                ),
                Decimal("0"),
            )
        return sum(
            (position.market_value() for position in self._positions.values()),
            Decimal("0"),
        )

    def total_cost(self) -> Decimal:
        """Return total cost basis."""

        if self._total_cost is not None:
            return self._total_cost
        if self._holdings:
            return sum(
                (
                    holding.quantity * holding.average_cost
                    for holding in self._holdings.values()
                    if holding.average_cost is not None
                ),
                Decimal("0"),
            )
        return sum(
            (position.total_cost() for position in self._positions.values()),
            Decimal("0"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe aggregation payload."""

        total_assets = self.total_assets
        if total_assets is None:
            total_assets = len(self._holdings) or len(self._positions)
        return {
            "portfolio_id": self.portfolio_id,
            "portfolio_name": self.portfolio_name,
            "base_currency": self.base_currency,
            "total_assets": total_assets,
            "total_market_value": _format_decimal(self.total_market_value()),
            "total_cost": _format_decimal(self.total_cost()),
            "holdings": [
                holding.to_dict() for holding in self.list_holdings()
            ],
            "cash_balance": _format_optional_decimal(self.cash_balance),
            "note": self.note,
            "tags": list(self.tags),
        }


def _format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def _format_optional_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _format_decimal(value)
