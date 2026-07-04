from decimal import Decimal

from onecool_os.connectors.collectibles import BaseCollectibleConnector
from onecool_os.connectors.collectibles import CardLadderConnector
from onecool_os.connectors.collectibles import CollectibleMarketRecord
from onecool_os.connectors.collectibles import CollectibleMarketSource
from onecool_os.connectors.collectibles import CollectibleSourceRole
from onecool_os.connectors.collectibles import EbaySoldConnector
from onecool_os.connectors.collectibles import FanaticsConnector
from onecool_os.connectors.collectibles import GoldinConnector
from onecool_os.connectors.collectibles import PWCCConnector
from onecool_os.connectors.collectibles import source_role_for_source
from onecool_os.connectors.collectibles.models import (
    CollectibleConnectorError,
)


def test_collectible_market_record_model() -> None:
    record = CollectibleMarketRecord(
        record_id="ebay_sold:123",
        source="EBAY_SOLD",
        external_id="123",
        asset_hint={"player": "Shohei Ohtani"},
        title="Shohei Ohtani Rookie PSA 10",
        player="Shohei Ohtani",
        year=2018,
        brand="Topps",
        card_number="700",
        grade_company="PSA",
        grade=10,
        sale_price="250.50",
        currency="usd",
        sale_date="2026-07-01",
        url="https://example.test/card",
        raw_payload={"item_id": "123"},
    )

    assert record.source == CollectibleMarketSource.EBAY_SOLD
    assert record.sale_price == Decimal("250.50")
    assert record.currency == "USD"
    assert record.year == "2018"
    assert record.grade == "10"
    assert record.to_dict()["sale_price"] == "250.50"


def test_collectible_market_record_rejects_invalid_source() -> None:
    try:
        CollectibleMarketRecord(record_id="bad:1", source="BAD")
    except CollectibleConnectorError as exc:
        assert "Invalid source" in str(exc)
    else:
        raise AssertionError("Invalid source should be rejected.")


def test_source_role_mapping() -> None:
    assert (
        source_role_for_source(CollectibleMarketSource.EBAY_SOLD)
        == CollectibleSourceRole.PRIMARY_MARKET_PRICE
    )
    assert (
        source_role_for_source("CARD_LADDER")
        == CollectibleSourceRole.VALIDATION_SOURCE
    )
    assert (
        source_role_for_source("PWCC")
        == CollectibleSourceRole.VALIDATION_SOURCE
    )
    assert (
        source_role_for_source("GOLDIN")
        == CollectibleSourceRole.VALIDATION_SOURCE
    )
    assert (
        source_role_for_source("FANATICS")
        == CollectibleSourceRole.VALIDATION_SOURCE
    )
    assert (
        source_role_for_source("MANUAL")
        == CollectibleSourceRole.MANUAL_FALLBACK
    )


def test_base_connector_reads_local_records_without_mutation() -> None:
    raw = ebay_fixture()
    connector = EbaySoldConnector([raw])
    read_record = connector.read_records()[0]

    read_record["title"] = "changed"

    assert isinstance(connector, BaseCollectibleConnector)
    assert connector.read_records()[0]["title"] == raw["title"]


def test_ebay_fixture_normalization() -> None:
    record = EbaySoldConnector().normalize_record(ebay_fixture())

    assert record.source == CollectibleMarketSource.EBAY_SOLD
    assert record.record_id == "ebay_sold:EBAY-1"
    assert record.external_id == "EBAY-1"
    assert record.title == "2018 Topps Shohei Ohtani PSA 10"
    assert record.player == "Shohei Ohtani"
    assert record.sale_price == Decimal("250")
    assert record.currency == "USD"
    assert record.asset_hint["grade"] == "10"


def test_card_ladder_fixture_normalization() -> None:
    record = CardLadderConnector().normalize_record(
        {
            "card_id": "CL-1",
            "title": "2018 Topps Shohei Ohtani PSA 10",
            "player": "Shohei Ohtani",
            "year": "2018",
            "brand": "Topps",
            "card_number": "700",
            "grade_company": "PSA",
            "grade": "10",
            "latest_value": "260",
            "currency": "USD",
            "valuation_date": "2026-07-01",
        }
    )

    assert record.source == CollectibleMarketSource.CARD_LADDER
    assert record.record_id == "card_ladder:CL-1"
    assert record.sale_price == Decimal("260")


def test_pwcc_fixture_normalization() -> None:
    record = PWCCConnector().normalize_record(
        {
            "lot_id": "PWCC-1",
            "title": "2018 Topps Shohei Ohtani PSA 10",
            "sold_price": "245",
            "currency": "USD",
            "auction_date": "2026-07-02",
        }
    )

    assert record.source == CollectibleMarketSource.PWCC
    assert record.record_id == "pwcc:PWCC-1"
    assert record.sale_price == Decimal("245")


def test_goldin_fixture_normalization() -> None:
    record = GoldinConnector().normalize_record(
        {
            "lot_id": "GOLDIN-1",
            "title": "2018 Topps Shohei Ohtani PSA 10",
            "price": "255",
            "currency": "USD",
            "date": "2026-07-03",
        }
    )

    assert record.source == CollectibleMarketSource.GOLDIN
    assert record.record_id == "goldin:GOLDIN-1"
    assert record.sale_price == Decimal("255")


def test_fanatics_fixture_normalization() -> None:
    record = FanaticsConnector().normalize_record(
        {
            "listing_id": "FANATICS-1",
            "title": "2018 Topps Shohei Ohtani PSA 10",
            "value": "248",
            "currency": "USD",
            "date": "2026-07-04",
        }
    )

    assert record.source == CollectibleMarketSource.FANATICS
    assert record.record_id == "fanatics:FANATICS-1"
    assert record.sale_price == Decimal("248")


def test_connector_normalize_records_uses_local_records_only() -> None:
    connector = EbaySoldConnector([ebay_fixture()])

    records = connector.normalize_records()

    assert len(records) == 1
    assert records[0].source == CollectibleMarketSource.EBAY_SOLD


def test_normalization_rejects_missing_external_id() -> None:
    try:
        EbaySoldConnector().normalize_record({"title": "Missing id"})
    except CollectibleConnectorError as exc:
        assert "external_id" in str(exc)
    else:
        raise AssertionError("Missing external id should be rejected.")


def test_no_live_api_usage() -> None:
    connectors = (
        EbaySoldConnector(),
        CardLadderConnector(),
        PWCCConnector(),
        GoldinConnector(),
        FanaticsConnector(),
    )

    for connector in connectors:
        assert connector.read_records() == ()


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
