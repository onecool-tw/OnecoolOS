from datetime import date
from decimal import Decimal
import json
from pathlib import Path

from onecool_os.transactions.enums import EventType
from onecool_os.transactions.enums import TransactionStatus
from onecool_os.transactions.enums import TransactionType
from onecool_os.transactions.loader import TransactionLoader
from onecool_os.transactions.loader import TransactionLoaderError
from onecool_os.transactions.models import BaseTransaction
from onecool_os.transactions.models import Event
from onecool_os.transactions.models import Transaction
from onecool_os.transactions.models import TransactionError
from onecool_os.transactions.registry import TransactionRegistry


def test_transaction_model_creation() -> None:
    transaction = sample_transaction()

    assert transaction.transaction_id == "TXN-001"
    assert transaction.asset_id == "ASSET-1"
    assert transaction.asset_type == "ETF"
    assert transaction.trade_date == date(2026, 1, 1)
    assert transaction.transaction_type == TransactionType.BUY
    assert transaction.status == TransactionStatus.COMPLETED
    assert transaction.quantity == Decimal("10")
    assert transaction.price == Decimal("100")
    assert transaction.currency == "USD"
    assert transaction.fee == Decimal("1")
    assert transaction.tags == ("demo", "buy")
    assert transaction.to_dict()["transaction_type"] == "BUY"


def test_transaction_optional_fields() -> None:
    transaction = Transaction(
        transaction_id="TXN-OPTIONAL",
        asset_id="CASH-TWD",
        asset_type="CASH",
        transaction_type="DEPOSIT",
        trade_date="2026-01-01",
        currency="twd",
        status="PENDING",
    )

    assert transaction.quantity is None
    assert transaction.price is None
    assert transaction.portfolio_id is None
    assert transaction.currency == "TWD"
    assert transaction.status == TransactionStatus.PENDING


def test_transaction_rejects_invalid_type() -> None:
    try:
        Transaction(
            transaction_id="TXN-BAD",
            asset_id="ASSET-1",
            asset_type="ETF",
            transaction_type="BAD",
            trade_date="2026-01-01",
            currency="USD",
            status="COMPLETED",
        )
    except TransactionError as exc:
        assert "Invalid transaction_type" in str(exc)
    else:
        raise AssertionError("Invalid transaction_type should be rejected.")


def test_transaction_rejects_invalid_status() -> None:
    try:
        Transaction(
            transaction_id="TXN-BAD",
            asset_id="ASSET-1",
            asset_type="ETF",
            transaction_type="BUY",
            trade_date="2026-01-01",
            currency="USD",
            status="BAD",
        )
    except TransactionError as exc:
        assert "Invalid status" in str(exc)
    else:
        raise AssertionError("Invalid status should be rejected.")


def test_transaction_rejects_negative_cost() -> None:
    try:
        Transaction(
            transaction_id="TXN-BAD",
            asset_id="ASSET-1",
            asset_type="ETF",
            transaction_type="BUY",
            trade_date="2026-01-01",
            currency="USD",
            status="COMPLETED",
            fee="-1",
        )
    except TransactionError as exc:
        assert "fee must not be negative" in str(exc)
    else:
        raise AssertionError("Negative fee should be rejected.")


def test_event_model_creation() -> None:
    event = sample_event()

    assert event.event_id == "EVT-001"
    assert event.event_type == EventType.LISTED
    assert event.event_date == date(2026, 1, 2)
    assert event.asset_id == "ASSET-1"
    assert event.payload == {"platform": "Demo"}
    assert event.tags == ("demo",)
    assert event.to_dict()["event_type"] == "LISTED"


def test_event_rejects_invalid_type() -> None:
    try:
        Event(
            event_id="EVT-BAD",
            event_type="BAD",
            event_date="2026-01-01",
        )
    except TransactionError as exc:
        assert "Invalid event_type" in str(exc)
    else:
        raise AssertionError("Invalid event_type should be rejected.")


def test_enums() -> None:
    assert TransactionType.BUY.value == "BUY"
    assert TransactionType.TRANSFER_IN.value == "TRANSFER_IN"
    assert TransactionStatus.CANCELLED.value == "CANCELLED"
    assert EventType.SUBMITTED_GRADING.value == "SUBMITTED_GRADING"


def test_transaction_loader_valid_json(tmp_path: Path) -> None:
    result = TransactionLoader().load(write_ledger_json(tmp_path))

    assert result.ledger_name == "Test Ledger"
    assert result.base_currency == "TWD"
    assert len(result.transactions) == 2
    assert len(result.events) == 1
    assert result.transactions[0].transaction_id == "TXN-001"
    assert result.events[0].event_id == "EVT-001"


