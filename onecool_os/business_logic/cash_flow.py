"""Cash Flow Engine foundation."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from onecool_os.business_logic.calculators import BaseCalculator
from onecool_os.business_logic.context import BusinessLogicContext
from onecool_os.business_logic.results import BusinessLogicResult


class CashFlowEngine(BaseCalculator):
    """Calculate deterministic cash flow metrics from ledger data."""

    inflow_types = frozenset(
        {
            "SELL",
            "DIVIDEND",
            "INTEREST",
            "DEPOSIT",
            "TRANSFER_IN",
        }
    )
    outflow_types = frozenset(
        {
            "BUY",
            "WITHDRAW",
            "TRANSFER_OUT",
            "FEE",
            "TAX",
        }
    )
    cost_fields = (
        "fee",
        "tax",
        "shipping",
        "insurance",
        "other_cost",
    )

    def __init__(self) -> None:
        super().__init__(engine_name="cash_flow", engine_version="v1")

    def supports(self, context: BusinessLogicContext) -> bool:
        """Return whether this engine can inspect the context."""

        return isinstance(context, BusinessLogicContext)

    def calculate(
        self,
        context: BusinessLogicContext,
    ) -> BusinessLogicResult:
        """Calculate cash flow totals from ledger transactions."""

        transactions = tuple(_extract_transactions(context.ledger_data))
        totals = {
            "cash_inflow": Decimal("0"),
            "cash_outflow": Decimal("0"),
            "fees": Decimal("0"),
            "taxes": Decimal("0"),
            "shipping": Decimal("0"),
            "insurance": Decimal("0"),
            "other_cost": Decimal("0"),
        }

        for transaction in transactions:
            transaction_type = _transaction_type(transaction)
            amount = _transaction_amount(transaction)
            if transaction_type in self.inflow_types:
                totals["cash_inflow"] += amount
            if transaction_type in self.outflow_types:
                totals["cash_outflow"] += amount

            costs = _transaction_costs(transaction)
            totals["fees"] += costs["fee"]
            totals["taxes"] += costs["tax"]
            totals["shipping"] += costs["shipping"]
            totals["insurance"] += costs["insurance"]
            totals["other_cost"] += costs["other_cost"]
            totals["cash_outflow"] += sum(costs.values(), Decimal("0"))

        net_cash_flow = totals["cash_inflow"] - totals["cash_outflow"]
        payload = {
            **totals,
            "net_cash_flow": net_cash_flow,
            "transaction_count": len(transactions),
        }
        return BusinessLogicResult(
            result_id=f"{context.context_id}-cash-flow",
            engine_name=self.engine_name,
            engine_version=self.engine_version,
            metric_type="CASH_FLOW",
            value=net_cash_flow,
            currency=context.base_currency,
            payload=payload,
            confidence="HIGH",
            note="Deterministic cash flow metrics from ledger data.",
            tags=["cash_flow", "business_logic"],
        )


def _extract_transactions(ledger_data: Any) -> tuple[Any, ...]:
    if ledger_data in (None, ""):
        return ()
    if hasattr(ledger_data, "transactions"):
        transactions = getattr(ledger_data, "transactions")
        return tuple(transactions or ())
    if isinstance(ledger_data, dict):
        transactions = ledger_data.get("transactions", ())
        return tuple(transactions or ())
    if isinstance(ledger_data, (list, tuple)):
        return tuple(ledger_data)
    return ()


def _transaction_type(transaction: Any) -> str:
    value = _get_value(transaction, "transaction_type")
    if hasattr(value, "value"):
        return str(value.value).upper()
    return str(value or "").upper()


def _transaction_amount(transaction: Any) -> Decimal:
    quantity = _decimal_or_none(_get_value(transaction, "quantity"))
    price = _decimal_or_none(_get_value(transaction, "price"))
    if quantity is not None and price is not None:
        return quantity * price
    if price is not None:
        return price
    return Decimal("0")


def _transaction_costs(transaction: Any) -> dict[str, Decimal]:
    return {
        field_name: _decimal_or_none(_get_value(transaction, field_name))
        or Decimal("0")
        for field_name in CashFlowEngine.cost_fields
    }


def _get_value(source: Any, field_name: str) -> Any:
    if isinstance(source, dict):
        return source.get(field_name)
    return getattr(source, field_name, None)


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not decimal_value.is_finite():
        return None
    return decimal_value
