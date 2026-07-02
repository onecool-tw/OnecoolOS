"""Universal valuation enumerations."""

from __future__ import annotations

from enum import StrEnum


class ValuationSource(StrEnum):
    """Supported valuation data sources."""

    EBAY_SOLD = "EBAY_SOLD"
    CARD_LADDER = "CARD_LADDER"
    PWCC = "PWCC"
    GOLDIN = "GOLDIN"
    FANATICS = "FANATICS"
    PSA_ESTIMATE = "PSA_ESTIMATE"
    YAHOO = "YAHOO"
    POLYGON = "POLYGON"
    BROKER = "BROKER"
    FUND_NAV = "FUND_NAV"
    MORNINGSTAR = "MORNINGSTAR"
    REAL_ESTATE_TRANSACTION = "REAL_ESTATE_TRANSACTION"
    BANK_VALUATION = "BANK_VALUATION"
    MANUAL = "MANUAL"


class ValuationConfidence(StrEnum):
    """Supported valuation confidence levels."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


SOURCE_PRIORITY_BY_ASSET_TYPE: dict[str, tuple[ValuationSource, ...]] = {
    "SPORTS_CARD": (
        ValuationSource.EBAY_SOLD,
        ValuationSource.CARD_LADDER,
        ValuationSource.PWCC,
        ValuationSource.GOLDIN,
        ValuationSource.FANATICS,
        ValuationSource.PSA_ESTIMATE,
        ValuationSource.MANUAL,
    ),
    "SPORTS_CARDS": (
        ValuationSource.EBAY_SOLD,
        ValuationSource.CARD_LADDER,
        ValuationSource.PWCC,
        ValuationSource.GOLDIN,
        ValuationSource.FANATICS,
        ValuationSource.PSA_ESTIMATE,
        ValuationSource.MANUAL,
    ),
    "SECURITY": (
        ValuationSource.YAHOO,
        ValuationSource.POLYGON,
        ValuationSource.BROKER,
        ValuationSource.MANUAL,
    ),
    "SECURITIES": (
        ValuationSource.YAHOO,
        ValuationSource.POLYGON,
        ValuationSource.BROKER,
        ValuationSource.MANUAL,
    ),
    "STOCK": (
        ValuationSource.YAHOO,
        ValuationSource.POLYGON,
        ValuationSource.BROKER,
        ValuationSource.MANUAL,
    ),
    "ETF": (
        ValuationSource.YAHOO,
        ValuationSource.POLYGON,
        ValuationSource.BROKER,
        ValuationSource.MANUAL,
    ),
    "FUND": (
        ValuationSource.FUND_NAV,
        ValuationSource.MORNINGSTAR,
        ValuationSource.BROKER,
        ValuationSource.MANUAL,
    ),
    "MUTUAL_FUND": (
        ValuationSource.FUND_NAV,
        ValuationSource.MORNINGSTAR,
        ValuationSource.BROKER,
        ValuationSource.MANUAL,
    ),
    "REAL_ESTATE": (
        ValuationSource.REAL_ESTATE_TRANSACTION,
        ValuationSource.BANK_VALUATION,
        ValuationSource.MANUAL,
    ),
    "CASH": (
        ValuationSource.BROKER,
        ValuationSource.MANUAL,
    ),
}


def source_priority_for_asset(
    asset_type: str,
    source: ValuationSource | str,
) -> int | None:
    """Return the configured priority for an asset type and source."""

    normalized_asset_type = asset_type.strip().upper()
    normalized_source = (
        source
        if isinstance(source, ValuationSource)
        else ValuationSource(str(source).upper())
    )
    priority_list = SOURCE_PRIORITY_BY_ASSET_TYPE.get(normalized_asset_type)
    if priority_list is None:
        return None
    try:
        return priority_list.index(normalized_source) + 1
    except ValueError:
        return None
