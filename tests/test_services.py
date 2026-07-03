import json
from pathlib import Path

from onecool_os.services import AnalyticsService
from onecool_os.services import BaseService
from onecool_os.services import LedgerService
from onecool_os.services import PortfolioService
from onecool_os.services import ServiceError
from onecool_os.services import ValuationService
from onecool_os.transactions.loader import TransactionLoaderError


def test_base_service_validate_ready() -> None:
    service = BaseService(service_name="demo")

    assert service.is_ready is False
    try:
        service.validate_ready()
    except ServiceError as exc:
        assert "demo has no loaded data" in str(exc)
    else:
        raise AssertionError("Unloaded service should fail readiness.")

    service._mark_loaded("demo source")

    assert service.is_ready is True
    assert service.source_description == "demo source"
    service.validate_ready()


def test_ledger_service_loads_and_lists_records() -> None:
    service = LedgerService().load("data/transactions/ledger.example.json")

    assert len(service.list_transactions()) == 2
    assert len(service.list_events()) == 1
    assert service.get_transaction_by_id(
        "TXN-DEMO-FUND-BUY-001"
    ).asset_id == "FUND-DEMO-001"
    assert service.get_event_by_id(
        "EVT-DEMO-CARD-LISTED-001"
    ).asset_id == "CARD-DEMO-001"
    assert service.get_transaction_by_id("missing") is None
    assert service.get_event_by_id("missing") is None


def test_ledger_service_requires_loaded_data() -> None:
    service = LedgerService()

    try:
        service.list_transactions()
    except ServiceError as exc:
        assert "ledger has no loaded data" in str(exc)
    else:
        raise AssertionError("Unloaded ledger service should fail.")


def test_ledger_service_missing_file_error(tmp_path: Path) -> None:
    service = LedgerService()

    try:
        service.load(tmp_path / "missing-ledger.json")
    except TransactionLoaderError as exc:
        assert "Ledger JSON file cannot be read" in str(exc)
    else:
        raise AssertionError("Missing ledger file should be rejected.")


def test_valuation_service_lookup_and_latest(tmp_path: Path) -> None:
    json_path = write_valuation_book(tmp_path)
    service = ValuationService().load(json_path)

    assert len(service.list_valuations()) == 3
    assert service.get_valuation_by_id("VAL-OLD").asset_id == "ASSET-1"
    assert len(service.get_valuations_for_asset("ASSET-1")) == 2
    assert (
        service.get_latest_valuation_for_asset("ASSET-1").valuation_id
        == "VAL-NEW"
    )
    assert service.get_latest_valuation_for_asset("missing") is None


def test_valuation_service_requires_loaded_data() -> None:
    service = ValuationService()

    try:
        service.list_valuations()
    except ServiceError as exc:
        assert "valuation has no loaded data" in str(exc)
    else:
        raise AssertionError("Unloaded valuation service should fail.")


def test_portfolio_service_lookup_and_summary() -> None:
    service = PortfolioService().load("data/portfolio/portfolio.example.json")

    assert len(service.list_holdings()) == 3
    assert service.get_holding_by_asset_id(
        "FUND-DEMO-001"
    ).asset_type == "MUTUAL_FUND"
    assert service.get_holding_by_asset_id("missing") is None

    summary = service.get_summary()

    assert summary["portfolio_id"] == "portfolio-demo"
    assert summary["portfolio_name"] == "Onecool Demo Portfolio"
    assert "holdings" not in summary


def test_portfolio_service_requires_loaded_data() -> None:
    service = PortfolioService()

    try:
        service.get_summary()
    except ServiceError as exc:
        assert "portfolio has no loaded data" in str(exc)
    else:
        raise AssertionError("Unloaded portfolio service should fail.")


def test_analytics_service_lookup_and_latest(tmp_path: Path) -> None:
    json_path = write_analytics_book(tmp_path)
    service = AnalyticsService().load(json_path)

    assert len(service.list_snapshots()) == 3
    assert service.get_snapshot_by_id(
        "SNAPSHOT-OLD"
    ).portfolio_id == "portfolio-1"
    assert (
        service.get_latest_snapshot_for_portfolio(
            "portfolio-1"
        ).snapshot_id == "SNAPSHOT-NEW"
    )
    assert service.get_latest_snapshot_for_portfolio("missing") is None


def test_analytics_service_requires_loaded_data() -> None:
    service = AnalyticsService()

    try:
        service.list_snapshots()
    except ServiceError as exc:
        assert "analytics has no loaded data" in str(exc)
    else:
        raise AssertionError("Unloaded analytics service should fail.")


def test_services_do_not_modify_underlying_files(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text(
        Path("data/transactions/ledger.example.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    before = ledger_path.read_text(encoding="utf-8")

    service = LedgerService().load(ledger_path)
    service.list_transactions()
    service.get_event_by_id("EVT-DEMO-CARD-LISTED-001")

    after = ledger_path.read_text(encoding="utf-8")
    assert after == before


def write_valuation_book(tmp_path: Path) -> Path:
    payload = {
        "valuation_book_name": "Service Valuation Book",
        "base_currency": "TWD",
        "valuations": [
            valuation_payload("VAL-OLD", "ASSET-1", "2026-01-01", "100"),
            valuation_payload("VAL-NEW", "ASSET-1", "2026-02-01", "110"),
            valuation_payload("VAL-OTHER", "ASSET-2", "2026-01-15", "50"),
        ],
    }
    json_path = tmp_path / "valuations.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    return json_path


def valuation_payload(
    valuation_id: str,
    asset_id: str,
    valuation_date: str,
    market_value: str,
) -> dict[str, str]:
    return {
        "valuation_id": valuation_id,
        "asset_id": asset_id,
        "asset_type": "ETF",
        "source": "YAHOO",
        "currency": "USD",
        "market_value": market_value,
        "valuation_date": valuation_date,
        "confidence": "HIGH",
    }


def write_analytics_book(tmp_path: Path) -> Path:
    payload = {
        "analytics_book_name": "Service Analytics Book",
        "base_currency": "TWD",
        "snapshots": [
            analytics_payload("SNAPSHOT-OLD", "portfolio-1", "2026-01-01"),
            analytics_payload("SNAPSHOT-NEW", "portfolio-1", "2026-02-01"),
            analytics_payload("SNAPSHOT-OTHER", "portfolio-2", "2026-01-15"),
        ],
    }
    json_path = tmp_path / "analytics.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    return json_path


def analytics_payload(
    snapshot_id: str,
    portfolio_id: str,
    snapshot_date: str,
) -> dict[str, str]:
    return {
        "snapshot_id": snapshot_id,
        "portfolio_id": portfolio_id,
        "base_currency": "TWD",
        "snapshot_date": snapshot_date,
        "total_cost": "100",
        "total_market_value": "110",
        "risk_level": "LOW",
    }
