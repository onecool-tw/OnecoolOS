import json
from datetime import date
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from onecool_os.__main__ import main
from onecool_os.assets.base import BaseAsset
from onecool_os.intelligence.valuation.engine import ValuationEngine
from onecool_os.intelligence.valuation.models import (
    ValuationError,
    ValuationResult,
)
from onecool_os.intelligence.valuation.registry import ValuationRegistry
from onecool_os.intelligence.valuation.valuators import DemoValuator
from onecool_os.valuation.enums import ValuationConfidence
from onecool_os.valuation.enums import ValuationSource
from onecool_os.valuation.enums import source_priority_for_asset
from onecool_os.valuation.loader import ValuationLoader
from onecool_os.valuation.loader import ValuationLoaderError
from onecool_os.valuation.models import ValuationRecord
from onecool_os.valuation.validation import ValuationError as RecordError


def test_valuation_result_to_dict() -> None:
    result = ValuationResult(
        asset_id="asset-1",
        asset_type="CASH",
        provider="demo",
        estimated_value=Decimal("100"),
        currency="TWD",
        valuation_time=datetime(2026, 6, 30, tzinfo=UTC),
        confidence=0.5,
        notes="Demo valuation.",
    )

    payload = result.to_dict()

    assert payload["asset_id"] == "asset-1"
    assert payload["estimated_value"] == "100.00"
    assert payload["provider"] == "demo"
    assert payload["confidence"] == 0.5


def test_valuation_registry_register_get_list_unregister() -> None:
    registry = ValuationRegistry()
    valuator = DemoValuator()

    registry.register(valuator)

    assert registry.get("demo") is valuator
    assert registry.list() == (valuator,)
    assert registry.unregister("demo") is valuator
    assert registry.list() == ()


def test_valuation_registry_rejects_duplicate() -> None:
    registry = ValuationRegistry()
    registry.register(DemoValuator())

    try:
        registry.register(DemoValuator())
    except ValuationError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError("Duplicate valuator should be rejected.")


def test_demo_valuator_supports_current_asset_modules() -> None:
    valuator = DemoValuator()

    assert valuator.supports(BaseAsset("fund", "MUTUAL_FUND", "Fund", "USD"))
    assert valuator.supports(BaseAsset("card", "SPORTS_CARD", "Card", "USD"))
    assert valuator.supports(BaseAsset("house", "REAL_ESTATE", "House", "TWD"))
    assert valuator.supports(BaseAsset("cash", "CASH", "Cash", "TWD"))


def test_demo_valuator_returns_mocked_result() -> None:
    asset = BaseAsset("cash", "CASH", "Cash", "TWD")

    result = DemoValuator().valuate(asset)

    assert result.asset_id == "cash"
    assert result.asset_type == "CASH"
    assert result.provider == "demo"
    assert result.estimated_value == Decimal("100000")
    assert result.currency == "TWD"


def test_valuation_engine_initializes_with_demo_valuator() -> None:
    engine = ValuationEngine().initialize()

    assert engine.started is True
    assert engine.registry.get("demo").provider_id == "demo"


def test_valuation_engine_valuates_supported_asset() -> None:
    engine = ValuationEngine().initialize()
    asset = BaseAsset("fund", "MUTUAL_FUND", "Fund", "USD")

    result = engine.valuate(asset)

    assert result.provider == "demo"
    assert result.estimated_value == Decimal("10000")


def test_valuation_engine_rejects_unsupported_asset() -> None:
    engine = ValuationEngine().initialize()
    asset = BaseAsset("other", "OTHER", "Other", "USD")

    try:
        engine.valuate(asset)
    except ValuationError as exc:
        assert "No valuator supports" in str(exc)
    else:
        raise AssertionError("Unsupported asset should be rejected.")


