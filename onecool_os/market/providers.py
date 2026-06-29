"""Market provider interfaces and built-in providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from logging import Logger
from typing import Any

from onecool_os.core.exceptions import OnecoolOSError


class MarketProviderError(OnecoolOSError):
    """Raised when a market provider cannot fulfill a request."""


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


class YahooFinanceProvider(MarketProvider):
    """Yahoo Finance market provider backed by yfinance."""

    provider_id = "yahoo"
    name = "Yahoo Finance"
    supported_symbols = {"SPY"}

    def __init__(self, logger: Logger | None = None) -> None:
        self.connected = False
        self.logger = logger
        self._yfinance: Any | None = None

    def connect(self) -> None:
        """Connect the provider by loading yfinance lazily."""

        try:
            self._yfinance = __import__("yfinance")
            self.connected = True
            self._log_info("Initialized Yahoo Finance provider.")
        except Exception as exc:  # noqa: BLE001 - provider boundary.
            self.connected = False
            self._log_error("Yahoo Finance provider initialization failed.")
            raise MarketProviderError(str(exc)) from exc

    def health_check(self) -> dict[str, Any]:
        """Return Yahoo provider health."""

        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "connected": self.connected,
            "status": "ok" if self.connected else "disconnected",
        }

    def fetch(self, symbol: str) -> dict[str, Any]:
        """Fetch normalized market data from Yahoo Finance."""

        normalized_symbol = symbol.upper()
        if not normalized_symbol:
            message = "Yahoo Finance symbol is required."
            self._log_error(message)
            raise MarketProviderError(message)
        if normalized_symbol not in self.supported_symbols:
            message = f"Unsupported Yahoo Finance symbol: {normalized_symbol}"
            self._log_error(message)
            raise MarketProviderError(message)
        if not self.connected:
            self.connect()

        try:
            ticker = self._yfinance.Ticker(normalized_symbol)
            raw = _extract_fast_info(ticker)
            if not raw:
                raise MarketProviderError("Yahoo Finance returned empty data.")
            last_price = _extract_last_price(raw)
            currency = str(raw.get("currency") or "USD")
            if last_price is None:
                raise MarketProviderError("Yahoo Finance returned no price.")
            payload = {
                "symbol": normalized_symbol,
                "provider": self.provider_id,
                "last_price": float(last_price),
                "currency": currency,
                "timestamp": datetime.now(UTC).isoformat(),
                "raw": raw,
            }
            self._log_info(
                "Fetched Yahoo Finance data for %s.",
                normalized_symbol,
            )
            return payload
        except Exception as exc:  # noqa: BLE001 - provider boundary.
            self._log_error(
                "Yahoo Finance fetch failed for %s.",
                normalized_symbol,
            )
            if isinstance(exc, MarketProviderError):
                raise
            raise MarketProviderError(str(exc)) from exc

    def disconnect(self) -> None:
        """Disconnect the Yahoo Finance provider."""

        self.connected = False
        self._yfinance = None

    def _log_info(self, message: str, *args: Any) -> None:
        if self.logger is not None:
            self.logger.info(message, *args)

    def _log_error(self, message: str, *args: Any) -> None:
        if self.logger is not None:
            self.logger.error(message, *args)


def _extract_fast_info(ticker: Any) -> dict[str, Any]:
    fast_info = getattr(ticker, "fast_info", {})
    if callable(fast_info):
        fast_info = fast_info()
    return dict(fast_info or {})


def _extract_last_price(raw: dict[str, Any]) -> float | None:
    for key in ("last_price", "lastPrice", "regularMarketPrice"):
        value = raw.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError) as exc:
                raise MarketProviderError("Yahoo Finance price is invalid.") from exc
    return None
