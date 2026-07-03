"""Analytics snapshot models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from onecool_os.analytics.enums import RiskLevel
from onecool_os.analytics.validation import AnalyticsError
from onecool_os.analytics.validation import optional_text
from onecool_os.analytics.validation import parse_date
from onecool_os.analytics.validation import parse_enum
from onecool_os.analytics.validation import parse_optional_datetime
from onecool_os.analytics.validation import parse_optional_decimal
from onecool_os.analytics.validation import parse_optional_non_negative_decimal
from onecool_os.analytics.validation import parse_optional_risk_score
from onecool_os.analytics.validation import parse_tags
from onecool_os.analytics.validation import parse_weight_map
from onecool_os.analytics.validation import require_currency
from onecool_os.analytics.validation import require_text


@dataclass(frozen=True)
class AnalyticsSnapshot:
    """Immutable derived analytics snapshot for a portfolio."""

    snapshot_id: str
    portfolio_id: str
    base_currency: str
    snapshot_date: date | str
    created_at: datetime | str | None = None
    total_cost: Decimal | str | int | float | None = None
    total_market_value: Decimal | str | int | float | None = None
    unrealized_gain: Decimal | str | int | float | None = None
    unrealized_return: Decimal | str | int | float | None = None
    realized_gain: Decimal | str | int | float | None = None
    realized_return: Decimal | str | int | float | None = None
    asset_class_weights: dict[str, Decimal | str | int | float] | None = None
    currency_weights: dict[str, Decimal | str | int | float] | None = None
    account_weights: dict[str, Decimal | str | int | float] | None = None
    cash_inflow: Decimal | str | int | float | None = None
    cash_outflow: Decimal | str | int | float | None = None
    net_cash_flow: Decimal | str | int | float | None = None
    risk_score: Decimal | str | int | float | None = None
    risk_level: RiskLevel | str | None = None
    note: str | None = None
    tags: list[str] | tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            require_text(self.snapshot_id, "snapshot_id"),
        )
        object.__setattr__(
            self,
            "portfolio_id",
            require_text(self.portfolio_id, "portfolio_id"),
        )
        object.__setattr__(
            self,
            "base_currency",
            require_currency(self.base_currency),
        )
        object.__setattr__(
            self,
            "snapshot_date",
            self.snapshot_date
            if isinstance(self.snapshot_date, date)
            else parse_date(self.snapshot_date, "snapshot_date"),
        )
        object.__setattr__(
            self,
            "created_at",
            parse_optional_datetime(self.created_at, "created_at"),
        )
        for field_name in ("total_cost", "total_market_value"):
            object.__setattr__(
                self,
                field_name,
                parse_optional_non_negative_decimal(
                    getattr(self, field_name),
                    field_name,
                ),
            )
        for field_name in (
            "unrealized_gain",
            "unrealized_return",
            "realized_gain",
            "realized_return",
            "net_cash_flow",
        ):
            object.__setattr__(
                self,
                field_name,
                parse_optional_decimal(getattr(self, field_name), field_name),
            )
        for field_name in ("cash_inflow", "cash_outflow"):
            object.__setattr__(
                self,
                field_name,
                parse_optional_non_negative_decimal(
                    getattr(self, field_name),
                    field_name,
                ),
            )
        object.__setattr__(
            self,
            "asset_class_weights",
            parse_weight_map(self.asset_class_weights, "asset_class_weights"),
        )
        object.__setattr__(
            self,
            "currency_weights",
            parse_weight_map(self.currency_weights, "currency_weights"),
        )
        object.__setattr__(
            self,
            "account_weights",
            parse_weight_map(self.account_weights, "account_weights"),
        )
        object.__setattr__(self, "risk_score", parse_optional_risk_score(
            self.risk_score
        ))
        risk_level = (
            None
            if self.risk_level in (None, "")
            else parse_enum(RiskLevel, self.risk_level, "risk_level")
        )
        object.__setattr__(self, "risk_level", risk_level)
        object.__setattr__(self, "note", optional_text(self.note, "note"))
        object.__setattr__(self, "tags", parse_tags(self.tags))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "snapshot_id": self.snapshot_id,
            "portfolio_id": self.portfolio_id,
            "base_currency": self.base_currency,
            "snapshot_date": self.snapshot_date.isoformat(),
            "created_at": _format_optional_datetime(self.created_at),
            "total_cost": _format_optional_decimal(self.total_cost),
            "total_market_value": _format_optional_decimal(
                self.total_market_value
            ),
            "unrealized_gain": _format_optional_decimal(self.unrealized_gain),
            "unrealized_return": _format_optional_decimal(
                self.unrealized_return
            ),
            "realized_gain": _format_optional_decimal(self.realized_gain),
            "realized_return": _format_optional_decimal(self.realized_return),
            "asset_class_weights": _format_weight_map(
                self.asset_class_weights
            ),
            "currency_weights": _format_weight_map(self.currency_weights),
            "account_weights": _format_weight_map(self.account_weights),
            "cash_inflow": _format_optional_decimal(self.cash_inflow),
            "cash_outflow": _format_optional_decimal(self.cash_outflow),
            "net_cash_flow": _format_optional_decimal(self.net_cash_flow),
            "risk_score": _format_optional_decimal(self.risk_score),
            "risk_level": self.risk_level.value if self.risk_level else None,
            "note": self.note,
            "tags": list(self.tags),
        }


def _format_optional_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}"


def _format_optional_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _format_weight_map(weights: dict[str, Decimal]) -> dict[str, str]:
    return {
        label: _format_optional_decimal(weight) or "0.00"
        for label, weight in weights.items()
    }
