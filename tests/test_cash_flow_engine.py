from decimal import Decimal

from onecool_os.business_logic import BusinessLogicContext
from onecool_os.business_logic import CashFlowEngine
from onecool_os.business_logic import MetricType
from onecool_os.transactions.loader import TransactionLoader


def test_cash_flow_engine_supports_context() -> None:
    engine = CashFlowEngine()
    context = BusinessLogicContext(context_id="context-1")

    assert engine.engine_name == "cash_flow"
    assert engine.engine_version == "v1"
    assert engine.supports(context) is True


def test_cash_flow_engine_empty_ledger() -> None:
    result = CashFlowEngine().calculate(
        BusinessLogicContext(context_id="empty", base_currency="TWD")
    )

    assert result.metric_type == MetricType.CASH_FLOW
    assert result.value == Decimal("0")
    assert result.currency == "TWD"
    assert result.payload["cash_inflow"] == Decimal("0")
    assert result.payload["cash_outflow"] == Decimal("0")
    assert result.payload["net_cash_flow"] == Decimal("0")
    assert result.payload["transaction_count"] == 0


def test_cash_flow_engine_inflow_transactions() -> None:
    context = BusinessLogicContext(
        context_id="inflow",
        base_currency="USD",
        ledger_data={
            "transactions": [
                transaction("SELL", quantity="2", price="100"),
                transaction("DIVIDEND", price="25"),
                transaction("INTEREST", price="5"),
                transaction("DEPOSIT", price="50"),
                transaction("TRANSFER_IN", price="20"),
            ]
        },
    )

    result = CashFlowEngine().calculate(context)

    assert result.payload["cash_inflow"] == Decimal("300")
    assert result.payload["cash_outflow"] == Decimal("0")
    assert result.value == Decimal("300")


def test_cash_flow_engine_outflow_transactions() -> None:
    context = BusinessLogicContext(
        context_id="outflow",
        ledger_data={
            "transactions": [
                transaction("BUY", quantity="3", price="10"),
                transaction("WITHDRAW", price="15"),
                transaction("TRANSFER_OUT", price="20"),
                transaction("FEE", price="2"),
                transaction("TAX", price="3"),
            ]
        },
    )

    result = CashFlowEngine().calculate(context)

    assert result.payload["cash_inflow"] == Decimal("0")
    assert result.payload["cash_outflow"] == Decimal("70")
    assert result.value == Decimal("-70")


def test_cash_flow_engine_costs_count_as_outflows() -> None:
    context = BusinessLogicContext(
        context_id="costs",
        ledger_data={
            "transactions": [
                transaction(
                    "BUY",
                    quantity="1",
                    price="100",
                    fee="2",
                    tax="3",
                    shipping="4",
                    insurance="5",
                    other_cost="6",
                )
            ]
        },
    )

    result = CashFlowEngine().calculate(context)

    assert result.payload["fees"] == Decimal("2")
    assert result.payload["taxes"] == Decimal("3")
    assert result.payload["shipping"] == Decimal("4")
    assert result.payload["insurance"] == Decimal("5")
    assert result.payload["other_cost"] == Decimal("6")
    assert result.payload["cash_outflow"] == Decimal("120")
    assert result.payload["net_cash_flow"] == Decimal("-120")


def test_cash_flow_engine_mixed_inflow_outflow() -> None:
    context = BusinessLogicContext(
        context_id="mixed",
        base_currency="USD",
        ledger_data={
            "transactions": [
                transaction("SELL", quantity="2", price="100"),
                transaction("BUY", quantity="1", price="75", fee="5"),
                transaction("DIVIDEND", price="10"),
            ]
        },
    )

    result = CashFlowEngine().calculate(context)

    assert result.payload["cash_inflow"] == Decimal("210")
    assert result.payload["cash_outflow"] == Decimal("80")
    assert result.payload["net_cash_flow"] == Decimal("130")
    assert result.value == result.payload["net_cash_flow"]
    assert result.currency == "USD"


def test_cash_flow_engine_missing_optional_cost_fields() -> None:
    context = BusinessLogicContext(
        context_id="missing-costs",
        ledger_data={"transactions": [transaction("BUY", price="10")]},
    )

    result = CashFlowEngine().calculate(context)

    assert result.payload["fees"] == Decimal("0")
    assert result.payload["taxes"] == Decimal("0")
    assert result.payload["shipping"] == Decimal("0")
    assert result.payload["insurance"] == Decimal("0")
    assert result.payload["other_cost"] == Decimal("0")
    assert result.payload["cash_outflow"] == Decimal("10")


def test_cash_flow_engine_transaction_count() -> None:
    context = BusinessLogicContext(
        context_id="count",
        ledger_data={
            "transactions": [
                transaction("SELL", price="1"),
                transaction("BUY", price="1"),
                transaction("DIVIDEND", price="1"),
            ]
        },
    )

    result = CashFlowEngine().calculate(context)

    assert result.payload["transaction_count"] == 3


def test_cash_flow_engine_accepts_loaded_ledger_result() -> None:
    ledger = TransactionLoader().load("data/transactions/ledger.example.json")
    context = BusinessLogicContext(
        context_id="loaded-ledger",
        base_currency=ledger.base_currency,
        ledger_data=ledger,
    )

    result = CashFlowEngine().calculate(context)

    assert result.payload["transaction_count"] == 2
    assert result.payload["cash_inflow"] == Decimal("0")
    assert result.payload["fees"] == Decimal("1")
    assert result.payload["shipping"] == Decimal("12")
    assert result.payload["insurance"] == Decimal("5")
    assert result.payload["cash_outflow"] == Decimal("1268")
    assert result.value == Decimal("-1268")


def transaction(
    transaction_type: str,
    price: str,
    quantity: str | None = None,
    fee: str | None = None,
    tax: str | None = None,
    shipping: str | None = None,
    insurance: str | None = None,
    other_cost: str | None = None,
) -> dict[str, str]:
    payload = {
        "transaction_type": transaction_type,
        "price": price,
    }
    optional_values = {
        "quantity": quantity,
        "fee": fee,
        "tax": tax,
        "shipping": shipping,
        "insurance": insurance,
        "other_cost": other_cost,
    }
    for key, value in optional_values.items():
        if value is not None:
            payload[key] = value
    return payload
