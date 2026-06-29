"""Market provider interfaces and built-in providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any


class MarketProvider(ABC):
    """Abstract market data provider interface."""

    provider_id: str
    name: str

    @abstractmethod
    def connect(self) -> None:
        """Connect the provider."""

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Return provider health information."""

    @abstractmethod
    def fetch(self, symbol: str) -> dict[str, Any]:
        """Fetch market data for a symbol."""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect the provider."""


class MockProvider(MarketProvider):
    """Built-in mock provider for Market Engine foundation tests."""

    provider_id = "mock"
    name = "Mock Provider"

    def __init__(self) -> None:
        self.connected = False

    def connect(self) -> None:
        """Connect the mock provider."""

        self.connected = True

    def health_check(self) -> dict[str, Any]:
        """Return mock provider health."""

        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "connected": self.connected,
            "status": "ok" if self.connected else "disconnected",
        }

    def fetch(self, symbol: str) -> dict[str, Any]:
        """Return simple mock market data."""

        if not self.connected:
            self.connect()
        return {
            "provider_id": self.provider_id,
            "symbol": symbol.upper(),
            "price": 100.0,
            "currency": "USD",
            "as_of": datetime.now(UTC).isoformat(),
            "source": "mock",
        }

    def disconnect(self) -> None:
        """Disconnect the mock provider."""

        self.connected = False
