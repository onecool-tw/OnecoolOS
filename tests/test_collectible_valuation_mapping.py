from copy import deepcopy
from decimal import Decimal

from onecool_os.connectors.collectibles import CardLadderConnector
from onecool_os.connectors.collectibles import CollectibleMarketRecord
from onecool_os.connectors.collectibles import CollectibleSourceRole
from onecool_os.connectors.collectibles import EbaySoldConnector
from onecool_os.connectors.collectibles import FanaticsConnector
from onecool_os.connectors.collectibles import GoldinConnector
from onecool_os.connectors.collectibles import PWCCConnector
from onecool_os.valuation import CollectibleValuationMapper
from onecool_os.valuation.enums import ValuationConfidence
from onecool_os.valuation.enums import ValuationSource
from onecool_os.valuation.models import ValuationRecord
from onecool_os.valuation.validation import ValuationError


def test_ebay_sold_mapping() -> None:
    mapping = CollectibleValuationMapper().map_record(
        EbaySoldConnector().normalize_record(ebay_fixture()),
        asset_id="CARD-001",
    )

    record = mapping.valuation_record
    assert isinstance(record, ValuationRecord)
    assert record.asset_id == "CARD-001"
    assert record.asset_type == "SPORTS_CARD"
    assert record.source == ValuationSource.EBAY_SOLD
    assert record.market_value == Decimal("250")
    assert record.currency == "USD"
    assert record.valuation_date.isoformat() == "2026-07-01"
    assert record.confidence == ValuationConfidence.LOW
    assert mapping.metadata["primary_market_price"] is True
    assert mapping.metadata["validation_source"] is False
    assert (
        mapping.metadata["source_role"]
        == CollectibleSourceRole.PRIMARY_MARKET_PRICE.value
    )


def test_card_ladder_mapping() -> None:
    mapping = CollectibleValuationMapper().map_record(
        CardLadderConnector().normalize_record(card_ladder_fixture())
    )

    assert mapping.valuation_record.source == ValuationSource.CARD_LADDER
    assert mapping.metadata["primary_market_price"] is False
    assert mapping.metadata["validation_source"] is True


def test_pwcc_mapping() -> None:
    mapping = CollectibleValuationMapper().map_record(
        PWCCConnector().normalize_record(pwcc_fixture())
    )

    assert mapping.valuation_record.source == ValuationSource.PWCC
    assert mapping.metadata["source_role"] == "VALIDATION_SOURCE"


def test_goldin_mapping() -> None:
    mapping = CollectibleValuationMapper().map_record(
        GoldinConnector().normalize_record(goldin_fixture())
    )

    assert mapping.valuation_record.source == ValuationSource.GOLDIN
    assert mapping.valuation_record.market_value == Decimal("255")


def test_fanatics_mapping() -> None:
    mapping = CollectibleValuationMapper().map_record(
        FanaticsConnector().normalize_record(fanatics_fixture())
    )

    assert mapping.valuation_record.source == ValuationSource.FANATICS
    assert mapping.valuation_record.url is None


def test_source_role_preservation() -> None:
    mapper = CollectibleValuationMapper()
    ebay_mapping = mapper.map_record(
        EbaySoldConnector().normalize_record(ebay_fixture())
    )
    pwcc_mapping = mapper.map_record(
        PWCCConnector().normalize_record(pwcc_fixture())
    )

    assert ebay_mapping.metadata["source_role"] == "PRIMARY_MARKET_PRICE"
    assert pwcc_mapping.metadata["source_role"] == "VALIDATION_SOURCE"


def test_raw_payload_preservation() -> None:
    raw = ebay_fixture()
    mapping = CollectibleValuationMapper().map_record(
        EbaySoldConnector().normalize_record(raw)
    )

    assert mapping.metadata["raw_payload"] == raw
    assert mapping.metadata["external_id"] == "EBAY-1"
    assert mapping.metadata["raw_market_record_id"] == "ebay_sold:EBAY-1"


def test_missing_sale_price_returns_clear_validation_error() -> None:
    record = CollectibleMarketRecord(
        record_id="ebay_sold:missing-price",
        source="EBAY_SOLD",
        external_id="missing-price",
        currency="USD",
        sale_date="2026-07-01",
    )

    try:
        CollectibleValuationMapper().map_record(record)
    except ValuationError as exc:
        assert "sale_price is required" in str(exc)
    else:
        raise AssertionError("Missing sale price should be rejected.")


def test_missing_currency_returns_clear_validation_error() -> None:
    record = CollectibleMarketRecord(
        record_id="ebay_sold:missing-currency",
        source="EBAY_SOLD",
        external_id="missing-currency",
        sale_price="100",
        sale_date="2026-07-01",
    )

    try:
        CollectibleValuationMapper().map_record(record)
    except ValuationError as exc:
        assert "currency is required" in str(exc)
    else:
        raise AssertionError("Missing currency should be rejected.")


def test_no_final_valuation_selection() -> None:
    payload = CollectibleValuationMapper().to_dict(
        EbaySoldConnector().normalize_record(ebay_fixture())
    )

    assert "final_market_value" not in payload
    assert "selected_market_value" not in payload
    assert payload["metadata"]["source_agreement_status"] is None


def test_no_mutation_behavior() -> None:
    raw = ebay_fixture()
    original = deepcopy(raw)
    market_record = EbaySoldConnector().normalize_record(raw)
    metadata_before = deepcopy(market_record.raw_payload)

    CollectibleValuationMapper().map_record(market_record)

    assert raw == original
    assert market_record.raw_payload == metadata_before


def ebay_fixture() -> dict[str, str]:
    return {
        "item_id": "EBAY-1",
        "title": "2018 Topps Shohei Ohtani PSA 10",
        "player": "Shohei Ohtani",
        "year": "2018",
        "brand": "Topps",
        "card_number": "700",
        "grade_company": "PSA",
        "grade": "10",
        "price": "250",
        "currency": "USD",
        "sold_at": "2026-07-01",
        "url": "https://example.test/ebay/EBAY-1",
    }


def card_ladder_fixture() -> dict[str, str]:
    return {
        "card_id": "CL-1",
        "title": "2018 Topps Shohei Ohtani PSA 10",
        "latest_value": "260",
        "currency": "USD",
        "valuation_date": "2026-07-01",
    }


def pwcc_fixture() -> dict[str, str]:
    return {
        "lot_id": "PWCC-1",
        "title": "2018 Topps Shohei Ohtani PSA 10",
        "sold_price": "245",
        "currency": "USD",
        "auction_date": "2026-07-02",
    }


def goldin_fixture() -> dict[str, str]:
    return {
        "lot_id": "GOLDIN-1",
        "title": "2018 Topps Shohei Ohtani PSA 10",
        "price": "255",
        "currency": "USD",
        "date": "2026-07-03",
    }


def fanatics_fixture() -> dict[str, str]:
    return {
        "listing_id": "FANATICS-1",
        "title": "2018 Topps Shohei Ohtani PSA 10",
        "value": "248",
        "currency": "USD",
        "date": "2026-07-04",
    }
