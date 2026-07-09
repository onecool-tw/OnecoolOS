"""Collectible Radar OFAI Context foundation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from typing import TYPE_CHECKING

from onecool_os.ofai.validation import OFAIError
from onecool_os.ofai.validation import parse_optional_datetime
from onecool_os.ofai.validation import require_text

if TYPE_CHECKING:
    from onecool_os.decision.queue import DecisionQueue
    from onecool_os.decision.queue import DecisionQueueItem
    from onecool_os.report.models import CollectibleDailyRadarReport


@dataclass(frozen=True)
class CollectibleOFAIContext:
    """Structured deterministic context for future OFAI consumption."""

    context_id: str
    generated_at: datetime | str | None
    reference_datetime: datetime | str | None
    collection_summary: dict[str, Any] | None
    market_summary: dict[str, Any] | None
    radar_summary: dict[str, Any] | None
    timeline_summary: dict[str, Any] | None
    decision_queue_summary: dict[str, Any] | None
    performance_overview: dict[str, Any] | None
    performance_review_priorities: dict[str, Any] | None
    top_movers: dict[str, Any] | None
    review_targets: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None
    warnings: list[str] | tuple[str, ...] | None
    report_id: str | None
    decision_queue_id: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "context_id",
            require_text(self.context_id, "context_id"),
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
            "collection_summary",
            "market_summary",
            "radar_summary",
            "timeline_summary",
            "decision_queue_summary",
            "performance_overview",
            "performance_review_priorities",
            "top_movers",
        ):
            object.__setattr__(
                self,
                field_name,
                _dict_or_empty(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "review_targets",
            _dict_tuple(self.review_targets, "review_targets"),
        )
        object.__setattr__(
            self,
            "warnings",
            _text_tuple(self.warnings, "warnings"),
        )
        object.__setattr__(
            self,
            "report_id",
            str(self.report_id) if self.report_id else None,
        )
        object.__setattr__(
            self,
            "decision_queue_id",
            str(self.decision_queue_id) if self.decision_queue_id else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe OFAI context."""

        return {
            "context_id": self.context_id,
            "generated_at": _format_datetime(self.generated_at),
            "reference_datetime": _format_datetime(self.reference_datetime),
            "collection_summary": self.collection_summary,
            "market_summary": self.market_summary,
            "radar_summary": self.radar_summary,
            "timeline_summary": self.timeline_summary,
            "decision_queue_summary": self.decision_queue_summary,
            "performance_overview": self.performance_overview,
            "performance_review_priorities": self.performance_review_priorities,
            "top_movers": self.top_movers,
            "review_targets": list(self.review_targets),
            "warnings": list(self.warnings),
            "metadata": {
                "report_id": self.report_id,
                "decision_queue_id": self.decision_queue_id,
            },
        }


class CollectibleOFAIContextBuilder:
    """Build deterministic OFAI context from report and queue outputs."""

    def build(
        self,
        report: CollectibleDailyRadarReport,
        decision_queue: DecisionQueue,
    ) -> CollectibleOFAIContext:
        """Prepare structured context without recommendations."""

        from onecool_os.decision.queue import DecisionQueue
        from onecool_os.report.models import CollectibleDailyRadarReport

        if not isinstance(report, CollectibleDailyRadarReport):
            raise OFAIError(
                "report must be a CollectibleDailyRadarReport."
            )
        if not isinstance(decision_queue, DecisionQueue):
            raise OFAIError("decision_queue must be a DecisionQueue.")
        return CollectibleOFAIContext(
            context_id=f"collectible-ofai:{report.report_id}",
            generated_at=report.generated_at,
            reference_datetime=report.reference_datetime,
            collection_summary=_collection_summary(report),
            market_summary=_market_summary(report),
            radar_summary=_radar_summary(report),
            timeline_summary=_timeline_summary(report),
            decision_queue_summary=_decision_queue_summary(decision_queue),
            performance_overview=_performance_overview(report),
            performance_review_priorities=_performance_review_priorities(
                decision_queue,
            ),
            top_movers=dict(report.top_movers),
            review_targets=_review_targets(decision_queue),
            warnings=report.warnings,
            report_id=report.report_id,
            decision_queue_id=decision_queue.queue_id,
        )