def test_cli_valuation_demo_works(capsys) -> None:
    assert main(["valuation", "demo"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert len(payload["valuations"]) == 4
    assert payload["valuations"][0]["asset"] == "Demo Fund"
    assert payload["valuations"][0]["provider"] == "demo"
    assert payload["valuations"][0]["estimated_value"] == "10000.00"
    assert payload["valuations"][0]["confidence"] == 0.5


def test_valuation_record_model_creation() -> None:
    record = sample_valuation_record()

    assert record.valuation_id == "VAL-001"
    assert record.asset_id == "CARD-001"
    assert record.asset_type == "SPORTS_CARD"
    assert record.source == ValuationSource.EBAY_SOLD
    assert record.source_priority == 2
    assert record.currency == "USD"
    assert record.market_value == Decimal("250")
    assert record.valuation_date == date(2026, 3, 15)
    assert record.confidence == ValuationConfidence.HIGH
    assert record.tags == ("demo", "card")
    assert record.to_dict()["market_value"] == "250.00"


def test_valuation_record_optional_fields() -> None:
    record = ValuationRecord(
        valuation_id="VAL-OPTIONAL",
        asset_id="CASH-TWD",
        asset_type="CASH",
        source="BROKER",
        currency="twd",
        estimated_value="1000",
        valuation_date="2026-03-15",
        confidence="MEDIUM",
    )

    assert record.source_priority == 1
    assert record.market_value is None
    assert record.effective_date is None
    assert record.note is None
    assert record.currency == "TWD"


def test_valuation_record_rejects_invalid_source() -> None:
    try:
        ValuationRecord(
            valuation_id="VAL-BAD",
            asset_id="ASSET-1",
            asset_type="ETF",
            source="BAD",
            currency="USD",
            market_value="100",
            valuation_date="2026-03-15",
            confidence="HIGH",
        )
    except RecordError as exc:
        assert "Invalid source" in str(exc)
    else:
        raise AssertionError("Invalid source should be rejected.")


def test_valuation_record_rejects_invalid_confidence() -> None:
    try:
        ValuationRecord(
            valuation_id="VAL-BAD",
            asset_id="ASSET-1",
            asset_type="ETF",
            source="YAHOO",
            currency="USD",
            market_value="100",
            valuation_date="2026-03-15",
            confidence="BAD",
        )
    except RecordError as exc:
        assert "Invalid confidence" in str(exc)
    else:
        raise AssertionError("Invalid confidence should be rejected.")


def test_valuation_record_rejects_negative_values() -> None:
    try:
        ValuationRecord(
            valuation_id="VAL-BAD",
            asset_id="ASSET-1",
            asset_type="ETF",
            source="YAHOO",
            currency="USD",
            market_value="-1",
            valuation_date="2026-03-15",
            confidence="HIGH",
        )
    except RecordError as exc:
        assert "market_value must not be negative" in str(exc)
    else:
        raise AssertionError("Negative values should be rejected.")


def test_valuation_record_rejects_low_value_greater_than_high_value() -> None:
    try:
        ValuationRecord(
            valuation_id="VAL-BAD",
            asset_id="ASSET-1",
            asset_type="REAL_ESTATE",
            source="BANK_VALUATION",
            currency="TWD",
            low_value="200",
            high_value="100",
            valuation_date="2026-03-15",
            confidence="LOW",
        )
    except RecordError as exc:
        assert "low_value cannot be greater than high_value" in str(exc)
    else:
        raise AssertionError("Invalid valuation range should be rejected.")


def test_valuation_record_requires_at_least_one_value() -> None:
    try:
        ValuationRecord(
            valuation_id="VAL-BAD",
            asset_id="ASSET-1",
            asset_type="ETF",
            source="YAHOO",
            currency="USD",
            valuation_date="2026-03-15",
            confidence="HIGH",
        )
    except RecordError as exc:
        assert "At least one valuation value field" in str(exc)
    else:
        raise AssertionError("Missing valuation value should be rejected.")


def test_valuation_source_priority_rules() -> None:
    assert source_priority_for_asset("SPORTS_CARD", "ONECOOL_FAIR_VALUE") == 1
    assert source_priority_for_asset("SPORTS_CARD", "EBAY_SOLD") == 2
    assert source_priority_for_asset("SPORTS_CARD", "MANUAL") == 8
    assert source_priority_for_asset("ETF", "YAHOO") == 1
    assert source_priority_for_asset("STOCK", "BROKER") == 3
    assert source_priority_for_asset("MUTUAL_FUND", "FUND_NAV") == 1
    assert source_priority_for_asset("REAL_ESTATE", "BANK_VALUATION") == 2
    assert source_priority_for_asset("CASH", "BROKER") == 1
    assert source_priority_for_asset("OTHER", "MANUAL") is None


def test_valuation_loader_valid_json(tmp_path: Path) -> None:
    result = ValuationLoader().load(write_valuation_json(tmp_path))

    assert result.valuation_book_name == "Test Valuation Book"
    assert result.base_currency == "TWD"
    assert len(result.valuations) == 2
    assert result.valuations[0].valuation_id == "VAL-001"


def test_valuation_loader_example_file() -> None:
    result = ValuationLoader().load("data/valuation/valuation.example.json")

    assert result.valuation_book_name == "Onecool Valuation Book"
    assert result.base_currency == "TWD"
    assert len(result.valuations) == 3


def test_valuation_loader_invalid_json(tmp_path: Path) -> None:
    json_path = tmp_path / "valuation.json"
    json_path.write_text("{invalid", encoding="utf-8")

    try:
        ValuationLoader().load(json_path)
    except ValuationLoaderError as exc:
        assert "Invalid valuation JSON" in str(exc)
    else:
        raise AssertionError("Invalid JSON should be rejected.")


def test_valuation_loader_missing_fields(tmp_path: Path) -> None:
    payload = valuation_json_payload()
    del payload["valuations"][0]["asset_id"]
    json_path = write_valuation_json(tmp_path, payload)

    try:
        ValuationLoader().load(json_path)
    except ValuationLoaderError as exc:
        assert "Missing required field" in str(exc)
        assert "asset_id" in str(exc)
    else:
        raise AssertionError("Missing valuation fields should be rejected.")


def test_valuation_loader_duplicate_ids(tmp_path: Path) -> None:
    payload = valuation_json_payload()
    payload["valuations"][1]["valuation_id"] = "VAL-001"
    json_path = write_valuation_json(tmp_path, payload)

    try:
        ValuationLoader().load(json_path)
    except ValuationLoaderError as exc:
        assert "Duplicate valuation_id" in str(exc)
    else:
        raise AssertionError("Duplicate valuation_id should be rejected.")


def test_valuation_loader_invalid_enum_value(tmp_path: Path) -> None:
    payload = valuation_json_payload()
    payload["valuations"][0]["source"] = "BAD"
    json_path = write_valuation_json(tmp_path, payload)

    try:
        ValuationLoader().load(json_path)
    except ValuationLoaderError as exc:
        assert "Invalid source" in str(exc)
    else:
        raise AssertionError("Invalid enum values should be rejected.")


def sample_valuation_record() -> ValuationRecord:
    return ValuationRecord(
        valuation_id="VAL-001",
        asset_id="CARD-001",
        asset_type="sports_card",
        source="ebay_sold",
        currency="usd",
        market_value="250",
        valuation_date="2026-03-15",
        effective_date="2026-03-14",
        confidence="high",
        note="Demo valuation.",
        url="https://example.com/valuation",
        tags=["demo", "card"],
    )


def valuation_json_payload() -> dict[str, object]:
    return {
        "valuation_book_name": "Test Valuation Book",
        "base_currency": "TWD",
        "valuations": [
            sample_valuation_record().to_dict(),
            {
                "valuation_id": "VAL-002",
                "asset_id": "ETF-001",
                "asset_type": "ETF",
                "source": "YAHOO",
                "currency": "USD",
                "estimated_value": "500",
                "valuation_date": "2026-03-15",
                "confidence": "MEDIUM",
            },
        ],
    }


def write_valuation_json(
    tmp_path: Path,
    payload: dict[str, object] | None = None,
) -> Path:
    json_path = tmp_path / "valuation.json"
    json_path.write_text(
        json.dumps(payload or valuation_json_payload()),
        encoding="utf-8",
    )
    return json_path
