"""Portfolio aggregation enumerations."""

from __future__ import annotations

from enum import StrEnum


class PortfolioInputLayer(StrEnum):
    """Layers consumed by the portfolio aggregation model."""

    ASSETS = "ASSETS"
    LEDGER = "LEDGER"
    VALUATION = "VALUATION"


class ValuationCoverageStatus(StrEnum):
    """NAV valuation coverage class for an asset."""

    VERIFIED = "VERIFIED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ESTIMATED = "ESTIMATED"
    MISSING = "MISSING"


class PortfolioNavStatus(StrEnum):
    """Portfolio NAV snapshot completeness status."""

    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
