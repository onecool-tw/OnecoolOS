from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal
import json
from pathlib import Path

from onecool_os.transactions.loader import TransactionLoader
from onecool_os.transactions.loader import TransactionLoaderError
from onecool_os.transactions.models import BaseTransaction
from onecool_os.transactions.models import TransactionError
from onecool_os.transactions.models import TransactionType
from onecool_os.transactions.registry import TransactionRegistry


def test_base_transaction_creation() -> None:
    transaction = sample_transaction()

    assert transaction.transaction_id == "TXN-001"
    assert transaction.date == date(2026, 1, 1)
    assert transaction.transaction_type == TransactionType.BUY
    assert transaction.amount == Decimal("1000")
    assert transaction.to_dict()["amount"] == "1000.00"


def test_base_transaction_is_immutable() -> None:
    transaction = sample_transaction()

    try:
        transaction.amount = Decimal("2000")
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("Transactions should be immutable.")


def test_base_transaction_rejects_invalid_type() -> None:
    try:
        BaseTransaction(
            transaction_id="TXN-002",
            date=date(2026, 1, 1),
            asset_id="ASSET-1",
            transaction_type="BAD",
            currency="USD",
            amount=Decimal("100"),
        )
    except TransactionError as exc:
        assert "Invalid transaction_type" in str(exc)
    else:
        raise AssertionError("Invalid transaction_type should be rejected.")


def test_base_transaction_rejects_negative_amount_when_inappropriate() -> None:
    try:
        BaseTransaction(
            transaction_id="TXN-003",
            date=date(2026, 1, 1),
            asset_id="ASSET-1",
            transaction_type=TransactionType.BUY,
            currency="USD",
            amount=Decimal("-100"),
        )
    except TransactionError as exc:
        assert "Invalid amount" in str(exc)
    else:
        raise AssertionError("Negative BUY amount should be rejected.")


def test_base_transaction_allows_negative_adjustment() -> None:
    transaction = BaseTransaction(
        transaction_id="TXN-004",
        date=date(2026, 1, 1),
        asset_id="ASSET-1",
        transaction_type=TransactionType.ADJUSTMENT,
        currency="USD",
        amount=Decimal("-10"),
    )

    assert transaction.amount == Decimal("-10")


def test_transaction_registry_register_get_list_unregister() -> None:
    registry = TransactionRegistry()
    transaction = sample_transaction()

    registry.register(transaction)

    assert registry.get("TXN-001") is transaction
    assert registry.list() == (transaction,)
    assert registry.unregister("TXN-001") is transaction
    assert registry.list() == ()


def test_transaction_registry_rejects_duplicate() -> None:
    registry = TransactionRegistry()
    registry.register(sample_transaction())

    try:
        registry.register(sample_transaction())
    except TransactionError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError("Duplicate transaction should be rejected.")


def test_transaction_registry_rejects_unknown() -> None:
    try:
        TransactionRegistry().get("missing")
    except TransactionError as exc:
        assert "Unknown transaction" in str(exc)
    else:
        raise AssertionError("Unknown transaction should be rejected.")


def test_transaction_loader_valid_json(tmp_path: Path) -> None:
    result = TransactionLoader().load(write_transactions_json(tmp_path))

    assert len(result.transactions) == 2
    assert result.registry.get("TXN-001").asset_id == "ASSET-1"
    assert result.transactions[0].transaction_type == TransactionType.BUY


def test_transaction_loader_template_loading() -> None:
    result = TransactionLoader().load(
        "data/transactions/transactions.example.json"
    )

    assert len(result.transactions) == 3
    assert result.transactions[0].transaction_id == "TXN-DEMO-001"


def test_transaction_loader_invalid_json(tmp_path: Path) -> None:
    json_path = tmp_path / "transactions.json"
    json_path.write_text("{invalid", encoding="utf-8")

    try:
        TransactionLoader().load(json_path)
    except TransactionLoaderError as exc:
        assert "Invalid transactions JSON" in str(exc)
    else:
        raise AssertionError("Invalid JSON should be rejected.")


def test_transaction_loader_missing_fields(tmp_path: Path) -> None:
    payload = transactions_json_payload()
    del payload["transactions"][0]["asset_id"]
    json_path = write_transactions_json(tmp_path, payload)

    try:
        TransactionLoader().load(json_path)
    except TransactionLoaderError as exc:
        assert "Missing required field" in str(exc)
        assert "asset_id" in str(exc)
    else:
        raise AssertionError("Missing fields should be rejected.")


def test_transaction_loader_invalid_transaction_type(tmp_path: Path) -> None:
    payload = transactions_json_payload()
    payload["transactions"][0]["transaction_type"] = "BAD"
    json_path = write_transactions_json(tmp_path, payload)

    try:
        TransactionLoader().load(json_path)
    except TransactionLoaderError as exc:
        assert "Invalid transaction_type" in str(exc)
    else:
        raise AssertionError("Invalid transaction_type should be rejected.")


def test_transaction_loader_rejects_negative_amount(tmp_path: Path) -> None:
    payload = transactions_json_payload()
    payload["transactions"][0]["amount"] = "-100"
    json_path = write_transactions_json(tmp_path, payload)

    try:
        TransactionLoader().load(json_path)
    except TransactionLoaderError as exc:
        assert "Invalid amount" in str(exc)
    else:
        raise AssertionError("Negative BUY amount should be rejected.")


def test_transaction_loader_rejects_duplicate_transaction_id(
    tmp_path: Path,
) -> None:
    payload = transactions_json_payload()
    payload["transactions"][1]["transaction_id"] = "TXN-001"
    json_path = write_transactions_json(tmp_path, payload)

    try:
        TransactionLoader().load(json_path)
    except TransactionLoaderError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError("Duplicate transaction_id should be rejected.")


def sample_transaction() -> BaseTransaction:
    return BaseTransaction(
        transaction_id="TXN-001",
        date=date(2026, 1, 1),
        asset_id="ASSET-1",
        transaction_type=TransactionType.BUY,
        currency="usd",
        amount=Decimal("1000"),
        notes="Sample transaction.",
    )


def transactions_json_payload() -> dict[str, object]:
    return {
        "transactions": [
            {
                "transaction_id": "TXN-001",
                "date": "2026-01-01",
                "asset_id": "ASSET-1",
                "transaction_type": "BUY",
                "currency": "USD",
                "amount": "1000",
                "notes": "Sample buy.",
            },
            {
                "transaction_id": "TXN-002",
                "date": "2026-01-02",
                "asset_id": "ASSET-1",
                "transaction_type": "DIVIDEND",
                "currency": "USD",
                "amount": "25",
            },
        ],
    }


def write_transactions_json(
    tmp_path: Path,
    payload: dict[str, object] | None = None,
) -> Path:
    json_path = tmp_path / "transactions.json"
    json_path.write_text(
        json.dumps(payload or transactions_json_payload()),
        encoding="utf-8",
    )
    return json_path
