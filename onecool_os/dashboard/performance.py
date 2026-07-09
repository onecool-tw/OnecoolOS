"""Investment performance dashboard presentation models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from onecool_os.dashboard.validation import parse_optional_datetime
from onecool_os.performance import InvestmentPerformanceSnapshot


@dataclass(frozen=True)
class PerformanceDashboard:
    """Presentation-only dashboard data for investment performance."""

    generated_at: datetime | str | None
    portfolio_performance: dict[str, Any]
    asset_performance_table: tuple[dict[str, Any], ...]
    summary: dict[str, Any]
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "generated_at",
            parse_optional_datetime(self.generated_at, "generated_at"),
        )
        object.__setattr__(
            self,
            "portfolio_performance",
            dict(self.portfolio_performance),
        )
        object.__setattr__(
            self,
            "asset_performance_table",
            tuple(dict(row) for row in self.asset_performance_table),
        )
        object.__setattr__(self, "summary", dict(self.summary))
        object.__setattr__(self, "warnings", tuple(self.warnings))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dashboard payload."""

        return {
            "generated_at": (
                self.generated_at.isoformat()
                if self.generated_at is not None
                else None
            ),
            "portfolio_performance": self.portfolio_performance,
            "asset_performance_table": [
                dict(row) for row in self.asset_performance_table
            ],
            "summary": self.summary,
            "warnings": list(self.warnings),
        }


class PerformanceDashboardBuilder:
    """Build presentation-only dashboard data from performance snapshots."""

    def build(
        self,
        *,
        performance_snapshots: tuple[InvestmentPerformanceSnapshot, ...]
        | list[InvestmentPerformanceSnapshot],
        collectible_assets: tuple[Any, ...] | list[Any] | None = None,
        generated_at: datetime | str | None = None,
    ) -> PerformanceDashboard:
        """Build dashboard data without recalculating performance."""

        snapshots = tuple(performance_snapshots or ())
        asset_map = _asset_map(collectible_assets)
        resolved_generated_at = generated_at or _generated_at(snapshots)
        rows = tuple(_asset_row(snapshot, asset_map) for snapshot in snapshots)
        warnings = _warnings(snapshots)

        return PerformanceDashboard(
            generated_at=resolved_generated_at,
            portfolio_performance=_portfolio_performance(snapshots),
            asset_performance_table=rows,
            summary=_summary(snapshots, rows),
            warnings=warnings,
        )


def _portfolio_performance(
    snapshots: tuple[InvestmentPerformanceSnapshot, ...],
) -> dict[str, Any]:
    total_cost = _sum_optional(snapshot.cost_basis for snapshot in snapshots)
    total_market_value = _sum_optional(
        snapshot.market_value for snapshot in snapshots
    )
    total_gain = _sum_optional(
        snapshot.unrealized_gain for snapshot in snapshots
    )
    total_gain_percent = (
        total_gain / total_cost
        if total_gain is not None
        and total_cost is not None
        and total_cost > Decimal("0")
        else None
    )

    return {
        "total_cost_basis": _format_decimal(total_cost),
        "total_market_value": _format_decimal(total_market_value),
        "total_unrealized_gain_loss": _format_decimal(total_gain),
        "total_unrealized_percent": _format_decimal(total_gain_percent),
        "performing_asset_count": sum(
            1
            for snapshot in snapshots
            if snapshot.cost_basis is not None
            and snapshot.market_value is not None
        ),
        "missing_valuation_count": sum(
            1 for snapshot in snapshots if snapshot.market_value is None
        ),
        "missing_cost_basis_count": sum(
            1 for snapshot in snapshots if snapshot.cost_basis is None
        ),
    }


def _asset_row(
    snapshot: InvestmentPerformanceSnapshot,
    asset_map: dict[str, Any],
) -> dict[str, Any]:
    asset = asset_map.get(snapshot.asset_id)
    return {
        "asset_id": snapshot.asset_id,
        "card_name": _card_name(asset, snapshot.asset_id),
        "player": _get_value(asset, "player"),
        "grade": _grade(asset),
        "cost_basis": _format_decimal(snapshot.cost_basis),
        "market_value": _format_decimal(snapshot.market_value),
        "unrealized_gain_loss": _format_decimal(snapshot.unrealized_gain),
        "unrealized_percent": _format_decimal(
            snapshot.unrealized_gain_percent,
        ),
        "holding_days": snapshot.holding_days,
        "performance_status": snapshot.performance_status.value,
        "warning_count": len(snapshot.warnings),
    }


