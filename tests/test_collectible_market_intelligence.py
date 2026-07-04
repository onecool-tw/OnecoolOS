from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal

from onecool_os.connectors.collectibles import CardLadderConnector
from onecool_os.connectors.collectibles import EbaySoldConnector
from onecool_os.connectors.collectibles import FanaticsConnector
from onecool_os.connectors.collectibles import GoldinConnector
from onecool_os.connectors.collectibles import PWCCConnector
from onecool_os.valuation import AgreementLevel
from onecool_os.valuation import CollectibleMarketIntelligenceBuilder
from onecool_os.valuation import CollectibleValuationMapper
from onecool_os.valuation import ConfidenceLevel
from onecool_os.valuation import FreshnessLevel
from onecool_os.valuation import LiquidityLevel
from onecool_os.valuation import MarketIntelligence


REFERENCE = datetime(2026, 7, 4, tzinfo=timezone.utc)


def test_confidence_calculation() -> None:
    intelligence = build_intelligence(prices=("250", "260", "245", "255"))

    assert intelligence.confidence_score == 94
    assert intelligence.confidence_level == ConfidenceLevel.VERY_HIGH
    assert intelligence.primary_market_score == 30


def test_explainable_confidence_breakdown() -> None:
    intelligence = build_intelligence(prices=("250", "260", "245", "255"))

    assert intelligence.primary_market_score == 30
    assert intelligence.agreement_score_component == 30
    assert intelligence.freshness_score_component == 20
    assert intelligence.coverage_score_component == 8
    assert intelligence.liquidity_score_component == 6


def test_agreement_calculation() -> None:
    intelligence = build_intelligence(prices=("250", "260", "245", "255"))

    assert intelligence.agreement_score == 100
    assert intelligence.agreement_level == AgreementLevel.STRONG


def test_coverage_calculation() -> None:
    intelligence = build_intelligence(prices=("250", "260", "245", "255"))

    assert intelligence.available_sources == (
        "EBAY_SOLD",
        "CARD_LADDER",
        "PWCC",
        "GOLDIN",
    )
    assert intelligence.coverage_score == 80


def test_freshness_calculation() -> None:
    intelligence = build_intelligence(prices=("250", "260", "245", "255"))

    assert intelligence.latest_market_date.isoformat() == "2026-07-04"
    assert intelligence.freshness_days == 0
    assert intelligence.freshness_level == FreshnessLevel.LIVE


def test_liquidity_calculation() -> None:
    intelligence = build_intelligence(prices=("250", "260", "245", "255"))

    assert intelligence.comparable_sales_count == 4
    assert intelligence.liquidity_level == LiquidityLevel.MEDIUM


def test_warnings_for_low_coverage_and_liquidity() -> None:
    intelligence = build_intelligence(prices=("250",))

    assert "Validation Sources Missing" in intelligence.warnings
    assert "Low Liquidity" in intelligence.warnings
    assert "Low Confidence" in intelligence.warnings


def test_missing_primary_market_warning() -> None:
    mappings = [map_card_ladder("260")]

    intelligence = CollectibleMarketIntelligenceBuilder().build(
        mappings,
        reference_datetime=REFERENCE,
        asset_id="CARD-001",
    )

    assert intelligence.primary_market_price is None
    assert "Missing Primary Market Price" in intelligence.warnings


def test_stale_valuation_warning() -> None:
    intelligence = build_intelligence(
        prices=("250", "260"),
        sale_dates=("2026-01-01", "2026-01-02"),
    )

    assert intelligence.freshness_level == FreshnessLevel.STALE
    assert "Stale Market Data" in intelligence.warnings


def test_conflicting_sources_warning() -> None:
    intelligence = build_intelligence(prices=("250", "500"))

    assert intelligence.agreement_level == AgreementLevel.CONFLICT
    assert "Source Conflict" in intelligence.warnings


def test_low_coverage_warning() -> None:
    intelligence = build_intelligence(prices=("250", "260"))

    assert intelligence.coverage_score == 40
    assert "Validation Sources Missing" in intelligence.warnings


def test_low_liquidity_warning() -> None:
    intelligence = build_intelligence(prices=("250", "260"))

    assert intelligence.liquidity_level == LiquidityLevel.LOW
    assert "Low Liquidity" in intelligence.warnings


def test_injected_reference_datetime() -> None:
    reference = datetime(2026, 7, 10, tzinfo=timezone.utc)
    intelligence = build_intelligence(
        prices=("250", "260"),
        sale_dates=("2026-07-01", "2026-07-01"),
        reference_datetime=reference,
    )

    assert intelligence.reference_datetime == reference
    assert intelligence.generated_at == reference
    assert intelligence.freshness_days == 9


