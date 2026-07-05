"""Collectible-specific deterministic intelligence engine."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from onecool_os.business_logic.calculators import BaseCalculator
from onecool_os.business_logic.context import BusinessLogicContext
from onecool_os.business_logic.evaluators import BaseEvaluator
from onecool_os.business_logic.results import BusinessLogicResult
from onecool_os.business_logic.results import SignalResult
from onecool_os.valuation.intelligence import AgreementLevel
from onecool_os.valuation.intelligence import ConfidenceLevel
from onecool_os.valuation.intelligence import FreshnessLevel
from onecool_os.valuation.intelligence import LiquidityLevel
from onecool_os.valuation.intelligence import MarketIntelligence


class MarketQuality(StrEnum):
    """Collectible market quality levels."""

    PREMIUM = "PREMIUM"
    STRONG = "STRONG"
    NORMAL = "NORMAL"
    WEAK = "WEAK"
    UNKNOWN = "UNKNOWN"


class ReviewStatus(StrEnum):
    """Collectible review readiness levels."""

    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class CollectibleIntelligenceAssessment:
    """Internal collectible intelligence assessment."""

    market_quality: MarketQuality
    valuation_quality: MarketQuality
    liquidity_quality: MarketQuality
    source_quality: MarketQuality
    review_status: ReviewStatus
    warnings: tuple[str, ...]


class CollectibleIntelligenceEngine(BaseCalculator, BaseEvaluator):
    """Produce collectible-specific signals from MarketIntelligence."""

    def __init__(self) -> None:
        super().__init__(
            engine_name="collectible_intelligence",
            engine_version="v1",
        )

    def supports(self, context: BusinessLogicContext) -> bool:
        """Return whether this engine can inspect the context."""

        return isinstance(context, BusinessLogicContext)

    def calculate(
        self,
        context: BusinessLogicContext,
    ) -> BusinessLogicResult:
        """Calculate deterministic collectible intelligence fields."""

        intelligence = _market_intelligence_from_context(context)
        assessment = _assess_market_intelligence(intelligence)
        payload = _payload_from_assessment(assessment, intelligence)
        return BusinessLogicResult(
            result_id=f"{context.context_id}-collectible-intelligence",
            engine_name=self.engine_name,
            engine_version=self.engine_version,
            metric_type="EXPOSURE",
            value=_result_value(intelligence),
            currency=context.base_currency,
            payload=payload,
            confidence=_result_confidence(assessment),
            generated_at=(
                intelligence.generated_at
                if intelligence is not None
                else None
            ),
            note=(
                "Deterministic collectible intelligence from "
                "MarketIntelligence."
            ),
            tags=["collectible", "business_logic"],
        )

    def evaluate(
        self,
        context: BusinessLogicContext,
    ) -> tuple[SignalResult, ...]:
        """Return review-readiness signals for collectibles."""

        intelligence = _market_intelligence_from_context(context)
        assessment = _assess_market_intelligence(intelligence)
        if assessment.review_status == ReviewStatus.READY_FOR_REVIEW:
            return ()
        severity = (
            "HIGH"
            if assessment.review_status == ReviewStatus.BLOCKED
            else "MEDIUM"
        )
        return (
            SignalResult(
                signal_id=(
                    f"{context.context_id}-collectible-"
                    f"{assessment.review_status.value.lower()}"
                ),
                engine_name=self.engine_name,
                engine_version=self.engine_version,
                signal_type="collectible_review_status",
                severity=severity,
                message=f"Collectible intelligence {assessment.review_status}",
                payload=_payload_from_assessment(assessment, intelligence),
                generated_at=(
                    intelligence.generated_at
                    if intelligence is not None
                    else None
                ),
                note="Deterministic collectible intelligence signal.",
                tags=["collectible", "business_logic"],
            ),
        )


def _market_intelligence_from_context(
    context: BusinessLogicContext,
) -> MarketIntelligence | None:
    for source in (
        context.valuation_data,
        context.analytics_data,
        context.metadata.get("market_intelligence")
        if context.metadata
        else None,
    ):
        intelligence = _coerce_market_intelligence(source)
        if intelligence is not None:
            return intelligence
    return None


def _coerce_market_intelligence(source: Any) -> MarketIntelligence | None:
    if isinstance(source, MarketIntelligence):
        return source
    if isinstance(source, dict):
        value = source.get("market_intelligence")
        if isinstance(value, MarketIntelligence):
            return value
    if isinstance(source, (list, tuple)):
        for item in source:
            if isinstance(item, MarketIntelligence):
                return item
    return None


def _assess_market_intelligence(
    intelligence: MarketIntelligence | None,
) -> CollectibleIntelligenceAssessment:
    if intelligence is None:
        return CollectibleIntelligenceAssessment(
            market_quality=MarketQuality.UNKNOWN,
            valuation_quality=MarketQuality.UNKNOWN,
            liquidity_quality=MarketQuality.UNKNOWN,
            source_quality=MarketQuality.UNKNOWN,
            review_status=ReviewStatus.BLOCKED,
            warnings=("Missing required valuation data",),
        )

    market_quality = _market_quality(intelligence)
    valuation_quality = _valuation_quality(intelligence)
    liquidity_quality = _liquidity_quality(intelligence)
    source_quality = _source_quality(intelligence)
    review_status = _review_status(intelligence)
    return CollectibleIntelligenceAssessment(
        market_quality=market_quality,
        valuation_quality=valuation_quality,
        liquidity_quality=liquidity_quality,
        source_quality=source_quality,
        review_status=review_status,
        warnings=tuple(intelligence.warnings),
    )


def _market_quality(intelligence: MarketIntelligence) -> MarketQuality:
    if _is_blocked(intelligence):
        return MarketQuality.UNKNOWN
    if (
        intelligence.confidence_level
        in (ConfidenceLevel.VERY_HIGH, ConfidenceLevel.HIGH)
        and intelligence.agreement_level
        in (AgreementLevel.STRONG, AgreementLevel.GOOD)
        and intelligence.freshness_level
        in (FreshnessLevel.LIVE, FreshnessLevel.RECENT)
        and intelligence.liquidity_level
        in (LiquidityLevel.VERY_HIGH, LiquidityLevel.HIGH)
    ):
        return MarketQuality.PREMIUM
    if (
        intelligence.confidence_level
        in (ConfidenceLevel.VERY_HIGH, ConfidenceLevel.HIGH)
        and intelligence.agreement_level
        in (AgreementLevel.STRONG, AgreementLevel.GOOD)
    ):
        return MarketQuality.STRONG
    if intelligence.confidence_level == ConfidenceLevel.MEDIUM:
        return MarketQuality.NORMAL
    return MarketQuality.WEAK


def _valuation_quality(intelligence: MarketIntelligence) -> MarketQuality:
    if intelligence.confidence_level == ConfidenceLevel.VERY_HIGH:
        return MarketQuality.PREMIUM
    if intelligence.confidence_level == ConfidenceLevel.HIGH:
        return MarketQuality.STRONG
    if intelligence.confidence_level == ConfidenceLevel.MEDIUM:
        return MarketQuality.NORMAL
    if intelligence.confidence_level == ConfidenceLevel.LOW:
        return MarketQuality.WEAK
    return MarketQuality.UNKNOWN


def _liquidity_quality(intelligence: MarketIntelligence) -> MarketQuality:
    if intelligence.liquidity_level == LiquidityLevel.VERY_HIGH:
        return MarketQuality.PREMIUM
    if intelligence.liquidity_level == LiquidityLevel.HIGH:
        return MarketQuality.STRONG
    if intelligence.liquidity_level == LiquidityLevel.MEDIUM:
        return MarketQuality.NORMAL
    if intelligence.liquidity_level == LiquidityLevel.LOW:
        return MarketQuality.WEAK
    return MarketQuality.UNKNOWN


def _source_quality(intelligence: MarketIntelligence) -> MarketQuality:
    if intelligence.agreement_level == AgreementLevel.STRONG:
        return MarketQuality.PREMIUM
    if intelligence.agreement_level == AgreementLevel.GOOD:
        return MarketQuality.STRONG
    if intelligence.agreement_level == AgreementLevel.FAIR:
        return MarketQuality.NORMAL
    if intelligence.agreement_level == AgreementLevel.WEAK:
        return MarketQuality.WEAK
    return MarketQuality.UNKNOWN


def _review_status(intelligence: MarketIntelligence) -> ReviewStatus:
    if _is_blocked(intelligence):
        return ReviewStatus.BLOCKED
    if (
        intelligence.confidence_level
        in (ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW)
        or intelligence.agreement_level
        in (AgreementLevel.FAIR, AgreementLevel.WEAK)
        or intelligence.freshness_level == FreshnessLevel.STALE
        or intelligence.liquidity_level == LiquidityLevel.LOW
    ):
        return ReviewStatus.NEEDS_REVIEW
    return ReviewStatus.READY_FOR_REVIEW


def _is_blocked(intelligence: MarketIntelligence) -> bool:
    return (
        intelligence.primary_market_price is None
        or intelligence.confidence_level == ConfidenceLevel.VERY_LOW
        or intelligence.agreement_level == AgreementLevel.CONFLICT
        or not intelligence.raw_valuation_ids
    )


def _payload_from_assessment(
    assessment: CollectibleIntelligenceAssessment,
    intelligence: MarketIntelligence | None,
) -> dict[str, Any]:
    payload = {
        "market_quality": assessment.market_quality.value,
        "valuation_quality": assessment.valuation_quality.value,
        "liquidity_quality": assessment.liquidity_quality.value,
        "source_quality": assessment.source_quality.value,
        "review_status": assessment.review_status.value,
        "warnings": list(assessment.warnings),
        "excluded_decisions": ["buy", "sell", "hold", "target_price"],
    }
    if intelligence is not None:
        payload["market_intelligence"] = {
            "intelligence_id": intelligence.intelligence_id,
            "asset_id": intelligence.asset_id,
            "confidence_score": intelligence.confidence_score,
            "confidence_level": intelligence.confidence_level.value,
            "agreement_level": intelligence.agreement_level.value,
            "freshness_level": intelligence.freshness_level.value,
            "liquidity_level": intelligence.liquidity_level.value,
            "primary_market_source": intelligence.primary_market_source,
            "raw_valuation_ids": list(intelligence.raw_valuation_ids),
        }
    return payload


def _result_value(intelligence: MarketIntelligence | None) -> Decimal | None:
    if intelligence is None:
        return None
    return Decimal(str(intelligence.confidence_score))


def _result_confidence(
    assessment: CollectibleIntelligenceAssessment,
) -> str:
    if assessment.market_quality in (
        MarketQuality.PREMIUM,
        MarketQuality.STRONG,
    ):
        return "HIGH"
    if assessment.market_quality == MarketQuality.NORMAL:
        return "MEDIUM"
    return "LOW"
