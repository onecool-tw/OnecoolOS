"""Source agreement foundation for collectible valuations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from typing import Iterable

from onecool_os.valuation.enums import ValuationSource
from onecool_os.valuation.models import ValuationRecord
from onecool_os.valuation.validation import ValuationError
from onecool_os.valuation.validation import require_text


class AgreementLevel(StrEnum):
    """Deterministic source agreement levels."""

    STRONG = "STRONG"
    GOOD = "GOOD"
    FAIR = "FAIR"
    WEAK = "WEAK"
    CONFLICT = "CONFLICT"
    UNKNOWN = "UNKNOWN"


PRIMARY_MARKET_SOURCES = (ValuationSource.EBAY_SOLD,)
VALIDATION_SOURCES = (
    ValuationSource.CARD_LADDER,
    ValuationSource.MANUAL,
    ValuationSource.PWCC,
    ValuationSource.GOLDIN,
    ValuationSource.FANATICS,
)


@dataclass(frozen=True)
class SourceAgreementResult:
    """Deterministic agreement assessment across valuation sources."""

    agreement_id: str
    asset_id: str
    generated_at: datetime
    reference_datetime: datetime
    primary_market_source: str | None
    primary_market_price: Decimal | None
    validation_sources: dict[str, Decimal]
    participating_sources: tuple[str, ...]
    missing_sources: tuple[str, ...]
    agreement_score: int
    agreement_level: AgreementLevel | str
    agreement_spread: Decimal | None
    max_divergence: Decimal | None
    source_count: int
    warnings: tuple[str, ...]
    raw_valuation_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "agreement_id",
            require_text(self.agreement_id, "agreement_id"),
        )
        object.__setattr__(
            self,
            "asset_id",
            require_text(self.asset_id, "asset_id"),
        )
        if not isinstance(self.generated_at, datetime):
            raise ValuationError("generated_at must be a datetime.")
        if not isinstance(self.reference_datetime, datetime):
            raise ValuationError("reference_datetime must be a datetime.")
        object.__setattr__(
            self,
            "agreement_level",
            AgreementLevel(str(self.agreement_level).upper()),
        )
        if self.primary_market_price is not None:
            object.__setattr__(
                self,
                "primary_market_price",
                _non_negative_decimal(
                    self.primary_market_price,
                    "primary_market_price",
                ),
            )
        object.__setattr__(
            self,
            "validation_sources",
            {
                str(source): _non_negative_decimal(value, source)
                for source, value in self.validation_sources.items()
            },
        )
        for field_name in ("agreement_spread", "max_divergence"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    _non_negative_decimal(value, field_name),
                )
        if not isinstance(self.agreement_score, int) or not (
            0 <= self.agreement_score <= 100
        ):
            raise ValuationError("agreement_score must be between 0 and 100.")
        if not isinstance(self.source_count, int) or self.source_count < 0:
            raise ValuationError(
                "source_count must be a non-negative integer."
            )
        object.__setattr__(
            self,
            "participating_sources",
            tuple(str(source) for source in self.participating_sources),
        )
        object.__setattr__(
            self,
            "missing_sources",
            tuple(str(source) for source in self.missing_sources),
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(str(warning) for warning in self.warnings),
        )
        object.__setattr__(
            self,
            "raw_valuation_ids",
            tuple(str(item) for item in self.raw_valuation_ids),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "agreement_id": self.agreement_id,
            "asset_id": self.asset_id,
            "generated_at": self.generated_at.isoformat(),
            "reference_datetime": self.reference_datetime.isoformat(),
            "primary_market_source": self.primary_market_source,
            "primary_market_price": _format_decimal(
                self.primary_market_price,
            ),
            "validation_sources": {
                source: _format_decimal(value)
                for source, value in self.validation_sources.items()
            },
            "participating_sources": list(self.participating_sources),
            "missing_sources": list(self.missing_sources),
            "agreement_score": self.agreement_score,
            "agreement_level": self.agreement_level.value,
            "agreement_spread": _format_percent(self.agreement_spread),
            "max_divergence": _format_percent(self.max_divergence),
            "source_count": self.source_count,
            "warnings": list(self.warnings),
            "raw_valuation_ids": list(self.raw_valuation_ids),
        }


class SourceAgreementBuilder:
    """Build source agreement from ValuationRecord-compatible records."""

    primary_sources = PRIMARY_MARKET_SOURCES
    validation_sources = VALIDATION_SOURCES

    def build(
        self,
        valuation_records: Iterable[Any],
        *,
        reference_datetime: datetime,
        asset_id: str | None = None,
    ) -> SourceAgreementResult:
        """Build deterministic source agreement without mutating records."""

        if not isinstance(reference_datetime, datetime):
            raise ValuationError("reference_datetime must be a datetime.")
        records = tuple(_coerce_record(record) for record in valuation_records)
        resolved_asset_id = require_text(
            asset_id or (records[0].asset_id if records else "unknown"),
            "asset_id",
        )
        primary_record = _latest_source_record(records, self.primary_sources)
        validation_records_by_source = {
            source: _latest_source_record(records, (source,))
            for source in self.validation_sources
        }
        validation_prices = {
            source.value: _record_value(record)
            for source, record in validation_records_by_source.items()
            if record is not None and _record_value(record) is not None
        }
        primary_price = (
            _record_value(primary_record)
            if primary_record is not None
            else None
        )
        participating_sources = _participating_sources(
            primary_record,
            validation_prices,
        )
        missing_sources = tuple(
            source.value
            for source in self.validation_sources
            if source.value not in validation_prices
        )
        score, level, spread = _agreement(
            primary_price,
            tuple(validation_prices.values()),
        )
        warnings = _warnings(
            primary_price=primary_price,
            validation_count=len(validation_prices),
            source_count=len(participating_sources),
            level=level,
            spread=spread,
        )
        return SourceAgreementResult(
            agreement_id=f"source-agreement:{resolved_asset_id}",
            asset_id=resolved_asset_id,
            generated_at=reference_datetime,
            reference_datetime=reference_datetime,
            primary_market_source=(
                primary_record.source.value if primary_record else None
            ),
            primary_market_price=primary_price,
            validation_sources=validation_prices,
            participating_sources=participating_sources,
            missing_sources=missing_sources,
            agreement_score=score,
            agreement_level=level,
            agreement_spread=spread,
            max_divergence=spread,
            source_count=len(participating_sources),
            warnings=warnings,
            raw_valuation_ids=tuple(record.valuation_id for record in records),
        )


def _coerce_record(record: Any) -> ValuationRecord:
    if isinstance(record, ValuationRecord):
        return record
    nested = getattr(record, "valuation_record", None)
    if isinstance(nested, ValuationRecord):
        return nested
    if isinstance(record, dict):
        payload = record.get("valuation_record", record)
        if isinstance(payload, dict):
            return ValuationRecord(**payload)
    raise ValuationError("valuation_records must contain ValuationRecord data.")


def _latest_source_record(
    records: tuple[ValuationRecord, ...],
    sources: tuple[ValuationSource, ...],
) -> ValuationRecord | None:
    candidates = tuple(
        record
        for record in records
        if record.source in sources and _record_value(record) is not None
    )
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda record: (record.valuation_date, record.valuation_id),
    )[-1]


def _record_value(record: ValuationRecord | None) -> Decimal | None:
    if record is None:
        return None
    for field_name in (
        "market_value",
        "estimated_value",
        "low_value",
        "high_value",
    ):
        value = getattr(record, field_name)
        if value is not None:
            return value
    return None


def _participating_sources(
    primary_record: ValuationRecord | None,
    validation_prices: dict[str, Decimal],
) -> tuple[str, ...]:
    sources: list[str] = []
    if primary_record is not None:
        sources.append(primary_record.source.value)
    for source in (
        ValuationSource.CARD_LADDER.value,
        ValuationSource.MANUAL.value,
        ValuationSource.PWCC.value,
        ValuationSource.GOLDIN.value,
        ValuationSource.FANATICS.value,
    ):
        if source in validation_prices:
            sources.append(source)
    return tuple(sources)


def _agreement(
    primary_price: Decimal | None,
    validation_values: tuple[Decimal, ...],
) -> tuple[int, AgreementLevel, Decimal | None]:
    if primary_price is None or primary_price == Decimal("0"):
        return 0, AgreementLevel.UNKNOWN, None
    if not validation_values:
        return 0, AgreementLevel.UNKNOWN, None
    max_divergence = max(
        abs(value - primary_price) / primary_price
        for value in validation_values
    )
    score = max(0, round(100 - (max_divergence * Decimal("100"))))
    if max_divergence <= Decimal("0.05"):
        level = AgreementLevel.STRONG
    elif max_divergence <= Decimal("0.10"):
        level = AgreementLevel.GOOD
    elif max_divergence <= Decimal("0.20"):
        level = AgreementLevel.FAIR
    elif max_divergence <= Decimal("0.35"):
        level = AgreementLevel.WEAK
    else:
        level = AgreementLevel.CONFLICT
    return int(score), level, max_divergence


def _warnings(
    *,
    primary_price: Decimal | None,
    validation_count: int,
    source_count: int,
    level: AgreementLevel,
    spread: Decimal | None,
) -> tuple[str, ...]:
    warnings: list[str] = []
    if primary_price is None:
        warnings.append("Missing Primary Market Price")
    if validation_count == 0:
        warnings.append("Validation Sources Missing")
    if source_count < 2:
        warnings.append("Low Source Count")
    if level == AgreementLevel.WEAK:
        warnings.append("Source Agreement Weak")
    if level == AgreementLevel.CONFLICT:
        warnings.append("Source Conflict")
    if spread is not None and spread > Decimal("0.35"):
        warnings.append("High Divergence")
    return tuple(dict.fromkeys(warnings))


def _non_negative_decimal(value: Any, field_name: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except Exception as exc:
        raise ValuationError(f"{field_name} must be a Decimal.") from exc
    if not parsed.is_finite() or parsed < Decimal("0"):
        raise ValuationError(f"{field_name} must not be negative.")
    return parsed


def _format_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}"


def _format_percent(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{(value * Decimal('100')).quantize(Decimal('0.01'))}"
