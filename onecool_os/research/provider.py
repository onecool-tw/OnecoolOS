"""Provider interface for the Onecool Research Framework."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from onecool_os.research.enums import ResearchCapability
from onecool_os.research.enums import ResearchProviderType
from onecool_os.research.models import ResearchRequest
from onecool_os.research.models import ResearchResult


class ResearchProvider(ABC):
    """Abstract external research provider.

    Concrete providers must not communicate directly with RuntimeSession,
    Valuation, Dashboard, Decision Queue, or OFAI. Provider output must return
    through ResearchResult for normalization and validation.
    """

    @abstractmethod
    def provider_name(self) -> str:
        """Return the stable provider name."""

    @abstractmethod
    def provider_type(self) -> ResearchProviderType:
        """Return the provider type."""

    @abstractmethod
    def provider_version(self) -> str:
        """Return the provider adapter version."""

    @abstractmethod
    def capabilities(self) -> tuple[ResearchCapability, ...]:
        """Return provider capabilities."""

    @abstractmethod
    def validate_request(self, request: ResearchRequest) -> bool:
        """Return whether this provider supports the request."""

    @abstractmethod
    def research(self, request: ResearchRequest) -> ResearchResult:
        """Execute provider research and return normalized output."""
