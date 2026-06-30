"""Built-in demo valuators."""

from __future__ import annotations

from decimal import Decimal

from onecool_os.assets.base import BaseAsset
from onecool_os.intelligence.valuation.models import (
    BaseValuator,
    ValuationResult,
    now_utc,
)


class DemoValuator(BaseValuator):
    """Mock valuator for framework verification."""

    provider_id = "demo"
    _supported_values = {
        "MUTUAL_FUND": Decimal("10000"),
        "SPORTS_CARD": Decimal("5000"),
        "REAL_ESTATE": Decimal("30000000"),
        "CASH": Decimal("100000"),
    }

    def supports(self, asset: BaseAsset) -> bool:
        """Return whether the demo valuator supports an asset."""

        return asset.asset_type in self._supported_values

    def valuate(self, asset: BaseAsset) -> ValuationResult:
        """Return a mocked valuation result."""

        estimated_value = self._supported_values[asset.asset_type]
        return ValuationResult(
            asset_id=asset.asset_id,
            asset_type=asset.asset_type,
            provider=self.provider_id,
            estimated_value=estimated_value,
            currency=asset.currency,
            valuation_time=now_utc(),
            confidence=0.5,
            notes="Mock valuation for framework demonstration only.",
        )
