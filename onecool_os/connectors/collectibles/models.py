"""Shared collectible connector models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from onecool_os.connectors.collectibles.enums import CollectibleMarketSource


class CollectibleConnectorError(ValueError):
    """Raised when collectible connector data is invalid."""


@dataclass(frozen=True)
class CollectibleMarketRecord:
    """Normalized market observation for a collectible asset."""

    record_id: str
    source: CollectibleMarketSource | str
    external_id: str | None = None
    asset_hint: dict[str, Any] | None = None
    title: str | None = None
    player: str | None = None
    year: str | int | None = None
    brand: str | None = None
    card_number: str | None = None
    grade_company: str | None = None
    grade: str | int | float | None = None
    sale_price: Decimal | str | int | float | None = None
    currency: str | None = None
    sale_date: date | str | None = None
    url: str | None = None
    raw_payload: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "record_id",
            _require_text(self.record_id, "record_id"),
        )
        object.__setattr__(
            self,
            "source",
            _parse_source(self.source),
        )
        object.__setattr__(
            self,
            "external_id",
            _optional_text(self.external_id, "external_id"),
        )
        if self.asset_hint is not None and not isinstance(
            self.asset_hint,
            dict,
        ):
            raise CollectibleConnectorError(
                "asset_hint must be a dictionary."
            )
        object.__setattr__(
            self,
            "asset_hint",
            dict(self.asset_hint) if self.asset_hint is not None else None,
        )
        for field_name in (
            "title",
            "player",
            "brand",
            "card_number",
            "grade_company",
            "url",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "year",
            _optional_text(self.year, "year"),
        )
        object.__setattr__(
            self,
            "grade",
            _optional_text(self.grade, "grade"),
        )
        object.__setattr__(
            self,
            "sale_price",
            _optional_non_negative_decimal(self.sale_price, "sale_price"),
        )
        object.__setattr__(
            self,
            "currency",
            _optional_currency(self.currency),
        )
        object.__setattr__(
            self,
            "sale_date",
            _optional_date(self.sale_date, "sale_date"),
        )
        if self.raw_payload is not None and not isinstance(
            self.raw_payload,
            dict,
        ):
            raise CollectibleConnectorError(
                "raw_payload must be a dictionary."
            )
        object.__setattr__(
            self,
            "raw_payload",
            dict(self.raw_payload) if self.raw_payload is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "record_id": self.record_id,
            "source": self.source.value,
            "external_id": self.external_id,
            "asset_hint": self.asset_hint,
            "title": self.title,
            "player": self.player,
            "year": self.year,
            "brand": self.brand,
            "card_number": self.card_number,
            "grade_company": self.grade_company,
            "grade": self.grade,
            "sale_price": _format_decimal(self.sale_price),
            "currency": self.currency,
            "sale_date": (
                self.sale_date.isoformat()
                if isinstance(self.sale_date, date)
                else None
            ),
            "url": self.url,
            "raw_payload": self.raw_payload,
        }


def _parse_source(
    source: CollectibleMarketSource | str,
) -> CollectibleMarketSource:
    try:
        if isinstance(source, CollectibleMarketSource):
            return source
        return CollectibleMarketSource(str(source).upper())
    except ValueError as exc:
        raise CollectibleConnectorError("Invalid source.") from exc


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CollectibleConnectorError(
            f"{field_name} must be a non-empty string."
        )
    return value.strip()


def _optional_text(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if not isinstance(value, str):
        raise CollectibleConnectorError(f"{field_name} must be text.")
    normalized = value.strip()
    return normalized or None


def _optional_currency(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise CollectibleConnectorError("currency must be text.")
    return value.strip().upper()


def _optional_non_negative_decimal(
    value: Decimal | str | int | float | None,
    field_name: str,
) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        parsed = Decimal(str(value))
    except Exception as exc:
        raise CollectibleConnectorError(
            f"{field_name} must be a number."
        ) from exc
    if parsed < 0:
        raise CollectibleConnectorError(f"{field_name} must not be negative.")
    return parsed


def _optional_date(value: date | str | None, field_name: str) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise CollectibleConnectorError(
            f"{field_name} must be an ISO date string."
        )
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise CollectibleConnectorError(
            f"{field_name} must be an ISO date string."
        ) from exc


def _format_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}"
