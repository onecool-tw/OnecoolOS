"""Normalization helpers for collectible market connectors."""

from __future__ import annotations

from typing import Any

from onecool_os.connectors.collectibles.enums import CollectibleMarketSource
from onecool_os.connectors.collectibles.models import (
    CollectibleConnectorError,
)
from onecool_os.connectors.collectibles.models import CollectibleMarketRecord


DEFAULT_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "external_id": (
        "external_id",
        "item_id",
        "card_id",
        "lot_id",
        "listing_id",
        "sale_id",
        "id",
    ),
    "title": ("title", "item", "name"),
    "player": ("player", "subject"),
    "year": ("year",),
    "brand": ("brand", "set", "manufacturer"),
    "card_number": ("card_number", "card_no", "card number"),
    "grade_company": ("grade_company", "grade issuer", "grader"),
    "grade": ("grade",),
    "sale_price": (
        "sale_price",
        "price",
        "sold_price",
        "latest_value",
        "value",
    ),
    "currency": ("currency",),
    "sale_date": (
        "sale_date",
        "sold_at",
        "valuation_date",
        "date",
        "auction_date",
    ),
    "url": ("url", "link"),
}


def normalize_collectible_market_record(
    source: CollectibleMarketSource | str,
    raw_record: dict[str, Any],
    *,
    record_prefix: str | None = None,
    field_aliases: dict[str, tuple[str, ...]] | None = None,
) -> CollectibleMarketRecord:
    """Normalize a local market record without choosing final valuation."""

    if not isinstance(raw_record, dict):
        raise CollectibleConnectorError("raw_record must be a dictionary.")

    normalized_source = (
        source
        if isinstance(source, CollectibleMarketSource)
        else CollectibleMarketSource(str(source).upper())
    )
    aliases = field_aliases or DEFAULT_FIELD_ALIASES
    external_id = _first_value(raw_record, aliases["external_id"])
    if external_id is None:
        raise CollectibleConnectorError("external_id is required.")

    prefix = record_prefix or normalized_source.value.lower()
    record_id = f"{prefix}:{external_id}"
    asset_hint = {
        key: value
        for key, value in {
            "player": _first_value(raw_record, aliases["player"]),
            "year": _first_value(raw_record, aliases["year"]),
            "brand": _first_value(raw_record, aliases["brand"]),
            "card_number": _first_value(raw_record, aliases["card_number"]),
            "grade_company": _first_value(
                raw_record,
                aliases["grade_company"],
            ),
            "grade": _first_value(raw_record, aliases["grade"]),
        }.items()
        if value is not None
    }

    return CollectibleMarketRecord(
        record_id=record_id,
        source=normalized_source,
        external_id=str(external_id),
        asset_hint=asset_hint,
        title=_first_value(raw_record, aliases["title"]),
        player=_first_value(raw_record, aliases["player"]),
        year=_first_value(raw_record, aliases["year"]),
        brand=_first_value(raw_record, aliases["brand"]),
        card_number=_first_value(raw_record, aliases["card_number"]),
        grade_company=_first_value(raw_record, aliases["grade_company"]),
        grade=_first_value(raw_record, aliases["grade"]),
        sale_price=_first_value(raw_record, aliases["sale_price"]),
        currency=_first_value(raw_record, aliases["currency"]),
        sale_date=_first_value(raw_record, aliases["sale_date"]),
        url=_first_value(raw_record, aliases["url"]),
        raw_payload=raw_record,
    )


def _first_value(
    raw_record: dict[str, Any],
    aliases: tuple[str, ...],
) -> Any | None:
    normalized_keys = {_normalize_key(key): key for key in raw_record}
    for alias in aliases:
        raw_key = normalized_keys.get(_normalize_key(alias))
        if raw_key is not None:
            value = raw_record[raw_key]
            if value is not None and value != "":
                return value
    return None


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace("_", " ")
