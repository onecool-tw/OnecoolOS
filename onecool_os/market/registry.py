"""Provider registry for the Market Engine."""

from __future__ import annotations

from onecool_os.core.exceptions import OnecoolOSError
from onecool_os.market.providers import MarketProvider


class ProviderRegistryError(OnecoolOSError):
    """Raised for provider registry errors."""


class ProviderRegistry:
    """Registers and retrieves market providers."""

    def __init__(self) -> None:
        self._providers: dict[str, MarketProvider] = {}

    def register_provider(self, provider: MarketProvider) -> None:
        """Register a market provider."""

        if provider.provider_id in self._providers:
            raise ProviderRegistryError(
                f"Duplicate provider_id: {provider.provider_id}"
            )
        self._providers[provider.provider_id] = provider

    def unregister_provider(self, provider_id: str) -> None:
        """Unregister a market provider."""

        if provider_id not in self._providers:
            raise ProviderRegistryError(f"Unknown provider_id: {provider_id}")
        provider = self._providers.pop(provider_id)
        provider.disconnect()

    def list_providers(self) -> tuple[MarketProvider, ...]:
        """Return registered providers in stable order."""

        return tuple(
            self._providers[provider_id]
            for provider_id in sorted(self._providers)
        )

    def get_provider(self, provider_id: str) -> MarketProvider:
        """Return a provider by id."""

        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise ProviderRegistryError(
                f"Unknown provider_id: {provider_id}"
            ) from exc