def _summary(
    snapshots: tuple[InvestmentPerformanceSnapshot, ...],
    rows: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    gain_rows = [
        row for row in rows
        if row["unrealized_gain_loss"] is not None
    ]
    position_rows = [
        row for row in rows
        if row["market_value"] is not None
    ]
    dated_rows = [
        row for row in rows
        if row["holding_days"] is not None
    ]
    return {
        "top_gainers": _top_rows(gain_rows, "unrealized_gain_loss", reverse=True),
        "top_losers": _top_rows(gain_rows, "unrealized_gain_loss", reverse=False),
        "largest_position": _single_row(
            position_rows,
            "market_value",
            reverse=True,
        ),
        "oldest_holding": _single_row(dated_rows, "holding_days", reverse=True),
        "newest_holding": _single_row(dated_rows, "holding_days", reverse=False),
        "snapshot_count": len(snapshots),
    }


def _top_rows(
    rows: list[dict[str, Any]],
    field_name: str,
    *,
    reverse: bool,
) -> list[dict[str, Any]]:
    return [
        _summary_row(row)
        for row in sorted(
            rows,
            key=lambda row: (_decimal(row[field_name]), row["asset_id"]),
            reverse=reverse,
        )[:3]
    ]


def _single_row(
    rows: list[dict[str, Any]],
    field_name: str,
    *,
    reverse: bool,
) -> dict[str, Any] | None:
    if not rows:
        return None
    row = sorted(
        rows,
        key=lambda row: (_decimal(row[field_name]), row["asset_id"]),
        reverse=reverse,
    )[0]
    return _summary_row(row)


def _summary_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": row["asset_id"],
        "card_name": row["card_name"],
        "player": row["player"],
        "grade": row["grade"],
        "market_value": row["market_value"],
        "unrealized_gain_loss": row["unrealized_gain_loss"],
        "holding_days": row["holding_days"],
    }


def _warnings(
    snapshots: tuple[InvestmentPerformanceSnapshot, ...],
) -> tuple[str, ...]:
    warnings: list[str] = []
    for snapshot in snapshots:
        warnings.extend(snapshot.warnings)
    return tuple(dict.fromkeys(warnings))


def _asset_map(assets: tuple[Any, ...] | list[Any] | None) -> dict[str, Any]:
    return {
        str(_get_value(asset, "asset_id")): asset
        for asset in tuple(assets or ())
        if _get_value(asset, "asset_id") not in (None, "")
    }


def _generated_at(
    snapshots: tuple[InvestmentPerformanceSnapshot, ...],
) -> datetime | None:
    for snapshot in snapshots:
        return snapshot.generated_at
    return None


def _card_name(asset: Any, fallback: str) -> str:
    for field_name in ("name", "card_name", "title"):
        value = _get_value(asset, field_name)
        if value not in (None, ""):
            return str(value)

    parts = [
        _get_value(asset, "year"),
        _get_value(asset, "brand"),
        _get_value(asset, "set"),
        _get_value(asset, "card_number"),
    ]
    text = " ".join(str(part) for part in parts if part not in (None, ""))
    return text or fallback


def _grade(asset: Any) -> str | None:
    company = _get_value(asset, "grade_company") or _get_value(asset, "grader")
    grade = _get_value(asset, "grade")
    if company and grade:
        return f"{company} {grade}"
    if grade:
        return str(grade)
    return None


def _get_value(source: Any, field_name: str) -> Any:
    if source is None:
        return None
    if isinstance(source, dict):
        return source.get(field_name)
    return getattr(source, field_name, None)


def _sum_optional(values: Any) -> Decimal | None:
    parsed = tuple(value for value in values if value is not None)
    if not parsed:
        return None
    return sum(parsed, Decimal("0"))


def _format_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}"


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))
