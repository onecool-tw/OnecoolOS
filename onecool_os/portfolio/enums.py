"""Portfolio aggregation enumerations."""

from __future__ import annotations

from enum import StrEnum


class PortfolioInputLayer(StrEnum):
    """Layers consumed by the portfolio aggregation model."""

    ASSETS = "ASSETS"
    LEDGER = "LEDGER"
    VALUATION = "VALUATION"
