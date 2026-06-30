"""Registry for valuation providers."""

from __future__ import annotations

from onecool_os.intelligence.valuation.models import BaseValuator, ValuationError


class ValuationRegistry:
    """Register and retrieve valuation providers."""

    def __init__(self) -> None:
        self._valuators: dict[str, BaseValuator] = {}

    def register(self, valuator: BaseValuator) -> None:
        """Register a valuator."""

        if valuator.provider_id in self._valuators:
            raise ValuationError(
                f"Valuator already registered: {valuator.provider_id}"
            )
        self._valuators[valuator.provider_id] = valuator

    def unregister(self, provider_id: str) -> BaseValuator:
        """Unregister and return a valuator."""

        try:
            return self._valuators.pop(provider_id)
        except KeyError as exc:
            raise ValuationError(f"Unknown valuator: {provider_id}") from exc

    def get(self, provider_id: str) -> BaseValuator:
        """Return a valuator by provider id."""

        try:
            return self._valuators[provider_id]
        except KeyError as exc:
            raise ValuationError(f"Unknown valuator: {provider_id}") from exc

    def list(self) -> tuple[BaseValuator, ...]:
        """Return valuators in stable provider id order."""

        return tuple(
            self._valuators[provider_id]
            for provider_id in sorted(self._valuators)
        )
