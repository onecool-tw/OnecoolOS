"""Valuation domain models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from onecool_os.assets.base import BaseAsset
from onecool_os.core.exceptions import OnecoolOSError


class ValuationError(OnecoolOSError):
    """Raised for valuation errors."""


@dataclass(frozen=True)
class ValuationResult:
    """A normalized valuation result."""

    asset_id: str
    asset_type: str
    provider: str
    estimated_value: Decimal
    currency: str
    valuation_time: datetime
    confidence: float
    notes: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "provider": self.provider,
            "estimated_value": _format_decimal(self.estimated_value),
            "currency": self.currency,
            "valuation_time": self.valuation_time.isoformat(),
            "confidence": self.confidence,
            "notes": self.notes,
        }


class BaseValuator(ABC):
    """Abstract valuation provider interface."""

    provider_id: str

    @abstractmethod
    def supports(self, asset: BaseAsset) -> bool:
        """Return whether this valuator supports an asset."""

    @abstractmethod
    def valuate(self, asset: BaseAsset) -> ValuationResult:
        """Return a valuation result for an asset."""


def now_utc() -> datetime:
    """Return current UTC time for valuation timestamps."""

    return datetime.now(UTC)


def _format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"
