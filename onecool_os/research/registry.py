"""Research provider registry."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from onecool_os.research.enums import ResearchCapability
from onecool_os.research.provider import ResearchProvider
from onecool_os.research.validation import ResearchError


@dataclass(frozen=True)
class ResearchProviderRegistry:
    """In-memory registry for research providers."""

    _providers: Mapping[str, ResearchProvider] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "_registry", dict(self._providers or {}))

    def register_provider(self, provider: ResearchProvider) -> None:
        """Register a provider by stable normalized name."""

        name = _normalize_provider_name(provider.provider_name())
        if name in self._registry:
            raise ResearchError(f"Research provider already registered: {name}")
        self._registry[name] = provider

    def get_provider(self, name: str) -> ResearchProvider:
        """Return a provider by normalized name."""

        normalized_name = _normalize_provider_name(name)
        try:
            return self._registry[normalized_name]
        except KeyError as exc:
            raise ResearchError(f"Unknown research provider: {normalized_name}") from exc

    def list_providers(self) -> tuple[str, ...]:
        """Return registered provider names in deterministic order."""

        return tuple(sorted(self._registry))

    def list_by_capability(
        self,
        capability: ResearchCapability | str,
    ) -> tuple[ResearchProvider, ...]:
        """Return providers that advertise a capability."""

        wanted = ResearchCapability(str(capability).upper())
        return tuple(
            self._registry[name]
            for name in sorted(self._registry)
            if wanted in self._registry[name].capabilities()
        )


def _normalize_provider_name(name: str) -> str:
    normalized = str(name).strip().lower()
    if not normalized:
        raise ResearchError("Research provider name is required.")
    return normalized
