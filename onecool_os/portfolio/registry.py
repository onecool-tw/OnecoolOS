"""Portfolio registry."""

from __future__ import annotations

from onecool_os.core.exceptions import OnecoolOSError
from onecool_os.portfolio.models import Portfolio


class PortfolioRegistryError(OnecoolOSError):
    """Raised for portfolio registry errors."""


class PortfolioRegistry:
    """Creates and retrieves in-memory portfolios."""

    def __init__(self) -> None:
        self._portfolios: dict[str, Portfolio] = {}

    def create_portfolio(self, portfolio_id: str, name: str) -> Portfolio:
        """Create and register a portfolio."""

        if portfolio_id in self._portfolios:
            raise PortfolioRegistryError(
                f"Duplicate portfolio_id: {portfolio_id}"
            )
        portfolio = Portfolio(portfolio_id=portfolio_id, name=name)
        self._portfolios[portfolio_id] = portfolio
        return portfolio

    def get_portfolio(self, portfolio_id: str) -> Portfolio:
        """Return a portfolio by id."""

        try:
            return self._portfolios[portfolio_id]
        except KeyError as exc:
            raise PortfolioRegistryError(
                f"Unknown portfolio_id: {portfolio_id}"
            ) from exc

    def list_portfolios(self) -> tuple[Portfolio, ...]:
        """Return portfolios in stable id order."""

        return tuple(
            self._portfolios[portfolio_id]
            for portfolio_id in sorted(self._portfolios)
        )
