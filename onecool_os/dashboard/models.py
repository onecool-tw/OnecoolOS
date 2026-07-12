"""Dashboard display-only view models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from onecool_os.dashboard.validation import DashboardError
from onecool_os.dashboard.validation import optional_text
from onecool_os.dashboard.validation import parse_optional_datetime
from onecool_os.dashboard.validation import parse_optional_dict
from onecool_os.dashboard.validation import parse_tags
from onecool_os.dashboard.validation import require_currency
from onecool_os.dashboard.validation import require_text


@dataclass(frozen=True)
class DashboardSection:
    """Display-only dashboard section."""

    section_id: str
    title: str
    content: dict[str, Any] | None = None
    source_service: str | None = None
    generated_at: datetime | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "section_id",
            require_text(self.section_id, "section_id"),
        )
        object.__setattr__(self, "title", require_text(self.title, "title"))
        object.__setattr__(
            self,
            "content",
            parse_optional_dict(self.content, "content"),
        )
        object.__setattr__(
            self,
            "source_service",
            optional_text(self.source_service, "source_service"),
        )
        object.__setattr__(
            self,
            "generated_at",
            parse_optional_datetime(self.generated_at, "generated_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe section payload."""

        return {
            "section_id": self.section_id,
            "title": self.title,
            "content": self.content,
            "source_service": self.source_service,
            "generated_at": _format_optional_datetime(self.generated_at),
        }


@dataclass(frozen=True)
class DashboardView:
    """Display-only dashboard view."""

    dashboard_id: str
    dashboard_name: str
    base_currency: str
    generated_at: datetime | str | None = None
    portfolio_summary: DashboardSection | None = None
    analytics_summary: DashboardSection | None = None
    valuation_summary: DashboardSection | None = None
    ledger_summary: DashboardSection | None = None
    note: str | None = None
    tags: list[str] | tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dashboard_id",
            require_text(self.dashboard_id, "dashboard_id"),
        )
        object.__setattr__(
            self,
            "dashboard_name",
            require_text(self.dashboard_name, "dashboard_name"),
        )
        object.__setattr__(self, "base_currency", require_currency(
            self.base_currency
        ))
        object.__setattr__(
            self,
            "generated_at",
            parse_optional_datetime(self.generated_at, "generated_at"),
        )
        object.__setattr__(self, "note", optional_text(self.note, "note"))
        object.__setattr__(self, "tags", parse_tags(self.tags))
        self._validate_unique_sections()

    def sections(self) -> tuple[DashboardSection, ...]:
        """Return available sections in display order."""

        return tuple(
            section
            for section in (
                self.portfolio_summary,
                self.analytics_summary,
                self.valuation_summary,
                self.ledger_summary,
            )
            if section is not None
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dashboard payload."""

        return {
            "dashboard_id": self.dashboard_id,
            "dashboard_name": self.dashboard_name,
            "base_currency": self.base_currency,
            "generated_at": _format_optional_datetime(self.generated_at),
            "sections": [section.to_dict() for section in self.sections()],
            "note": self.note,
            "tags": list(self.tags),
        }

    def _validate_unique_sections(self) -> None:
        seen: set[str] = set()
        for section in self.sections():
            if section.section_id in seen:
                raise DashboardError(
                    f"Duplicate section_id: {section.section_id}"
                )
            seen.add(section.section_id)


def _format_optional_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


@dataclass(frozen=True)
class DashboardSnapshot:
    """Onecool Collection Dashboard 2.0 display snapshot."""

    snapshot_id: str
    portfolio_summary: dict[str, Any]
    nav_summary: dict[str, Any]
    coverage: dict[str, Any]
    research: dict[str, Any]
    evidence: dict[str, Any]
    valuation: dict[str, Any]
    top_holdings: tuple[dict[str, Any], ...] | list[dict[str, Any]]
    missing_valuation: tuple[dict[str, Any], ...] | list[dict[str, Any]]
    latest_updates: tuple[dict[str, Any], ...] | list[dict[str, Any]]
    warnings: tuple[dict[str, Any], ...] | list[dict[str, Any]]
    reference_datetime: datetime | str
    generated_at: datetime | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            require_text(self.snapshot_id, "snapshot_id"),
        )
        for field_name in (
            "portfolio_summary",
            "nav_summary",
            "coverage",
            "research",
            "evidence",
            "valuation",
        ):
            object.__setattr__(
                self,
                field_name,
                parse_optional_dict(getattr(self, field_name), field_name) or {},
            )
        for field_name in (
            "top_holdings",
            "missing_valuation",
            "latest_updates",
            "warnings",
        ):
            object.__setattr__(
                self,
                field_name,
                tuple(dict(item) for item in getattr(self, field_name)),
            )
        object.__setattr__(
            self,
            "reference_datetime",
            parse_optional_datetime(self.reference_datetime, "reference_datetime"),
        )
        if self.reference_datetime is None:
            raise DashboardError("reference_datetime is required.")
        object.__setattr__(
            self,
            "generated_at",
            parse_optional_datetime(self.generated_at, "generated_at") or self.reference_datetime,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dashboard snapshot."""

        return {
            "snapshot_id": self.snapshot_id,
            "portfolio_summary": dict(self.portfolio_summary),
            "nav_summary": dict(self.nav_summary),
            "coverage": dict(self.coverage),
            "research": dict(self.research),
            "evidence": dict(self.evidence),
            "valuation": dict(self.valuation),
            "top_holdings": [dict(item) for item in self.top_holdings],
            "missing_valuation": [dict(item) for item in self.missing_valuation],
            "latest_updates": [dict(item) for item in self.latest_updates],
            "warnings": [dict(item) for item in self.warnings],
            "reference_datetime": self.reference_datetime.isoformat(),
            "generated_at": self.generated_at.isoformat(),
        }
