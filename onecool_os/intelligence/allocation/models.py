"""Allocation domain models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class AllocationResult:
    """A normalized allocation calculation result."""

    asset_type: str
    asset_name: str
    market_value: Decimal
    allocation_percent: Decimal

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "asset_type": self.asset_type,
            "asset_name": self.asset_name,
            "market_value": _format_decimal(self.market_value),
            "allocation_percent": _format_decimal(
                self.allocation_percent,
            ),
        }


def _format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"