def _collection_summary(
    report: CollectibleDailyRadarReport,
) -> dict[str, Any]:
    return {
        "total_cards": report.total_cards,
        "total_market_value": report.total_market_value,
        "total_cost_basis": report.total_cost_basis,
        "unrealized_gain_loss": report.unrealized_gain_loss,
        "valuation_coverage": report.valuation_coverage,
    }


def _market_summary(report: CollectibleDailyRadarReport) -> dict[str, Any]:
    return {
        "market_quality": report.market_quality,
        "confidence_summary": dict(report.confidence_summary),
        "agreement_summary": dict(report.agreement_summary),
        "liquidity_summary": dict(report.liquidity_summary),
    }


def _radar_summary(report: CollectibleDailyRadarReport) -> dict[str, Any]:
    return {
        "new_signals": list(report.new_signals),
        "resolved_signals": list(report.resolved_signals),
        "changed_signals": list(report.changed_signals),
        "escalated_signals": list(report.escalated_signals),
    }


def _timeline_summary(report: CollectibleDailyRadarReport) -> dict[str, Any]:
    return {
        "trend_direction": report.trend_direction,
        "trend_strength": report.trend_strength,
        "trend_summary": list(report.trend_summary),
    }


def _decision_queue_summary(queue: DecisionQueue) -> dict[str, Any]:
    return {
        "total_items": queue.total_items,
        "critical_count": queue.critical_count,
        "high_count": queue.high_count,
        "medium_count": queue.medium_count,
        "low_count": queue.low_count,
    }


def _performance_overview(report: CollectibleDailyRadarReport) -> dict[str, Any]:
    summary = report.performance_summary or {}
    return {
        "total_cost_basis": summary.get("total_cost_basis"),
        "total_market_value": summary.get("total_market_value"),
        "unrealized_gain_loss": summary.get("total_unrealized_gain_loss"),
        "unrealized_percent": summary.get("total_unrealized_percent"),
        "performing_assets": summary.get("performing_assets", 0),
    }


def _performance_review_priorities(queue: DecisionQueue) -> dict[str, Any]:
    return {
        "critical": _performance_targets(queue.critical),
        "high": _performance_targets(queue.high),
        "medium": _performance_targets(queue.medium),
        "low": _performance_targets(queue.low),
    }


def _performance_targets(
    items: tuple[DecisionQueueItem, ...],
) -> list[dict[str, Any]]:
    return [
        _review_target(item)
        for item in items
        if item.source == "daily_radar_report.performance"
    ]


def _review_targets(queue: DecisionQueue) -> tuple[dict[str, Any], ...]:
    ordered_items = (
        list(queue.critical)
        + list(queue.high)
        + list(queue.medium)
        + list(queue.low)
    )
    return tuple(_review_target(item) for item in ordered_items)


def _review_target(item: DecisionQueueItem) -> dict[str, Any]:
    return {
        "item_id": item.item_id,
        "priority": item.priority.value,
        "title": item.title,
        "description": item.description,
        "source": item.source,
        "related_asset_id": item.related_asset_id,
        "warnings": list(item.warnings),
        "metadata": dict(item.metadata),
    }


def _dict_or_empty(value: Any, field_name: str) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise OFAIError(f"{field_name} must be a dictionary.")
    return dict(value)


def _dict_tuple(value: Any, field_name: str) -> tuple[dict[str, Any], ...]:
    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise OFAIError(f"{field_name} must be a list or tuple.")
    return tuple(_dict_or_empty(item, field_name) for item in value)


def _text_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise OFAIError(f"{field_name} must be a list or tuple.")
    return tuple(require_text(item, field_name) for item in value)


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