def test_transaction_loader_legacy_json(tmp_path: Path) -> None:
    json_path = tmp_path / "transactions.json"
    json_path.write_text(
        json.dumps(
            {
                "transactions": [
                    {
                        "transaction_id": "TXN-LEGACY",
                        "date": "2026-01-01",
                        "asset_id": "ASSET-1",
                        "transaction_type": "BUY",
                        "currency": "USD",
                        "amount": "100",
                        "notes": "Legacy transaction.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = TransactionLoader().load(json_path)

    assert len(result.transactions) == 1
    assert result.transactions[0].transaction_id == "TXN-LEGACY"
    assert result.transactions[0].asset_type == "OTHER"
    assert result.transactions[0].status == TransactionStatus.COMPLETED


def test_transaction_loader_example_file() -> None:
    result = TransactionLoader().load("data/transactions/ledger.example.json")

    assert result.ledger_name == "Onecool Ledger"
    assert result.base_currency == "TWD"
    assert len(result.transactions) == 2
    assert len(result.events) == 1


def test_transaction_loader_invalid_json(tmp_path: Path) -> None:
    json_path = tmp_path / "ledger.json"
    json_path.write_text("{invalid", encoding="utf-8")

    try:
        TransactionLoader().load(json_path)
    except TransactionLoaderError as exc:
        assert "Invalid ledger JSON" in str(exc)
    else:
        raise AssertionError("Invalid JSON should be rejected.")


def test_transaction_loader_missing_transaction_fields(tmp_path: Path) -> None:
    payload = ledger_json_payload()
    del payload["transactions"][0]["asset_id"]
    json_path = write_ledger_json(tmp_path, payload)

    try:
        TransactionLoader().load(json_path)
    except TransactionLoaderError as exc:
        assert "Missing required field" in str(exc)
        assert "asset_id" in str(exc)
    else:
        raise AssertionError("Missing transaction fields should be rejected.")


def test_transaction_loader_duplicate_transaction_ids(tmp_path: Path) -> None:
    payload = ledger_json_payload()
    payload["transactions"][1]["transaction_id"] = "TXN-001"
    json_path = write_ledger_json(tmp_path, payload)

    try:
        TransactionLoader().load(json_path)
    except TransactionLoaderError as exc:
        assert "Duplicate transaction_id" in str(exc)
    else:
        raise AssertionError("Duplicate transaction_id should be rejected.")


def test_transaction_loader_duplicate_event_ids(tmp_path: Path) -> None:
    payload = ledger_json_payload()
    payload["events"].append(dict(payload["events"][0]))
    json_path = write_ledger_json(tmp_path, payload)

    try:
        TransactionLoader().load(json_path)
    except TransactionLoaderError as exc:
        assert "Duplicate event_id" in str(exc)
    else:
        raise AssertionError("Duplicate event_id should be rejected.")


def test_transaction_loader_invalid_event_type(tmp_path: Path) -> None:
    payload = ledger_json_payload()
    payload["events"][0]["event_type"] = "BAD"
    json_path = write_ledger_json(tmp_path, payload)

    try:
        TransactionLoader().load(json_path)
    except TransactionLoaderError as exc:
        assert "Invalid event_type" in str(exc)
    else:
        raise AssertionError("Invalid event_type should be rejected.")


def test_base_transaction_backward_compatibility() -> None:
    transaction = BaseTransaction(
        transaction_id="TXN-BASE",
        date=date(2026, 1, 1),
        asset_id="ASSET-1",
        transaction_type=TransactionType.BUY,
        currency="usd",
        amount=Decimal("1000"),
        notes="Sample transaction.",
    )

    assert transaction.currency == "USD"
    assert transaction.to_dict()["amount"] == "1000.00"


def test_transaction_registry_register_get_list_unregister() -> None:
    registry = TransactionRegistry()
    transaction = BaseTransaction(
        transaction_id="TXN-BASE",
        date=date(2026, 1, 1),
        asset_id="ASSET-1",
        transaction_type=TransactionType.BUY,
        currency="USD",
        amount=Decimal("1000"),
    )

    registry.register(transaction)

    assert registry.get("TXN-BASE") is transaction
    assert registry.list() == (transaction,)
    assert registry.unregister("TXN-BASE") is transaction


def sample_transaction() -> Transaction:
    return Transaction(
        transaction_id="TXN-001",
        asset_id="ASSET-1",
        asset_type="ETF",
        portfolio_id="PORTFOLIO-1",
        trade_date="2026-01-01",
        settlement_date="2026-01-03",
        transaction_type="BUY",
        quantity="10",
        price="100",
        currency="usd",
        exchange_rate="31.5",
        fee="1",
        tax="0",
        shipping="0",
        insurance="0",
        other_cost="0",
        account="Demo Account",
        platform="Demo Platform",
        broker="Demo Broker",
        status="COMPLETED",
        note="Sample buy.",
        tags=["demo", "buy"],
    )


def sample_event() -> Event:
    return Event(
        event_id="EVT-001",
        event_type="LISTED",
        asset_id="ASSET-1",
        asset_type="ETF",
        related_transaction_id="TXN-001",
        event_date="2026-01-02",
        status="ACTIVE",
        payload={"platform": "Demo"},
        note="Sample event.",
        tags=["demo"],
    )


def ledger_json_payload() -> dict[str, object]:
    return {
        "ledger_name": "Test Ledger",
        "base_currency": "TWD",
        "transactions": [
            sample_transaction().to_dict(),
            {
                "transaction_id": "TXN-002",
                "asset_id": "CASH-TWD",
                "asset_type": "CASH",
                "trade_date": "2026-01-02",
                "transaction_type": "DEPOSIT",
                "currency": "TWD",
                "status": "COMPLETED",
            },
        ],
        "events": [
            sample_event().to_dict(),
        ],
    }


def write_ledger_json(
    tmp_path: Path,
    payload: dict[str, object] | None = None,
) -> Path:
    json_path = tmp_path / "ledger.json"
    json_path.write_text(
        json.dumps(payload or ledger_json_payload()),
        encoding="utf-8",
    )
    return json_path
