"""Collectible connector enumerations."""

from __future__ import annotations

from enum import StrEnum


class CollectibleMarketSource(StrEnum):
    """Supported collectible market data sources."""

    EBAY_SOLD = "EBAY_SOLD"
    CARD_LADDER = "CARD_LADDER"
    PWCC = "PWCC"
    GOLDIN = "GOLDIN"
    FANATICS = "FANATICS"
    MANUAL = "MANUAL"


class CollectibleSourceRole(StrEnum):
    """Role a source plays in the valuation strategy."""

    PRIMARY_MARKET_PRICE = "PRIMARY_MARKET_PRICE"
    VALIDATION_SOURCE = "VALIDATION_SOURCE"
    MANUAL_FALLBACK = "MANUAL_FALLBACK"


SOURCE_ROLE_BY_SOURCE: dict[
    CollectibleMarketSource,
    CollectibleSourceRole,
] = {
    CollectibleMarketSource.EBAY_SOLD: (
        CollectibleSourceRole.PRIMARY_MARKET_PRICE
    ),
    CollectibleMarketSource.CARD_LADDER: (
        CollectibleSourceRole.VALIDATION_SOURCE
    ),
    CollectibleMarketSource.PWCC: CollectibleSourceRole.VALIDATION_SOURCE,
    CollectibleMarketSource.GOLDIN: CollectibleSourceRole.VALIDATION_SOURCE,
    CollectibleMarketSource.FANATICS: (
        CollectibleSourceRole.VALIDATION_SOURCE
    ),
    CollectibleMarketSource.MANUAL: CollectibleSourceRole.MANUAL_FALLBACK,
}


def source_role_for_source(
    source: CollectibleMarketSource | str,
) -> CollectibleSourceRole:
    """Return the valuation role for a collectible market source."""

    normalized_source = (
        source
        if isinstance(source, CollectibleMarketSource)
        else CollectibleMarketSource(str(source).upper())
    )
    return SOURCE_ROLE_BY_SOURCE[normalized_source]
