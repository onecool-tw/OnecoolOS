"""Portfolio Engine foundation."""

from __future__ import annotations

from dataclasses import dataclass

from onecool_os.core.config import SystemConfig
from onecool_os.core.logging import LoggingSystem
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
    ) -> None:
        self.config = config
        self.registry = registry or PortfolioRegistry()
        self.logging_system = LoggingSystem(config)
        self.logger = self.logging_system.get_logger("system")
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


def create_portfolio_engine(config: SystemConfig) -> PortfolioEngine:
    """Create and initialize the Portfolio Engine."""

    return PortfolioEngine(config).initialize()
