"""Provider interfaces for runtime valuation sources."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from onecool_os.valuation.models import ValuationRecord


class ValuationProvider(ABC):
    """Abstract runtime valuation provider.

    Providers are responsible for finding provider-native observations and
    normalizing them into existing ``ValuationRecord`` objects. They must not
    choose final valuation, mutate source data, or call network resources unless
    a future concrete implementation explicitly owns that authorized behavior.
    """

    @abstractmethod
    def source_name(self) -> str:
        """Return the stable provider source name."""

    @abstractmethod
    def provider_metadata(self) -> Mapping[str, Any]:
        """Return non-secret metadata describing provider capabilities."""

    @abstractmethod
    def search(
        self,
        query: Mapping[str, Any] | None = None,
    ) -> Sequence[Any]:
        """Return provider-native candidate records for the query."""

    @abstractmethod
    def normalize(self, raw_record: Any) -> ValuationRecord:
        """Normalize one provider-native record into a ValuationRecord."""

    @abstractmethod
    def validate(self, valuation_record: ValuationRecord) -> bool:
        """Validate one normalized valuation record."""


@dataclass(frozen=True)
class ValuationProviderRegistry:
    """In-memory registry for runtime valuation providers."""

    _providers: Mapping[str, ValuationProvider] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "_registry", dict(self._providers or {}))

    def register_provider(self, provider: ValuationProvider) -> None:
        """Register a provider by its stable source name."""

        name = _provider_name(provider)
        if name in self._registry:
            raise ValueError(f"Valuation provider already registered: {name}")
        self._registry[name] = provider

    def get_provider(self, name: str) -> ValuationProvider:
        """Return a provider by name."""

        normalized_name = _normalize_provider_name(name)
        try:
            return self._registry[normalized_name]
        except KeyError as exc:
            raise KeyError(
                f"Unknown valuation provider: {normalized_name}"
            ) from exc

    def list_providers(self) -> tuple[str, ...]:
        """Return registered provider names in deterministic order."""

        return tuple(sorted(self._registry))


def valuation_records_from_provider(
    provider: ValuationProvider,
    query: Mapping[str, Any] | None = None,
) -> tuple[ValuationRecord, ...]:
    """Load and validate runtime valuation records from a provider."""

    records: list[ValuationRecord] = []
    for raw_record in provider.search(query):
        valuation_record = provider.normalize(raw_record)
        if not isinstance(valuation_record, ValuationRecord):
            raise TypeError(
                "Valuation provider normalize() must return ValuationRecord."
            )
        if not provider.validate(valuation_record):
            raise ValueError(
                "Valuation provider returned an invalid valuation record."
            )
        records.append(valuation_record)
    return tuple(records)


def _provider_name(provider: ValuationProvider) -> str:
    return _normalize_provider_name(provider.source_name())


def _normalize_provider_name(name: str) -> str:
    normalized_name = str(name).strip().lower()
    if not normalized_name:
        raise ValueError("Valuation provider name is required.")
    return normalized_name
