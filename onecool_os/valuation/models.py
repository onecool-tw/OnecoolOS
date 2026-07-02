"""Universal valuation record models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from onecool_os.valuation.enums import ValuationConfidence
from onecool_os.valuation.enums import ValuationSource
from onecool_os.valuation.enums import source_priority_for_asset
from onecool_os.valuation.validation import ValuationError
from onecool_os.valuation.validation import optional_text
from onecool_os.valuation.validation import parse_date
from onecool_os.valuation.validation import parse_enum
from onecool_os.valuation.validation import parse_non_negative_decimal
from onecool_os.valuation.validation import parse_optional_date
from onecool_os.valuation.validation import parse_optional_positive_int
from onecool_os.valuation.validation import parse_tags
from onecool_os.valuation.validation import require_currency
from onecool_os.valuation.validation import require_text


@dataclass(frozen=True)
class ValuationRecord:
    """Immutable valuation history record for any asset class."""

    valuation_id: str
    asset_id: str
    asset_type: str
    source: ValuationSource | str
    currency: str
    valuation_date: date | str
    confidence: ValuationConfidence | str
    source_priority: int | str | None = None
    market_value: Decimal | str | int | float | None = None
    estimated_value: Decimal | str | int | float | None = None
    low_value: Decimal | str | int | float | None = None
    high_value: Decimal | str | int | float | None = None
    effective_date: date | str | None = None
    note: str | None = None
    url: str | None = None
    tags: list[str] | tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "valuation_id",
            require_text(self.valuation_id, "valuation_id"),
        )
        object.__setattr__(
            self,
            "asset_id",
            require_text(self.asset_id, "asset_id"),
        )
        object.__setattr__(
            self,
            "asset_type",
            require_text(self.asset_type, "asset_type").upper(),
        )
        object.__setattr__(
            self,
            "source",
            parse_enum(ValuationSource, self.source, "source"),
        )
        object.__setattr__(self, "currency", require_currency(self.currency))
        object.__setattr__(
            self,
            "valuation_date",
            self.valuation_date
            if isinstance(self.valuation_date, date)
            else parse_date(self.valuation_date, "valuation_date"),
        )
        object.__setattr__(
            self,
            "confidence",
            parse_enum(ValuationConfidence, self.confidence, "confidence"),
        )
        source_priority = parse_optional_positive_int(
            self.source_priority,
            "source_priority",
        )
        if source_priority is None:
            source_priority = source_priority_for_asset(
                self.asset_type,
                self.source,
            )
        object.__setattr__(self, "source_priority", source_priority)

        for field_name in (
            "market_value",
            "estimated_value",
            "low_value",
            "high_value",
        ):
            object.__setattr__(
                self,
                field_name,
                parse_non_negative_decimal(
                    getattr(self, field_name),
                    field_name,
                ),
            )
        if not any(
            getattr(self, field_name) is not None
            for field_name in (
                "market_value",
                "estimated_value",
                "low_value",
                "high_value",
            )
        ):
            raise ValuationError(
                "At least one valuation value field must be provided."
            )
        if (
            self.low_value is not None
            and self.high_value is not None
            and self.low_value > self.high_value
        ):
            raise ValuationError(
                "low_value cannot be greater than high_value."
            )

        object.__setattr__(
            self,
            "effective_date",
            parse_optional_date(self.effective_date, "effective_date"),
        )
        object.__setattr__(self, "note", optional_text(self.note, "note"))
        object.__setattr__(self, "url", optional_text(self.url, "url"))
        object.__setattr__(self, "tags", parse_tags(self.tags))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "valuation_id": self.valuation_id,
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "source": self.source.value,
            "source_priority": self.source_priority,
            "currency": self.currency,
            "market_value": _format_optional_decimal(self.market_value),
            "estimated_value": _format_optional_decimal(self.estimated_value),
            "low_value": _format_optional_decimal(self.low_value),
            "high_value": _format_optional_decimal(self.high_value),
            "valuation_date": self.valuation_date.isoformat(),
            "effective_date": _format_optional_date(self.effective_date),
            "confidence": self.confidence.value,
            "note": self.note,
            "url": self.url,
            "tags": list(self.tags),
        }


def _format_optional_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}"


def _format_optional_date(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
