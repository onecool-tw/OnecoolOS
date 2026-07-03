"""Risk Engine foundation."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from onecool_os.business_logic.calculators import BaseCalculator
from onecool_os.business_logic.context import BusinessLogicContext
from onecool_os.business_logic.evaluators import BaseEvaluator
from onecool_os.business_logic.policies import BasePolicy
from onecool_os.business_logic.results import BusinessLogicResult
from onecool_os.business_logic.results import SignalResult


class RiskEngine(BaseCalculator, BaseEvaluator):
    """Assess deterministic portfolio risk dimensions from context data."""

    default_rules = {
        "concentration_threshold": Decimal("0.50"),
        "cash_minimum_weight": Decimal("0.05"),
        "minimum_categories": 2,
        "illiquid_categories": ("Collectible", "Real Estate"),
    }
    category_names = {
        "CASH": "Cash",
        "STOCK": "Equity",
        "ETF": "ETF",
        "MUTUAL_FUND": "Mutual Fund",
        "REAL_ESTATE": "Real Estate",
        "SPORTS_CARD": "Collectible",
        "COLLECTIBLE": "Collectible",
        "CRYPTO": "Crypto",
        "BOND": "Bond",
    }

    def __init__(self, policy: BasePolicy | None = None) -> None:
        super().__init__(engine_name="risk", engine_version="v1")
        object.__setattr__(self, "policy", policy)

    def supports(self, context: BusinessLogicContext) -> bool:
        """Return whether this engine can inspect the context."""

        return isinstance(context, BusinessLogicContext)

    def calculate(
        self,
        context: BusinessLogicContext,
    ) -> BusinessLogicResult:
        """Calculate deterministic risk dimensions."""

        assessment = _assess_context(context, self._rules())
        payload = {
            "risk_score": assessment["risk_score"],
            "dimensions": assessment["dimensions"],
        }
        return BusinessLogicResult(
            result_id=f"{context.context_id}-risk",
            engine_name=self.engine_name,
            engine_version=self.engine_version,
            metric_type="RISK",
            value=assessment["risk_score"],
            currency=context.base_currency,
            payload=payload,
            confidence="MEDIUM",
            note="Deterministic risk assessment from business logic context.",
            tags=["risk", "business_logic"],
        )

    def evaluate(
        self,
        context: BusinessLogicContext,
    ) -> tuple[SignalResult, ...]:
        """Return deterministic risk signals triggered by the context."""

        assessment = _assess_context(context, self._rules())
        signals = []
        for signal in assessment["signals"]:
            signals.append(
                SignalResult(
                    signal_id=f"{context.context_id}-risk-{signal['type']}",
                    engine_name=self.engine_name,
                    engine_version=self.engine_version,
                    signal_type=signal["type"],
                    severity=signal["severity"],
                    message=signal["message"],
                    payload=signal["payload"],
                    note="Deterministic risk signal.",
                    tags=["risk", "business_logic"],
                )
            )
        return tuple(signals)

    def _rules(self) -> dict[str, Any]:
        rules = dict(self.default_rules)
        if self.policy is not None and self.policy.rules is not None:
            rules.update(self.policy.rules)
        rules["concentration_threshold"] = _decimal_or_default(
            rules.get("concentration_threshold"),
            self.default_rules["concentration_threshold"],
        )
        rules["cash_minimum_weight"] = _decimal_or_default(
            rules.get("cash_minimum_weight"),
            self.default_rules["cash_minimum_weight"],
        )
        rules["minimum_categories"] = int(
            rules.get("minimum_categories")
            or self.default_rules["minimum_categories"]
        )
        rules["illiquid_categories"] = tuple(
            rules.get("illiquid_categories")
            or self.default_rules["illiquid_categories"]
        )
        return rules


def _assess_context(
    context: BusinessLogicContext,
    rules: dict[str, Any],
) -> dict[str, Any]:
    holdings = tuple(_holdings_from_source(context.ledger_data))
    transactions = tuple(_transactions_from_source(context.ledger_data))
    valuations = tuple(_valuations_from_source(context.valuation_data))
    categories = _category_totals(holdings)
    total_value = sum(categories.values(), Decimal("0"))
    weights = _category_weights(categories, total_value)
    dimensions = {
        "concentration": _concentration_dimension(
            holdings,
            total_value,
            rules,
        ),
        "liquidity": _liquidity_dimension(weights, rules),
        "cash_ratio": _cash_ratio_dimension(weights, rules),
        "diversification": _diversification_dimension(categories, rules),
        "valuation": "ok" if valuations else "missing",
        "history": "ok" if transactions else "missing",
    }
    signals = _signals(dimensions, holdings, total_value, rules)
    return {
        "risk_score": _risk_score(dimensions),
        "dimensions": dimensions,
        "signals": signals,
    }


def _holdings_from_source(source: Any) -> tuple[Any, ...]:
    if source in (None, ""):
        return ()
    if hasattr(source, "holdings"):
        return tuple(getattr(source, "holdings") or ())
    if hasattr(source, "positions"):
        return tuple(getattr(source, "positions") or ())
    if isinstance(source, dict):
        for key in ("holdings", "positions"):
            values = source.get(key)
            if values:
                return tuple(values)
    if isinstance(source, (list, tuple)):
        return tuple(source)
    return ()


def _transactions_from_source(source: Any) -> tuple[Any, ...]:
    if source in (None, ""):
        return ()
    if hasattr(source, "transactions"):
        return tuple(getattr(source, "transactions") or ())
    if isinstance(source, dict):
        return tuple(source.get("transactions") or ())
    return ()


def _valuations_from_source(source: Any) -> tuple[Any, ...]:
    if source in (None, ""):
        return ()
    if hasattr(source, "valuations"):
        return tuple(getattr(source, "valuations") or ())
    if isinstance(source, dict):
        return tuple(source.get("valuations") or ())
    if isinstance(source, (list, tuple)):
        return tuple(source)
    return ()


def _category_totals(holdings: tuple[Any, ...]) -> dict[str, Decimal]:
    categories: dict[str, Decimal] = {}
    for holding in holdings:
        category = _category_name(_asset_type(holding))
        value = _holding_value(holding)
        categories[category] = categories.get(category, Decimal("0")) + value
    return {
        category: categories[category]
        for category in sorted(categories)
    }


def _category_weights(
    categories: dict[str, Decimal],
    total_value: Decimal,
) -> dict[str, Decimal]:
    if total_value <= Decimal("0"):
        return {category: Decimal("0") for category in categories}
    return {
        category: value / total_value
        for category, value in categories.items()
    }


def _concentration_dimension(
    holdings: tuple[Any, ...],
    total_value: Decimal,
    rules: dict[str, Any],
) -> str:
    if not holdings or total_value <= Decimal("0"):
        return "unknown"
    threshold = rules["concentration_threshold"]
    largest_weight = max(
        (_holding_value(holding) / total_value for holding in holdings),
        default=Decimal("0"),
    )
    if largest_weight > threshold:
        return "warning"
    return "ok"


def _liquidity_dimension(
    weights: dict[str, Decimal],
    rules: dict[str, Any],
) -> str:
    illiquid_weight = sum(
        weights.get(category, Decimal("0"))
        for category in rules["illiquid_categories"]
    )
    if illiquid_weight > Decimal("0.50"):
        return "warning"
    return "ok"


def _cash_ratio_dimension(
    weights: dict[str, Decimal],
    rules: dict[str, Any],
) -> str:
    if not weights:
        return "missing"
    if weights.get("Cash", Decimal("0")) < rules["cash_minimum_weight"]:
        return "warning"
    return "ok"


def _diversification_dimension(
    categories: dict[str, Decimal],
    rules: dict[str, Any],
) -> str:
    active_categories = tuple(
        category for category, value in categories.items()
        if value > Decimal("0")
    )
    if len(active_categories) < rules["minimum_categories"]:
        return "warning"
    return "ok"


def _signals(
    dimensions: dict[str, str],
    holdings: tuple[Any, ...],
    total_value: Decimal,
    rules: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    signals = []
    if dimensions["valuation"] == "missing":
        signals.append(
            _signal(
                "missing_valuation",
                "HIGH",
                "No valuation data is available.",
                {},
            )
        )
    if dimensions["cash_ratio"] in {"missing", "warning"}:
        signals.append(
            _signal(
                "cash_ratio",
                "MEDIUM",
                "No sufficient cash position is available.",
                {"minimum_weight": str(rules["cash_minimum_weight"])},
            )
        )
    concentration = _largest_holding_weight(holdings, total_value)
    if concentration > rules["concentration_threshold"]:
        signals.append(
            _signal(
                "concentration",
                "HIGH",
                "Single asset concentration exceeds threshold.",
                {
                    "largest_weight": str(concentration),
                    "threshold": str(rules["concentration_threshold"]),
                },
            )
        )
    if dimensions["diversification"] == "warning":
        signals.append(
            _signal(
                "diversification",
                "MEDIUM",
                "Portfolio has limited category diversification.",
                {"minimum_categories": rules["minimum_categories"]},
            )
        )
    if dimensions["history"] == "missing":
        signals.append(
            _signal(
                "missing_ledger_history",
                "HIGH",
                "No ledger transaction history is available.",
                {},
            )
        )
    return tuple(signals)


def _signal(
    signal_type: str,
    severity: str,
    message: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": signal_type,
        "severity": severity,
        "message": message,
        "payload": payload,
    }


def _risk_score(dimensions: dict[str, str]) -> Decimal:
    score = Decimal("0")
    for status in dimensions.values():
        if status == "warning":
            score += Decimal("15")
        if status == "missing":
            score += Decimal("20")
        if status == "unknown":
            score += Decimal("10")
    return min(score, Decimal("100"))


def _largest_holding_weight(
    holdings: tuple[Any, ...],
    total_value: Decimal,
) -> Decimal:
    if not holdings or total_value <= Decimal("0"):
        return Decimal("0")
    return max(
        (_holding_value(holding) / total_value for holding in holdings),
        default=Decimal("0"),
    )


def _asset_type(holding: Any) -> str:
    asset_type = _get_value(holding, "asset_type")
    if asset_type is not None:
        return str(asset_type).upper()
    asset = _get_value(holding, "asset")
    if asset is not None:
        asset_type = _get_value(asset, "asset_type")
        if asset_type is not None:
            return str(asset_type).upper()
    return "OTHER"


def _category_name(asset_type: str) -> str:
    normalized_type = asset_type.strip().upper()
    if normalized_type in RiskEngine.category_names:
        return RiskEngine.category_names[normalized_type]
    return normalized_type.replace("_", " ").title()


def _holding_value(holding: Any) -> Decimal:
    for field_name in (
        "market_value",
        "value",
        "estimated_value",
        "current_value",
    ):
        value = _decimal_or_none(_get_value(holding, field_name))
        if value is not None:
            return max(value, Decimal("0"))
    return Decimal("0")


def _get_value(source: Any, field_name: str) -> Any:
    if isinstance(source, dict):
        return source.get(field_name)
    return getattr(source, field_name, None)


def _decimal_or_default(value: Any, default: Decimal) -> Decimal:
    decimal_value = _decimal_or_none(value)
    if decimal_value is None:
        return default
    return decimal_value


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
