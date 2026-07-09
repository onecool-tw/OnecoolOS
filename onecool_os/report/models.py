"""Report models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from onecool_os.report.validation import parse_list
from onecool_os.report.validation import parse_non_negative_number
from onecool_os.report.validation import parse_optional_datetime
from onecool_os.report.validation import parse_optional_dict
from onecool_os.report.validation import require_text


@dataclass(frozen=True)
class CollectibleDailyRadarReport:
    """Structured end-user Daily Radar Report for Collectible Radar."""

    report_id: str
    generated_at: datetime | str | None
    reference_datetime: datetime | str | None
    total_cards: int
    total_market_value: int | float
    total_cost_basis: int | float
    unrealized_gain_loss: int | float
    valuation_coverage: int | float
    market_quality: str | None
    confidence_summary: dict[str, Any] | None
    agreement_summary: dict[str, Any] | None
    liquidity_summary: dict[str, Any] | None
    new_signals: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None
    resolved_signals: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None
    changed_signals: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None
    escalated_signals: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None
    trend_direction: str | None
    trend_strength: str | None
    trend_summary: list[str] | tuple[str, ...] | None
    ready_for_review: int
    needs_review: int
    blocked: int
    performance_summary: dict[str, Any] | None
    top_movers: dict[str, Any] | None
    warnings: list[str] | tuple[str, ...] | None
    dashboard_snapshot_id: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "report_id",
            require_text(self.report_id, "report_id"),
        )
        object.__setattr__(
            self,
            "generated_at",
            parse_optional_datetime(self.generated_at, "generated_at"),
        )
        object.__setattr__(
            self,
            "reference_datetime",
            parse_optional_datetime(
                self.reference_datetime,
                "reference_datetime",
            ),
        )
        for field_name in (
            "total_cards",
            "total_market_value",
            "total_cost_basis",
            "valuation_coverage",
            "ready_for_review",
            "needs_review",
            "blocked",
        ):
            object.__setattr__(
                self,
                field_name,
                parse_non_negative_number(
                    getattr(self, field_name),
                    field_name,
                ),
            )
        if not isinstance(self.unrealized_gain_loss, (int, float)):
            raise TypeError("unrealized_gain_loss must be numeric.")
        for field_name in (
            "confidence_summary",
            "agreement_summary",
            "liquidity_summary",
            "performance_summary",
            "top_movers",
        ):
            object.__setattr__(
                self,
                field_name,
                parse_optional_dict(getattr(self, field_name), field_name),
            )
        for field_name in (
            "new_signals",
            "resolved_signals",
            "changed_signals",
            "escalated_signals",
            "trend_summary",
            "warnings",
        ):
            object.__setattr__(
                self,
                field_name,
                parse_list(getattr(self, field_name), field_name),
            )

    def section_order(self) -> tuple[str, ...]:
        """Return fixed report section order."""

        return (
            "collection_summary",
            "market_summary",
            "todays_changes",
            "timeline_summary",
            "review_queue",
            "performance_summary",
            "top_movers",
            "warnings",
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe report."""

        return {
            "report_id": self.report_id,
            "generated_at": _format_datetime(self.generated_at),
            "reference_datetime": _format_datetime(self.reference_datetime),
            "sections": {
                "collection_summary": {
                    "total_cards": self.total_cards,
                    "total_market_value": self.total_market_value,
                    "total_cost_basis": self.total_cost_basis,
                    "unrealized_gain_loss": self.unrealized_gain_loss,
                    "valuation_coverage": self.valuation_coverage,
                },
                "market_summary": {
                    "market_quality": self.market_quality,
                    "confidence_summary": self.confidence_summary,
                    "agreement_summary": self.agreement_summary,
                    "liquidity_summary": self.liquidity_summary,
                },
                "todays_changes": {
                    "new_signals": list(self.new_signals),
                    "resolved_signals": list(self.resolved_signals),
                    "changed_signals": list(self.changed_signals),
                    "escalated_signals": list(self.escalated_signals),
                },
                "timeline_summary": {
                    "trend_direction": self.trend_direction,
                    "trend_strength": self.trend_strength,
                    "trend_summary": list(self.trend_summary),
                },
                "review_queue": {
                    "ready_for_review": self.ready_for_review,
                    "needs_review": self.needs_review,
                    "blocked": self.blocked,
                },
                "performance_summary": self.performance_summary or {},
                "top_movers": self.top_movers or {},
                "warnings": {
                    "warnings": list(self.warnings),
                },
            },
            "metadata": {
                "dashboard_snapshot_id": self.dashboard_snapshot_id,
            },
        }


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
