"""Portfolio Engine foundation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from onecool_os.core.config import SystemConfig
from onecool_os.core.logging import LoggingSystem
from onecool_os.portfolio.models import Asset, Portfolio, Position
from onecool_os.portfolio.registry import PortfolioRegistry


@dataclass(frozen=True)
class PortfolioEngineStatus:
    """Portfolio Engine status for CLI output."""

    engine_status: str
    portfolio_count: int
    position_count: int

    def to_dict(self) -> dict[str, int | str]:
        """Return JSON-safe status."""

        return {
            "engine_status": self.engine_status,
            "portfolio_count": self.portfolio_count,
            "position_count": self.position_count,
        }


class PortfolioEngine:
    """Coordinates in-memory portfolios."""

    def __init__(
        self,
        config: SystemConfig,
        registry: PortfolioRegistry | None = None,
        file_logging: bool = True,
    ) -> None:
        self.config = config
        self.registry = registry or PortfolioRegistry()
        self.logging_system = LoggingSystem(config)
        if file_logging:
            self.logger = self.logging_system.get_logger("system")
        else:
            self.logger = self.logging_system.get_console_logger("system")
        self.started = False

    def initialize(self) -> "PortfolioEngine":
        """Initialize the Portfolio Engine."""

        self.started = True
        self.logger.info("Portfolio Engine initialized.")
        return self

    def status(self) -> PortfolioEngineStatus:
        """Return Portfolio Engine status."""

        portfolios = self.registry.list_portfolios()
        position_count = sum(
            len(portfolio.list_positions()) for portfolio in portfolios
        )
        return PortfolioEngineStatus(
            engine_status="ready" if self.started else "stopped",
            portfolio_count=len(portfolios),
            position_count=position_count,
        )

    def demo(self) -> dict[str, Any]:
        """Return a hardcoded in-memory demo portfolio."""

        portfolio = build_demo_portfolio()
        self.logger.info("Generated portfolio CLI demo.")
        return portfolio_to_demo_dict(portfolio)


def create_portfolio_engine(config: SystemConfig) -> PortfolioEngine:
    """Create and initialize the Portfolio Engine."""

    return PortfolioEngine(config).initialize()


def create_portfolio_demo(config: SystemConfig) -> dict[str, Any]:
    """Create a demo portfolio payload without file or database writes."""

    engine = PortfolioEngine(config, file_logging=False)
    return engine.demo()


def build_demo_portfolio() -> Portfolio:
    """Build a hardcoded sample portfolio for CLI demonstration."""

    portfolio = Portfolio(portfolio_id="demo", name="Demo Portfolio")
    samples = (
        ("SPY", "SPY", "SPDR S&P 500 ETF Trust", "USD", "10", "420", "455"),
        ("QQQ", "QQQ", "Invesco QQQ Trust", "USD", "8", "350", "390"),
        ("GLD", "GLD", "SPDR Gold Shares", "USD", "5", "180", "195"),
    )
    for asset_id, asset_type, name, currency, quantity, cost, price in samples:
        portfolio.add_position(
            Position(
                asset=Asset(
                    asset_id=asset_id,
                    asset_type=asset_type,
                    name=name,
                    currency=currency,
                ),
                quantity=Decimal(quantity),
                average_cost=Decimal(cost),
                current_price=Decimal(price),
            )
        )
    return portfolio


def portfolio_to_demo_dict(portfolio: Portfolio) -> dict[str, Any]:
    """Return a JSON-safe demo portfolio payload."""

    positions = [
        position_to_demo_dict(position)
        for position in portfolio.list_positions()
    ]
    total_cost = portfolio.total_cost()
    total_market_value = portfolio.total_market_value()
    return {
        "portfolio_name": portfolio.name,
        "positions": positions,
        "total_cost": _format_decimal(total_cost),
        "total_market_value": _format_decimal(total_market_value),
        "total_unrealized_pnl": _format_decimal(
            total_market_value - total_cost
        ),
    }


def position_to_demo_dict(position: Position) -> dict[str, str]:
    """Return a JSON-safe demo position payload."""

    return {
        "asset_id": position.asset.asset_id,
        "asset_type": position.asset.asset_type,
        "name": position.asset.name,
        "currency": position.asset.currency,
        "quantity": _format_decimal(position.quantity),
        "average_cost": _format_decimal(position.average_cost),
        "current_price": _format_decimal(position.current_price),
        "market_value": _format_decimal(position.market_value()),
        "unrealized_pnl": _format_decimal(position.unrealized_pnl()),
    }


def _format_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}"
