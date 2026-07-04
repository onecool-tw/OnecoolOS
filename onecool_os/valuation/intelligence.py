"""Reusable market intelligence models and builders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Iterable

from onecool_os.valuation.collectibles import CollectibleValuationMapping
from onecool_os.valuation.enums import ValuationSource
from onecool_os.valuation.validation import ValuationError
from onecool_os.valuation.validation import require_text


class ConfidenceLevel(StrEnum):
    """Market intelligence confidence levels."""

    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"


class AgreementLevel(StrEnum):
    """Source agreement levels."""

    STRONG = "STRONG"
    GOOD = "GOOD"
    FAIR = "FAIR"
    WEAK = "WEAK"
    CONFLICT = "CONFLICT"


class FreshnessLevel(StrEnum):
    """Market data freshness levels."""

    LIVE = "LIVE"
    RECENT = "RECENT"
    AGING = "AGING"
    STALE = "STALE"


class LiquidityLevel(StrEnum):
    """Comparable sale liquidity levels."""

    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class MarketIntelligence:
    """Reusable market data quality assessment."""

    intelligence_id: str
    asset_id: str
    generated_at: datetime
    reference_datetime: datetime
    primary_market_price: Decimal | None
    primary_market_source: str | None
    confidence_score: int
    confidence_level: ConfidenceLevel | str
    primary_market_score: int
    agreement_score_component: int
    freshness_score_component: int
    coverage_score_component: int
    liquidity_score_component: int
    agreement_score: int
    agreement_level: AgreementLevel | str
    coverage_score: int
    available_sources: tuple[str, ...]
    expected_sources: tuple[str, ...]
    latest_market_date: date | None
    freshness_days: int | None
    freshness_level: FreshnessLevel | str
    comparable_sales_count: int
    liquidity_level: LiquidityLevel | str
    warnings: tuple[str, ...]
    raw_valuation_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "intelligence_id",
            require_text(self.intelligence_id, "intelligence_id"),
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
            "confidence_level",
            ConfidenceLevel(str(self.confidence_level).upper()),
        )
        object.__setattr__(
            self,
            "agreement_level",
            AgreementLevel(str(self.agreement_level).upper()),
        )
        object.__setattr__(
            self,
            "freshness_level",
            FreshnessLevel(str(self.freshness_level).upper()),
        )
        object.__setattr__(
            self,
            "liquidity_level",
            LiquidityLevel(str(self.liquidity_level).upper()),
        )
        for field_name in (
            "confidence_score",
            "primary_market_score",
            "agreement_score_component",
            "freshness_score_component",
            "coverage_score_component",
            "liquidity_score_component",
            "agreement_score",
            "coverage_score",
            "comparable_sales_count",
        ):
            _require_int_range(getattr(self, field_name), field_name)
        if self.primary_market_price is not None and (
            not isinstance(self.primary_market_price, Decimal)
            or self.primary_market_price < Decimal("0")
        ):
            raise ValuationError(
                "primary_market_price must be a non-negative Decimal."
            )
        if self.latest_market_date is not None and not isinstance(
            self.latest_market_date,
            date,
        ):
            raise ValuationError("latest_market_date must be a date.")
        if self.freshness_days is not None and self.freshness_days < 0:
            raise ValuationError("freshness_days must not be negative.")
        object.__setattr__(
            self,
            "available_sources",
            tuple(self.available_sources),
        )
        object.__setattr__(
            self,
            "expected_sources",
            tuple(self.expected_sources),
        )
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(
            self,
            "raw_valuation_ids",
            tuple(self.raw_valuation_ids),
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation."""

        return {
            "intelligence_id": self.intelligence_id,
            "asset_id": self.asset_id,
            "generated_at": self.generated_at.isoformat(),
            "reference_datetime": self.reference_datetime.isoformat(),
            "primary_market_price": (
                f"{self.primary_market_price.quantize(Decimal('0.01'))}"
                if self.primary_market_price is not None
                else None
            ),
            "primary_market_source": self.primary_market_source,
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level.value,
            "primary_market_score": self.primary_market_score,
            "agreement_score_component": self.agreement_score_component,
            "freshness_score_component": self.freshness_score_component,
            "coverage_score_component": self.coverage_score_component,
            "liquidity_score_component": self.liquidity_score_component,
            "agreement_score": self.agreement_score,
            "agreement_level": self.agreement_level.value,
            "coverage_score": self.coverage_score,
            "available_sources": list(self.available_sources),
            "expected_sources": list(self.expected_sources),
            "latest_market_date": (
                self.latest_market_date.isoformat()
                if self.latest_market_date is not None
                else None
            ),
            "freshness_days": self.freshness_days,
            "freshness_level": self.freshness_level.value,
            "comparable_sales_count": self.comparable_sales_count,
            "liquidity_level": self.liquidity_level.value,
            "warnings": list(self.warnings),
            "raw_valuation_ids": list(self.raw_valuation_ids),
        }


