"""Investment performance models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation
from typing import Any

from onecool_os.performance.enums import PerformanceStatus
from onecool_os.performance.validation import PerformanceError
from onecool_os.performance.validation import parse_enum
from onecool_os.performance.validation import parse_non_negative_decimal
from onecool_os.performance.validation import require_text


@dataclass(frozen=True)
class InvestmentPerformanceSnapshot:
    """Deterministic performance snapshot for one asset."""

    asset_id: str
    cost_basis: Decimal | str | int | float | None
    cost_currency: str | None
    market_value: Decimal | str | int | float | None
    market_currency: str | None
    unrealized_gain: Decimal | str | int | float | None
    unrealized_gain_percent: Decimal | str | int | float | None
    holding_days: int | None
    performance_status: PerformanceStatus | str
    warnings: list[str] | tuple[str, ...] | None
    generated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "asset_id",
            require_text(self.asset_id, "asset_id"),
        )
        for field_name in (
            "cost_basis",
            "market_value",
        ):
            object.__setattr__(
                self,
                field_name,
                parse_non_negative_decimal(
                    getattr(self, field_name),
                    field_name,
                ),
            )
        for field_name in (
            "unrealized_gain",
            "unrealized_gain_percent",
        ):
            object.__setattr__(
                self,
                field_name,
                _parse_optional_decimal(getattr(self, field_name), field_name),
            )
        if self.holding_days is not None:
            if not isinstance(self.holding_days, int) or self.holding_days < 0:
                raise PerformanceError(
                    "holding_days must be a non-negative integer."
                )
        object.__setattr__(
            self,
            "performance_status",
            parse_enum(
                PerformanceStatus,
                self.performance_status,
                "performance_status",
            ),
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(str(warning) for warning in self.warnings or ()),
        )
        if not isinstance(self.generated_at, datetime):
            raise PerformanceError("generated_at must be a datetime.")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "asset_id": self.asset_id,
            "cost_basis": _format_decimal(self.cost_basis),
            "cost_currency": self.cost_currency,
            "market_value": _format_decimal(self.market_value),
            "market_currency": self.market_currency,
            "unrealized_gain": _format_decimal(self.unrealized_gain),
            "unrealized_gain_percent": _format_decimal(
                self.unrealized_gain_percent,
            ),
            "holding_days": self.holding_days,
            "performance_status": self.performance_status.value,
            "warnings": list(self.warnings),
            "generated_at": self.generated_at.isoformat(),
        }


def _parse_optional_decimal(value: Any, field_name: str) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise PerformanceError(f"{field_name} must be a number.") from exc
    if not parsed.is_finite():
        raise PerformanceError(f"{field_name} must be finite.")
    return parsed


def _format_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}"
