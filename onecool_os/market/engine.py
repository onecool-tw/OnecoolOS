"""Market Engine foundation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from onecool_os.core.config import SystemConfig
from onecool_os.core.logging import LoggingSystem
from onecool_os.market.providers import (
    MarketProviderError,
    MockProvider,
    YahooFinanceProvider,
)
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
                self._register_builtin_providers()
            for provider in self.registry.list_providers():
                try:
                    provider.connect()
                    self.logger.info(
                        "Connected market provider %s",
                        provider.provider_id,
                    )
                except MarketProviderError:
                    self.logger.warning(
                        "Market provider %s is unavailable.",
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
        try:
            data = provider.fetch(symbol)
            self.logger.info(
                "Fetched market data for %s from %s",
                symbol,
                provider_id,
            )
            return data
        except Exception:
            self.logger.error(
                "Market data fetch failed for %s from %s",
                symbol,
                provider_id,
            )
            raise

    def validate_fetch(self, provider_id: str, symbol: str) -> dict[str, Any]:
        """Validate a market fetch and return a safe result payload."""

        normalized_symbol = symbol.upper()
        self.logger.info(
            "Starting market validation for %s from %s",
            normalized_symbol,
            provider_id,
        )
        try:
            data = self.fetch(provider_id, normalized_symbol)
            payload = _validation_payload(
                symbol=str(data.get("symbol", normalized_symbol)),
                provider=str(data.get("provider", provider_id)),
                status="success",
                last_price=data.get("last_price"),
                currency=data.get("currency"),
                timestamp=data.get("timestamp"),
                error_message=None,
                raw=data.get("raw", {}),
            )
            self.logger.info(
                "Market validation succeeded for %s from %s",
                normalized_symbol,
                provider_id,
            )
            return payload
        except Exception as exc:  # noqa: BLE001 - validation must be safe.
            self.logger.error(
                "Market validation failed for %s from %s",
                normalized_symbol,
                provider_id,
            )
            return _validation_payload(
                symbol=normalized_symbol,
                provider=provider_id,
                status="failure",
                last_price=None,
                currency=None,
                timestamp=datetime.now(UTC).isoformat(),
                error_message=str(exc),
                raw={},
            )

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

    def _register_builtin_providers(self) -> None:
        providers_config = self.config.market.providers
        mock_enabled = _provider_enabled(providers_config, "mock", True)
        yahoo_enabled = _provider_enabled(providers_config, "yahoo", False)
        if mock_enabled:
            self.registry.register_provider(MockProvider())
        if yahoo_enabled:
            self.registry.register_provider(YahooFinanceProvider(self.logger))


def create_market_engine(config: SystemConfig) -> MarketEngine:
    """Create and initialize the Market Engine."""

    return MarketEngine(config).initialize()


def _provider_enabled(
    providers_config: dict[str, Any],
    provider_id: str,
    default: bool,
) -> bool:
    provider_config = providers_config.get(provider_id, {})
    if not isinstance(provider_config, dict):
        return default
    return bool(provider_config.get("enabled", default))


def _validation_payload(
    symbol: str,
    provider: str,
    status: str,
    last_price: Any,
    currency: Any,
    timestamp: Any,
    error_message: str | None,
    raw: dict[str, Any],
) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "provider": provider,
        "last_price": last_price,
        "currency": currency,
        "timestamp": timestamp,
        "status": status,
        "error_message": error_message,
        "raw": raw,
    }
