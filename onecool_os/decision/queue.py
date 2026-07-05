"""Decision Queue foundation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from typing import TYPE_CHECKING

from onecool_os.decision.validation import DecisionError
from onecool_os.decision.validation import parse_optional_datetime
from onecool_os.decision.validation import parse_optional_dict
from onecool_os.decision.validation import require_text

if TYPE_CHECKING:
    from onecool_os.report.models import CollectibleDailyRadarReport


class DecisionQueuePriority(StrEnum):
    """Decision Queue priority levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class DecisionQueueItem:
    """A prioritized review item, not a recommendation."""

    item_id: str
    priority: DecisionQueuePriority | str
    title: str
    description: str
    source: str
    related_asset_id: str | None = None
    warnings: list[str] | tuple[str, ...] | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "item_id",
            require_text(self.item_id, "item_id"),
        )
        object.__setattr__(
            self,
            "priority",
            DecisionQueuePriority(str(self.priority).upper()),
        )
        object.__setattr__(self, "title", require_text(self.title, "title"))
        object.__setattr__(
            self,
            "description",
            require_text(self.description, "description"),
        )
        object.__setattr__(self, "source", require_text(self.source, "source"))
        object.__setattr__(
            self,
            "related_asset_id",
            str(self.related_asset_id) if self.related_asset_id else None,
        )
        object.__setattr__(self, "warnings", tuple(self.warnings or ()))
        object.__setattr__(
            self,
            "metadata",
            parse_optional_dict(self.metadata, "metadata"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe queue item."""

        return {
            "item_id": self.item_id,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "related_asset_id": self.related_asset_id,
            "warnings": list(self.warnings),
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class DecisionQueue:
    """Prioritized review queue generated from deterministic outputs."""

    queue_id: str
    generated_at: datetime | str | None
    reference_datetime: datetime | str | None
    critical: list[DecisionQueueItem] | tuple[DecisionQueueItem, ...] | None
    high: list[DecisionQueueItem] | tuple[DecisionQueueItem, ...] | None
    medium: list[DecisionQueueItem] | tuple[DecisionQueueItem, ...] | None
    low: list[DecisionQueueItem] | tuple[DecisionQueueItem, ...] | None
    total_items: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    report_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "queue_id",
            require_text(self.queue_id, "queue_id"),
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
        for field_name in ("critical", "high", "medium", "low"):
            object.__setattr__(
                self,
                field_name,
                _item_tuple(getattr(self, field_name), field_name),
            )
        expected_counts = {
            "critical_count": len(self.critical),
            "high_count": len(self.high),
            "medium_count": len(self.medium),
            "low_count": len(self.low),
        }
        for field_name, expected in expected_counts.items():
            value = getattr(self, field_name)
            if value != expected:
                raise DecisionError(
                    f"{field_name} must equal {expected}."
                )
        expected_total = sum(expected_counts.values())
        if self.total_items != expected_total:
            raise DecisionError(f"total_items must equal {expected_total}.")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe queue."""

        return {
            "queue_id": self.queue_id,
            "generated_at": _format_datetime(self.generated_at),
            "reference_datetime": _format_datetime(self.reference_datetime),
            "priority_groups": {
                "critical": _items_to_dict(self.critical),
                "high": _items_to_dict(self.high),
                "medium": _items_to_dict(self.medium),
                "low": _items_to_dict(self.low),
            },
            "statistics": {
                "total_items": self.total_items,
                "critical_count": self.critical_count,
                "high_count": self.high_count,
                "medium_count": self.medium_count,
                "low_count": self.low_count,
            },
            "metadata": {
                "report_id": self.report_id,
            },
        }


class DecisionQueueBuilder:
    """Build a prioritized review queue from a Daily Radar Report."""

    def build(
        self,
        report: CollectibleDailyRadarReport,
    ) -> DecisionQueue:
        """Convert warnings and review items into queue entries."""

        from onecool_os.report.models import CollectibleDailyRadarReport

        if not isinstance(report, CollectibleDailyRadarReport):
            raise DecisionError(
                "report must be a CollectibleDailyRadarReport."
            )
        items = _items_from_report(report)
        critical = _filter_priority(items, DecisionQueuePriority.CRITICAL)
        high = _filter_priority(items, DecisionQueuePriority.HIGH)
        medium = _filter_priority(items, DecisionQueuePriority.MEDIUM)
        low = _filter_priority(items, DecisionQueuePriority.LOW)
        return DecisionQueue(
            queue_id=f"decision-queue:{report.report_id}",
            generated_at=report.generated_at,
            reference_datetime=report.reference_datetime,
            critical=critical,
            high=high,
            medium=medium,
            low=low,
            total_items=len(items),
            critical_count=len(critical),
            high_count=len(high),
            medium_count=len(medium),
            low_count=len(low),
            report_id=report.report_id,
        )


def _items_from_report(
    report: CollectibleDailyRadarReport,
) -> tuple[DecisionQueueItem, ...]:
    items: list[DecisionQueueItem] = []
    related_asset_id = _asset_id_from_report(report)
    for warning in report.warnings:
        priority = _priority_for_text(warning)
        items.append(
            DecisionQueueItem(
                item_id=f"warning:{_slug(warning)}",
                priority=priority,
                title=str(warning),
                description=f"Review warning: {warning}.",
                source="daily_radar_report.warning",
                related_asset_id=related_asset_id,
                warnings=[str(warning)],
                metadata={"classification_only": True},
            )
        )
    if report.blocked:
        items.append(
            DecisionQueueItem(
                item_id="review:blocking-items",
                priority=DecisionQueuePriority.CRITICAL,
                title="Blocked Review Items",
                description="One or more report items are blocked.",
                source="daily_radar_report.review_queue",
                related_asset_id=related_asset_id,
                metadata={"blocked": report.blocked},
            )
        )
    if report.needs_review:
        items.append(
            DecisionQueueItem(
                item_id="review:needs-review",
                priority=DecisionQueuePriority.MEDIUM,
                title="Needs Review",
                description="One or more report items need manual review.",
                source="daily_radar_report.review_queue",
                related_asset_id=related_asset_id,
                metadata={"needs_review": report.needs_review},
            )
        )
    for signal in report.new_signals + report.changed_signals:
        title = str(signal.get("title") or "Radar Signal")
        priority = _priority_for_text(title)
        items.append(
            DecisionQueueItem(
                item_id=f"signal:{_slug(title)}",
                priority=priority,
                title=title,
                description=f"Radar signal for review: {title}.",
                source="daily_radar_report.radar_signal",
                related_asset_id=related_asset_id,
                metadata={
                    "signal": dict(signal),
                    "classification_only": True,
                },
            )
        )
    return tuple(_deduplicate_items(items))


def _priority_for_text(text: str) -> DecisionQueuePriority:
    normalized = text.lower()
    if "missing primary market" in normalized or "source conflict" in normalized:
        return DecisionQueuePriority.CRITICAL
    if "blocked" in normalized:
        return DecisionQueuePriority.CRITICAL
    if "low confidence" in normalized or "stale valuation" in normalized:
        return DecisionQueuePriority.HIGH
    if "stale market" in normalized or "stale data" in normalized:
        return DecisionQueuePriority.HIGH
    if "low liquidity" in normalized or "missing validation" in normalized:
        return DecisionQueuePriority.MEDIUM
    if "coverage improvement" in normalized or "coverage improved" in normalized:
        return DecisionQueuePriority.LOW
    if "improved" in normalized or "resolved" in normalized:
        return DecisionQueuePriority.LOW
    return DecisionQueuePriority.LOW


def _asset_id_from_report(report: CollectibleDailyRadarReport) -> str | None:
    dashboard_id = report.dashboard_snapshot_id
    if not dashboard_id:
        return None
    if ":" in dashboard_id:
        return dashboard_id.rsplit(":", 1)[-1]
    return dashboard_id


def _filter_priority(
    items: tuple[DecisionQueueItem, ...],
    priority: DecisionQueuePriority,
) -> tuple[DecisionQueueItem, ...]:
    return tuple(item for item in items if item.priority == priority)


def _deduplicate_items(
    items: list[DecisionQueueItem],
) -> tuple[DecisionQueueItem, ...]:
    deduped: dict[str, DecisionQueueItem] = {}
    for item in items:
        deduped.setdefault(item.item_id, item)
    return tuple(deduped[key] for key in sorted(deduped))


def _item_tuple(value: Any, field_name: str) -> tuple[DecisionQueueItem, ...]:
    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise DecisionError(f"{field_name} must be a list or tuple.")
    items = tuple(value)
    for item in items:
        if not isinstance(item, DecisionQueueItem):
            raise DecisionError(f"{field_name} must contain queue items.")
    return items


def _items_to_dict(
    items: tuple[DecisionQueueItem, ...],
) -> list[dict[str, Any]]:
    return [item.to_dict() for item in items]


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _slug(value: str) -> str:
    return value.strip().lower().replace(" ", "-").replace("_", "-")
