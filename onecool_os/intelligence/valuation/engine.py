"""Valuation Engine foundation."""

from __future__ import annotations

from onecool_os.assets.base import BaseAsset
from onecool_os.intelligence.valuation.models import (
    ValuationError,
    ValuationResult,
)
from onecool_os.intelligence.valuation.registry import ValuationRegistry
from onecool_os.intelligence.valuation.valuators import DemoValuator


class ValuationEngine:
    """Coordinate valuation providers."""

    def __init__(self, registry: ValuationRegistry | None = None) -> None:
        self.registry = registry or ValuationRegistry()
        self.started = False

    def initialize(self) -> "ValuationEngine":
        """Initialize the engine and register built-in demo valuator."""

        if not self.registry.list():
            self.registry.register(DemoValuator())
        self.started = True
        return self

    def valuate(
        self,
        asset: BaseAsset,
        provider_id: str | None = None,
    ) -> ValuationResult:
        """Valuate an asset with a provider or the first supporting provider."""

        if provider_id:
            valuator = self.registry.get(provider_id)
            if not valuator.supports(asset):
                raise ValuationError(
                    f"Valuator {provider_id} does not support {asset.asset_type}"
                )
            return valuator.valuate(asset)

        for valuator in self.registry.list():
            if valuator.supports(asset):
                return valuator.valuate(asset)
        raise ValuationError(f"No valuator supports asset_type: {asset.asset_type}")

    def valuate_many(self, assets: list[BaseAsset]) -> tuple[ValuationResult, ...]:
        """Valuate multiple assets."""

        return tuple(self.valuate(asset) for asset in assets)
