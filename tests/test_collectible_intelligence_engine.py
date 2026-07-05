from copy import deepcopy
from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal

from onecool_os.business_logic import BusinessLogicContext
from onecool_os.business_logic import BusinessLogicResult
from onecool_os.business_logic import CollectibleIntelligenceEngine
from onecool_os.business_logic import MarketQuality
from onecool_os.business_logic import ReviewStatus
from onecool_os.business_logic import SignalResult
from onecool_os.business_logic.enums import MetricType
from onecool_os.valuation import AgreementLevel
from onecool_os.valuation import ConfidenceLevel as MarketConfidenceLevel
from onecool_os.valuation import FreshnessLevel
from onecool_os.valuation import LiquidityLevel
from onecool_os.valuation import MarketIntelligence


REFERENCE = datetime(2026, 7, 5, tzinfo=timezone.utc)


def test_premium_market_quality() -> None:
    result = CollectibleIntelligenceEngine().calculate(
        context_with_intelligence(
            market_intelligence(
                confidence_level=MarketConfidenceLevel.VERY_HIGH,
                agreement_level=AgreementLevel.STRONG,
                freshness_level=FreshnessLevel.LIVE,
                liquidity_level=LiquidityLevel.HIGH,
            )
        )
    )

    assert result.payload["market_quality"] == MarketQuality.PREMIUM.value
    assert result.payload["valuation_quality"] == MarketQuality.PREMIUM.value


def test_weak_market_quality() -> None:
    result = CollectibleIntelligenceEngine().calculate(
        context_with_intelligence(
            market_intelligence(
                confidence_score=40,
                confidence_level=MarketConfidenceLevel.LOW,
                agreement_level=AgreementLevel.WEAK,
                freshness_level=FreshnessLevel.AGING,
                liquidity_level=LiquidityLevel.LOW,
                warnings=("Source Agreement Weak", "Low Liquidity"),
            )
        )
    )

    assert result.payload["market_quality"] == MarketQuality.WEAK.value
    assert result.payload["review_status"] == ReviewStatus.NEEDS_REVIEW.value


def test_unknown_market_quality() -> None:
    result = CollectibleIntelligenceEngine().calculate(
        BusinessLogicContext(context_id="ctx-empty")
    )

    assert result.payload["market_quality"] == MarketQuality.UNKNOWN.value
    assert result.payload["review_status"] == ReviewStatus.BLOCKED.value


def test_ready_for_review() -> None:
    result = CollectibleIntelligenceEngine().calculate(
        context_with_intelligence(market_intelligence())
    )

    assert result.payload["review_status"] == (
        ReviewStatus.READY_FOR_REVIEW.value
    )


def test_needs_review() -> None:
    result = CollectibleIntelligenceEngine().calculate(
        context_with_intelligence(
            market_intelligence(
                confidence_score=65,
                confidence_level=MarketConfidenceLevel.MEDIUM,
                agreement_level=AgreementLevel.FAIR,
            )
        )
    )

    assert result.payload["review_status"] == ReviewStatus.NEEDS_REVIEW.value


def test_blocked() -> None:
    result = CollectibleIntelligenceEngine().calculate(
        context_with_intelligence(
            market_intelligence(
                confidence_score=10,
                confidence_level=MarketConfidenceLevel.VERY_LOW,
                agreement_score=10,
                agreement_level=AgreementLevel.CONFLICT,
                warnings=("Source Conflict",),
            )
        )
    )

    assert result.payload["review_status"] == ReviewStatus.BLOCKED.value
    assert result.payload["source_quality"] == MarketQuality.UNKNOWN.value


def test_warnings_preserved() -> None:
    result = CollectibleIntelligenceEngine().calculate(
        context_with_intelligence(
            market_intelligence(warnings=("Low Liquidity", "Low Confidence"))
        )
    )

    assert result.payload["warnings"] == ["Low Liquidity", "Low Confidence"]


def test_no_mutation() -> None:
    intelligence = market_intelligence(warnings=("Low Liquidity",))
    before = deepcopy(intelligence.to_dict())

    CollectibleIntelligenceEngine().calculate(
        context_with_intelligence(intelligence)
    )
    CollectibleIntelligenceEngine().evaluate(
        context_with_intelligence(intelligence)
    )

    assert intelligence.to_dict() == before


def test_business_logic_result_output() -> None:
    result = CollectibleIntelligenceEngine().calculate(
        context_with_intelligence(market_intelligence())
    )

    assert isinstance(result, BusinessLogicResult)
    assert result.engine_name == "collectible_intelligence"
    assert result.metric_type == MetricType.EXPOSURE
    assert result.value == Decimal("88")
    assert "buy" in result.payload["excluded_decisions"]
    assert "target_price" in result.payload["excluded_decisions"]


def test_signal_result_output_if_applicable() -> None:
    signals = CollectibleIntelligenceEngine().evaluate(
        context_with_intelligence(
            market_intelligence(
                confidence_score=42,
                confidence_level=MarketConfidenceLevel.LOW,
                agreement_level=AgreementLevel.WEAK,
            )
        )
    )

    assert len(signals) == 1
    assert isinstance(signals[0], SignalResult)
    assert signals[0].signal_type == "collectible_review_status"
    assert signals[0].severity.value == "MEDIUM"


def test_no_signal_when_ready_for_review() -> None:
    signals = CollectibleIntelligenceEngine().evaluate(
        context_with_intelligence(market_intelligence())
    )

    assert signals == ()


def test_supports_context() -> None:
    assert CollectibleIntelligenceEngine().supports(
        BusinessLogicContext(context_id="ctx")
    )


def context_with_intelligence(
    intelligence: MarketIntelligence,
) -> BusinessLogicContext:
    return BusinessLogicContext(
        context_id="ctx-card",
        base_currency="USD",
        valuation_data=[intelligence],
    )


def market_intelligence(
    *,
    confidence_score: int = 88,
    confidence_level: MarketConfidenceLevel = MarketConfidenceLevel.HIGH,
    agreement_score: int = 80,
    agreement_level: AgreementLevel = AgreementLevel.GOOD,
    freshness_level: FreshnessLevel = FreshnessLevel.RECENT,
    liquidity_level: LiquidityLevel = LiquidityLevel.HIGH,
    warnings: tuple[str, ...] = (),
) -> MarketIntelligence:
    return MarketIntelligence(
        intelligence_id="mi-card-001",
        asset_id="CARD-001",
        generated_at=REFERENCE,
        reference_datetime=REFERENCE,
        primary_market_price=Decimal("250"),
        primary_market_source="EBAY_SOLD",
        confidence_score=confidence_score,
        confidence_level=confidence_level,
        primary_market_score=30,
        agreement_score_component=24,
        freshness_score_component=16,
        coverage_score_component=8,
        liquidity_score_component=8,
        agreement_score=agreement_score,
        agreement_level=agreement_level,
        coverage_score=80,
        available_sources=("EBAY_SOLD", "CARD_LADDER", "PWCC", "GOLDIN"),
        expected_sources=(
            "EBAY_SOLD",
            "CARD_LADDER",
            "PWCC",
            "GOLDIN",
            "FANATICS",
        ),
        latest_market_date=date(2026, 7, 4),
        freshness_days=1,
        freshness_level=freshness_level,
        comparable_sales_count=5,
        liquidity_level=liquidity_level,
        warnings=warnings,
        raw_valuation_ids=("VAL-001", "VAL-002"),
    )
