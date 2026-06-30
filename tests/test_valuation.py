import json
from datetime import UTC, datetime
from decimal import Decimal

from onecool_os.__main__ import main
from onecool_os.assets.base import BaseAsset
from onecool_os.intelligence.valuation.engine import ValuationEngine
from onecool_os.intelligence.valuation.models import (
    ValuationError,
    ValuationResult,
)
from onecool_os.intelligence.valuation.registry import ValuationRegistry
from onecool_os.intelligence.valuation.valuators import DemoValuator


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