class CollectibleMarketIntelligenceBuilder:
    """Build market intelligence from collectible valuation mappings."""

    expected_sources = (
        ValuationSource.EBAY_SOLD.value,
        ValuationSource.CARD_LADDER.value,
        ValuationSource.PWCC.value,
        ValuationSource.GOLDIN.value,
        ValuationSource.FANATICS.value,
    )

    def build(
        self,
        valuation_mappings: Iterable[CollectibleValuationMapping],
        *,
        reference_datetime: datetime,
        asset_id: str | None = None,
    ) -> MarketIntelligence:
        """Build deterministic intelligence without mutating inputs."""

        if not isinstance(reference_datetime, datetime):
            raise ValuationError("reference_datetime must be a datetime.")
        mappings = tuple(valuation_mappings)
        if not mappings:
            resolved_asset_id = require_text(asset_id or "unknown", "asset_id")
            return self._empty_intelligence(
                resolved_asset_id,
                reference_datetime,
            )

        records = tuple(mapping.valuation_record for mapping in mappings)
        resolved_asset_id = asset_id or records[0].asset_id
        primary_mapping = self._latest_primary_mapping(mappings)
        primary_price = (
            primary_mapping.valuation_record.market_value
            if primary_mapping is not None
            else None
        )
        primary_source = (
            primary_mapping.valuation_record.source.value
            if primary_mapping is not None
            else None
        )
        validation_values = tuple(
            mapping.valuation_record.market_value
            for mapping in mappings
            if mapping.metadata.get("validation_source") is True
            and mapping.valuation_record.market_value is not None
        )
        agreement_score, agreement_level = self._agreement(
            primary_price,
            validation_values,
        )
        latest_market_date = max(record.valuation_date for record in records)
        freshness_days = max(
            0,
            (reference_datetime.date() - latest_market_date).days,
        )
        freshness_level, freshness_component = self._freshness(freshness_days)
        available_sources = self._available_sources(records)
        coverage_score = round(
            len(set(available_sources) & set(self.expected_sources))
            / len(self.expected_sources)
            * 100
        )
        coverage_component = round(coverage_score * 10 / 100)
        comparable_sales_count = sum(
            1 for record in records if record.market_value is not None
        )
        liquidity_level, liquidity_component = self._liquidity(
            comparable_sales_count,
        )
        primary_component = 30 if primary_price is not None else 0
        agreement_component = round(agreement_score * 30 / 100)
        confidence_score = sum(
            (
                primary_component,
                agreement_component,
                freshness_component,
                coverage_component,
                liquidity_component,
            )
        )
        warnings = self._warnings(
            primary_price=primary_price,
            validation_count=len(validation_values),
            agreement_level=agreement_level,
            coverage_score=coverage_score,
            liquidity_level=liquidity_level,
            freshness_level=freshness_level,
            confidence_score=confidence_score,
        )
        return MarketIntelligence(
            intelligence_id=f"market-intelligence:{resolved_asset_id}",
            asset_id=resolved_asset_id,
            generated_at=reference_datetime,
            reference_datetime=reference_datetime,
            primary_market_price=primary_price,
            primary_market_source=primary_source,
            confidence_score=confidence_score,
            confidence_level=self._confidence_level(confidence_score),
            primary_market_score=primary_component,
            agreement_score_component=agreement_component,
            freshness_score_component=freshness_component,
            coverage_score_component=coverage_component,
            liquidity_score_component=liquidity_component,
            agreement_score=agreement_score,
            agreement_level=agreement_level,
            coverage_score=coverage_score,
            available_sources=available_sources,
            expected_sources=self.expected_sources,
            latest_market_date=latest_market_date,
            freshness_days=freshness_days,
            freshness_level=freshness_level,
            comparable_sales_count=comparable_sales_count,
            liquidity_level=liquidity_level,
            warnings=warnings,
            raw_valuation_ids=tuple(record.valuation_id for record in records),
        )

    def _empty_intelligence(
        self,
        asset_id: str,
        reference_datetime: datetime,
    ) -> MarketIntelligence:
        warnings = (
            "Missing Primary Market Price",
            "Validation Sources Missing",
            "Low Liquidity",
            "Low Confidence",
        )
        return MarketIntelligence(
            intelligence_id=f"market-intelligence:{asset_id}",
            asset_id=asset_id,
            generated_at=reference_datetime,
            reference_datetime=reference_datetime,
            primary_market_price=None,
            primary_market_source=None,
            confidence_score=0,
            confidence_level=ConfidenceLevel.VERY_LOW,
            primary_market_score=0,
            agreement_score_component=0,
            freshness_score_component=0,
            coverage_score_component=0,
            liquidity_score_component=0,
            agreement_score=0,
            agreement_level=AgreementLevel.WEAK,
            coverage_score=0,
            available_sources=(),
            expected_sources=self.expected_sources,
            latest_market_date=None,
            freshness_days=None,
            freshness_level=FreshnessLevel.STALE,
            comparable_sales_count=0,
            liquidity_level=LiquidityLevel.UNKNOWN,
            warnings=warnings,
            raw_valuation_ids=(),
        )

    def _latest_primary_mapping(
        self,
        mappings: tuple[CollectibleValuationMapping, ...],
    ) -> CollectibleValuationMapping | None:
        primary_mappings = tuple(
            mapping
            for mapping in mappings
            if mapping.metadata.get("primary_market_price") is True
        )
        if not primary_mappings:
            return None
        return sorted(
            primary_mappings,
            key=lambda mapping: (
                mapping.valuation_record.valuation_date,
                mapping.valuation_record.valuation_id,
            ),
        )[-1]

    def _available_sources(self, records) -> tuple[str, ...]:
        source_values = {record.source.value for record in records}
        ordered = [
            source
            for source in self.expected_sources
            if source in source_values
        ]
        extras = sorted(source_values - set(self.expected_sources))
        return tuple(ordered + extras)

    def _agreement(
        self,
        primary_price: Decimal | None,
        validation_values: tuple[Decimal, ...],
    ) -> tuple[int, AgreementLevel]:
        if primary_price is None or primary_price == Decimal("0"):
            return 0, AgreementLevel.WEAK
        if not validation_values:
            return 0, AgreementLevel.WEAK
        average_divergence = sum(
            abs(value - primary_price) / primary_price
            for value in validation_values
        ) / len(validation_values)
        if average_divergence <= Decimal("0.10"):
            return 100, AgreementLevel.STRONG
        if average_divergence <= Decimal("0.20"):
            return 80, AgreementLevel.GOOD
        if average_divergence <= Decimal("0.35"):
            return 60, AgreementLevel.FAIR
        if average_divergence <= Decimal("0.50"):
            return 35, AgreementLevel.WEAK
        return 10, AgreementLevel.CONFLICT

    def _freshness(self, freshness_days: int) -> tuple[FreshnessLevel, int]:
        if freshness_days <= 1:
            return FreshnessLevel.LIVE, 20
        if freshness_days <= 30:
            return FreshnessLevel.RECENT, 16
        if freshness_days <= 90:
            return FreshnessLevel.AGING, 8
        return FreshnessLevel.STALE, 0

    def _liquidity(self, count: int) -> tuple[LiquidityLevel, int]:
        if count >= 10:
            return LiquidityLevel.VERY_HIGH, 10
        if count >= 5:
            return LiquidityLevel.HIGH, 8
        if count >= 3:
            return LiquidityLevel.MEDIUM, 6
        if count >= 1:
            return LiquidityLevel.LOW, 3
        return LiquidityLevel.UNKNOWN, 0

    def _confidence_level(self, score: int) -> ConfidenceLevel:
        if score >= 90:
            return ConfidenceLevel.VERY_HIGH
        if score >= 75:
            return ConfidenceLevel.HIGH
        if score >= 55:
            return ConfidenceLevel.MEDIUM
        if score >= 35:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW

    def _warnings(
        self,
        *,
        primary_price: Decimal | None,
        validation_count: int,
        agreement_level: AgreementLevel,
        coverage_score: int,
        liquidity_level: LiquidityLevel,
        freshness_level: FreshnessLevel,
        confidence_score: int,
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        if primary_price is None:
            warnings.append("Missing Primary Market Price")
        if validation_count == 0:
            warnings.append("Validation Sources Missing")
        if agreement_level == AgreementLevel.WEAK:
            warnings.append("Source Agreement Weak")
        if agreement_level == AgreementLevel.CONFLICT:
            warnings.append("Source Conflict")
        if coverage_score < 60:
            warnings.append("Validation Sources Missing")
        if liquidity_level in (LiquidityLevel.LOW, LiquidityLevel.UNKNOWN):
            warnings.append("Low Liquidity")
        if freshness_level == FreshnessLevel.STALE:
            warnings.append("Stale Market Data")
        if confidence_score < 55:
            warnings.append("Low Confidence")
        return tuple(dict.fromkeys(warnings))


def _require_int_range(value: object, field_name: str) -> None:
    if not isinstance(value, int):
        raise ValuationError(f"{field_name} must be an integer.")
    if field_name == "comparable_sales_count":
        if value < 0:
            raise ValuationError(f"{field_name} must not be negative.")
        return
    if value < 0 or value > 100:
        raise ValuationError(f"{field_name} must be between 0 and 100.")
