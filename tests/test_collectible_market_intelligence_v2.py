from copy import deepcopy
from datetime import datetime
from datetime import timezone
from decimal import Decimal

from onecool_os.valuation import AgreementLevel
from onecool_os.valuation import CollectibleMarketIntelligenceBuilder
from onecool_os.valuation import CollectibleValuationMapping
from onecool_os.valuation import SourceAgreementLevel
from onecool_os.valuation import SourceAgreementResult
from onecool_os.valuation import ValuationRecord


REFERENCE = datetime(2026, 7, 6, tzinfo=timezone.utc)


def test_market_intelligence_consumes_source_agreement_result() -> None:
    result = build_intelligence(
        source_agreement=source_agreement(
            score=88,
            level=SourceAgreementLevel.GOOD,
            participating_sources=("EBAY_SOLD", "CARD_LADDER", "MANUAL"),
            warnings=("Source Agreement Weak",),
        )
    )

    assert result.agreement_score == 88
    assert result.agreement_level == AgreementLevel.GOOD
    assert result.available_sources == (
        "EBAY_SOLD",
        "CARD_LADDER",
        "MANUAL",
    )
    assert "Source Agreement Weak" in result.warnings


def test_market_intelligence_does_not_recalculate_when_provided() -> None:
    mappings = (
        mapping("EBAY_SOLD", "250", "ebay-1", primary=True),
        mapping("CARD_LADDER", "500", "cl-1", validation=True),
    )
    injected = source_agreement(
        score=100,
        level=SourceAgreementLevel.STRONG,
        primary_price=Decimal("250"),
        validation_sources={"CARD_LADDER": Decimal("500")},
        participating_sources=("EBAY_SOLD", "CARD_LADDER"),
    )

    result = CollectibleMarketIntelligenceBuilder().build(
        mappings,
        reference_datetime=REFERENCE,
        source_agreement=injected,
    )

    assert result.agreement_score == 100
    assert result.agreement_level == AgreementLevel.STRONG
    assert "Source Conflict" not in result.warnings


def test_market_intelligence_preserves_source_agreement_warnings() -> None:
    result = build_intelligence(
        source_agreement=source_agreement(
            score=35,
            level=SourceAgreementLevel.WEAK,
            warnings=(
                "Validation Sources Missing",
                "Low Source Count",
                "High Divergence",
            ),
        )
    )

    assert "Validation Sources Missing" in result.warnings
    assert "Low Source Count" in result.warnings
    assert "High Divergence" in result.warnings


def test_market_intelligence_backward_compatibility_without_result() -> None:
    result = build_intelligence()

    assert result.agreement_score == 100
    assert result.agreement_level == AgreementLevel.STRONG
    assert result.available_sources == ("EBAY_SOLD", "CARD_LADDER")


def test_market_intelligence_confidence_uses_source_agreement_component() -> None:
    result = build_intelligence(
        source_agreement=source_agreement(
            score=50,
            level=SourceAgreementLevel.FAIR,
        )
    )

    assert result.agreement_score_component == 15
    assert result.confidence_score == 68


def test_market_intelligence_missing_primary_warning_propagates() -> None:
    result = build_intelligence(
        mappings=(mapping("CARD_LADDER", "255", "cl-1", validation=True),),
        source_agreement=source_agreement(
            score=0,
            level=SourceAgreementLevel.UNKNOWN,
            primary_source=None,
            primary_price=None,
            validation_sources={"CARD_LADDER": Decimal("255")},
            participating_sources=("CARD_LADDER",),
            warnings=("Missing Primary Market Price",),
        ),
    )

    assert result.primary_market_price is None
    assert result.agreement_level == AgreementLevel.UNKNOWN
    assert "Missing Primary Market Price" in result.warnings


def test_market_intelligence_source_conflict_warning_propagates() -> None:
    result = build_intelligence(
        source_agreement=source_agreement(
            score=10,
            level=SourceAgreementLevel.CONFLICT,
            warnings=("Source Conflict", "High Divergence"),
        )
    )

    assert result.agreement_level == AgreementLevel.CONFLICT
    assert "Source Conflict" in result.warnings
    assert "High Divergence" in result.warnings


def test_market_intelligence_v2_no_mutation() -> None:
    mappings = default_mappings()
    agreement = source_agreement()
    before_mappings = deepcopy([item.to_dict() for item in mappings])
    before_agreement = agreement.to_dict()

    CollectibleMarketIntelligenceBuilder().build(
        mappings,
        reference_datetime=REFERENCE,
        source_agreement=agreement,
    )

    assert [item.to_dict() for item in mappings] == before_mappings
    assert agreement.to_dict() == before_agreement


def test_market_intelligence_v2_deterministic_replay() -> None:
    mappings = default_mappings()
    agreement = source_agreement(score=88, level=SourceAgreementLevel.GOOD)
    builder = CollectibleMarketIntelligenceBuilder()

    first = builder.build(
        mappings,
        reference_datetime=REFERENCE,
        source_agreement=agreement,
    ).to_dict()
    second = builder.build(
        mappings,
        reference_datetime=REFERENCE,
        source_agreement=agreement,
    ).to_dict()

    assert first == second


def build_intelligence(
    *,
    mappings=None,
    source_agreement: SourceAgreementResult | None = None,
):
    return CollectibleMarketIntelligenceBuilder().build(
        default_mappings() if mappings is None else mappings,
        reference_datetime=REFERENCE,
        source_agreement=source_agreement,
    )


def default_mappings():
    return (
        mapping("EBAY_SOLD", "250", "ebay-1", primary=True),
        mapping("CARD_LADDER", "255", "cl-1", validation=True),
    )


def mapping(
    source: str,
    value: str,
    valuation_id: str,
    *,
    primary: bool = False,
    validation: bool = False,
) -> CollectibleValuationMapping:
    return CollectibleValuationMapping(
        valuation_record=ValuationRecord(
            valuation_id=valuation_id,
            asset_id="card-1",
            asset_type="SPORTS_CARD",
            source=source,
            currency="USD",
            valuation_date="2026-07-04",
            confidence="LOW",
            market_value=value,
        ),
        metadata={
            "primary_market_price": primary,
            "validation_source": validation,
        },
    )


def source_agreement(
    *,
    score: int = 98,
    level: SourceAgreementLevel = SourceAgreementLevel.STRONG,
    primary_source: str | None = "EBAY_SOLD",
    primary_price: Decimal | None = Decimal("250"),
    validation_sources: dict[str, Decimal] | None = None,
    participating_sources: tuple[str, ...] = ("EBAY_SOLD", "CARD_LADDER"),
    warnings: tuple[str, ...] = (),
) -> SourceAgreementResult:
    return SourceAgreementResult(
        agreement_id="source-agreement:card-1",
        asset_id="card-1",
        generated_at=REFERENCE,
        reference_datetime=REFERENCE,
        primary_market_source=primary_source,
        primary_market_price=primary_price,
        validation_sources=(
            {"CARD_LADDER": Decimal("255")}
            if validation_sources is None
            else validation_sources
        ),
        participating_sources=participating_sources,
        missing_sources=("MANUAL", "PWCC", "GOLDIN", "FANATICS"),
        agreement_score=score,
        agreement_level=level,
        agreement_spread=Decimal("0.02") if primary_price is not None else None,
        max_divergence=Decimal("0.02") if primary_price is not None else None,
        source_count=len(participating_sources),
        warnings=warnings,
        raw_valuation_ids=("ebay-1", "cl-1"),
    )
