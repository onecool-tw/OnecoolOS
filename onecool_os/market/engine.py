"""Market Engine foundation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from onecool_os.core.config import SystemConfig
from onecool_os.core.logging import LoggingSystem
from onecool_os.market.providers import MockProvider
from onecool_os.market.registry import ProviderRegistry


@dataclass(frozen=True)
class MarketEngineStatus:
    """Market Engine status for CLI output."""

    engine_status: str
    registered_providers: tuple[str, ...]
    provider_health: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe status."""

        return {
            "engine_status": self.engine_status,
            "registered_providers": list(self.registered_providers),
            "provider_health": self.provider_health,
        }


class MarketEngine:
    """Coordinates market providers without external data integrations."""

    def __init__(
        self,
        config: SystemConfig,
        registry: ProviderRegistry | None = None,
    ) -> None:
        self.config = config
        self.registry = registry or ProviderRegistry()
        self.logging_system = LoggingSystem(config)
        self.logger = self.logging_system.get_logger("market")
        self.started = False

    def initialize(self) -> "MarketEngine":
        """Register built-in providers and connect them."""

        if not self.started:
            if not self.registry.list_providers():
                self.registry.register_provider(MockProvider())
            for provider in self.registry.list_providers():
                provider.connect()
                self.logger.info(
                    "Connected market provider %s",
                    provider.provider_id,
                )
            self.started = True
        return self

    def shutdown(self) -> None:
        """Disconnect all market providers."""

        for provider in self.registry.list_providers():
            provider.disconnect()
            self.logger.info(
                "Disconnected market provider %s",
                provider.provider_id,
            )
        self.started = False

    def fetch(self, provider_id: str, symbol: str) -> dict[str, Any]:
        """Fetch market data through a registered provider."""

        provider = self.registry.get_provider(provider_id)
        if not self.started:
            provider.connect()
        data = provider.fetch(symbol)
        self.logger.info(
            "Fetched mock market data for %s from %s",
            symbol,
            provider_id,
        )
        return data

    def status(self) -> MarketEngineStatus:
        """Return Market Engine status."""

        providers = self.registry.list_providers()
        provider_health = {
            provider.provider_id: provider.health_check()
            for provider in providers
        }
        return MarketEngineStatus(
            engine_status="ready" if self.started else "stopped",
            registered_providers=tuple(
                provider.provider_id for provider in providers
            ),
            provider_health=provider_health,
        )


def create_market_engine(config: SystemConfig) -> MarketEngine:
    """Create and initialize the Market Engine."""

    return MarketEngine(config).initialize()