def test_replay_support() -> None:
    reference = datetime(2026, 8, 1, tzinfo=timezone.utc)
    first = build_intelligence(reference_datetime=reference)
    second = build_intelligence(reference_datetime=reference)

    assert first.to_dict() == second.to_dict()


def test_deterministic_output() -> None:
    mappings = sample_mappings()
    reversed_mappings = tuple(reversed(mappings))
    builder = CollectibleMarketIntelligenceBuilder()

    first = builder.build(mappings, reference_datetime=REFERENCE)
    second = builder.build(reversed_mappings, reference_datetime=REFERENCE)

    assert first.confidence_score == second.confidence_score
    assert first.available_sources == second.available_sources


def test_no_mutation() -> None:
    mappings = sample_mappings()
    before = deepcopy([mapping.to_dict() for mapping in mappings])

    CollectibleMarketIntelligenceBuilder().build(
        mappings,
        reference_datetime=REFERENCE,
    )

    after = [mapping.to_dict() for mapping in mappings]
    assert after == before


def test_empty_market_intelligence() -> None:
    intelligence = CollectibleMarketIntelligenceBuilder().build(
        (),
        reference_datetime=REFERENCE,
        asset_id="CARD-EMPTY",
    )

    assert isinstance(intelligence, MarketIntelligence)
    assert intelligence.asset_id == "CARD-EMPTY"
    assert intelligence.confidence_score == 0
    assert intelligence.raw_valuation_ids == ()


def build_intelligence(
    prices: tuple[str, ...] = ("250", "260", "245", "255", "248"),
    sale_dates: tuple[str, ...] = (
        "2026-07-01",
        "2026-07-02",
        "2026-07-03",
        "2026-07-04",
        "2026-07-04",
    ),
    reference_datetime: datetime = REFERENCE,
):
    mappings = sample_mappings(prices=prices, sale_dates=sale_dates)
    return CollectibleMarketIntelligenceBuilder().build(
        mappings,
        reference_datetime=reference_datetime,
    )


def sample_mappings(
    prices: tuple[str, ...] = ("250", "260", "245", "255", "248"),
    sale_dates: tuple[str, ...] = (
        "2026-07-01",
        "2026-07-02",
        "2026-07-03",
        "2026-07-04",
        "2026-07-04",
    ),
):
    builders = (
        map_ebay,
        map_card_ladder,
        map_pwcc,
        map_goldin,
        map_fanatics,
    )
    return tuple(
        builder(price, sale_dates[index])
        for index, (builder, price) in enumerate(zip(builders, prices))
    )


def map_ebay(price: str, sale_date: str = "2026-07-01"):
    return CollectibleValuationMapper().map_record(
        EbaySoldConnector().normalize_record(
            {
                "item_id": "EBAY-1",
                "title": "2018 Topps Shohei Ohtani PSA 10",
                "price": price,
                "currency": "USD",
                "sold_at": sale_date,
            }
        ),
        asset_id="CARD-001",
    )


def map_card_ladder(price: str, sale_date: str = "2026-07-02"):
    return CollectibleValuationMapper().map_record(
        CardLadderConnector().normalize_record(
            {
                "card_id": "CL-1",
                "title": "2018 Topps Shohei Ohtani PSA 10",
                "latest_value": price,
                "currency": "USD",
                "valuation_date": sale_date,
            }
        ),
        asset_id="CARD-001",
    )


def map_pwcc(price: str, sale_date: str = "2026-07-03"):
    return CollectibleValuationMapper().map_record(
        PWCCConnector().normalize_record(
            {
                "lot_id": "PWCC-1",
                "title": "2018 Topps Shohei Ohtani PSA 10",
                "sold_price": price,
                "currency": "USD",
                "auction_date": sale_date,
            }
        ),
        asset_id="CARD-001",
    )


def map_goldin(price: str, sale_date: str = "2026-07-04"):
    return CollectibleValuationMapper().map_record(
        GoldinConnector().normalize_record(
            {
                "lot_id": "GOLDIN-1",
                "title": "2018 Topps Shohei Ohtani PSA 10",
                "price": price,
                "currency": "USD",
                "date": sale_date,
            }
        ),
        asset_id="CARD-001",
    )


def map_fanatics(price: str, sale_date: str = "2026-07-04"):
    return CollectibleValuationMapper().map_record(
        FanaticsConnector().normalize_record(
            {
                "listing_id": "FANATICS-1",
                "title": "2018 Topps Shohei Ohtani PSA 10",
                "value": price,
                "currency": "USD",
                "date": sale_date,
            }
        ),
        asset_id="CARD-001",
    )
