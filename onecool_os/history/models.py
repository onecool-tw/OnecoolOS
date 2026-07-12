"""Immutable portfolio history models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any

from onecool_os.history.enums import HistoryRecordStatus
from onecool_os.history.enums import HistorySnapshotType
from onecool_os.history.enums import HistoryWriteStatus
from onecool_os.history.validation import PortfolioHistoryError
from onecool_os.history.validation import optional_text
from onecool_os.history.validation import parse_date
from onecool_os.history.validation import parse_datetime
from onecool_os.history.validation import parse_dict
from onecool_os.history.validation import parse_enum
from onecool_os.history.validation import parse_non_negative_int
from onecool_os.history.validation import parse_optional_decimal
from onecool_os.history.validation import parse_string_tuple
from onecool_os.history.validation import require_text
from onecool_os.history.validation import validate_percent


SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class AssetHistoryLine:
    """Historical per-asset valuation state."""

    asset_id: str
    asset_name: str
    valuation_coverage_status: str
    reference_datetime: datetime | str
    cert_number: str | None = None
    grade_issuer: str | None = None
    grade: str | None = None
    cost_basis: Decimal | str | int | None = None
    cost_currency: str | None = None
    market_value: Decimal | str | int | None = None
    market_currency: str | None = None
    unrealized_gain_loss: Decimal | str | int | None = None
    roi_percent: Decimal | str | int | None = None
    valuation_source: str | None = None
    valuation_record_id: str | None = None
    fair_value_snapshot_id: str | None = None
    evidence_quality_score: Decimal | str | int | None = None
    valuation_confidence: str | None = None
    freshness_status: str | None = None
    liquidity_level: str | None = None
    latest_sold_date: date | str | None = None
    warnings: tuple[str, ...] | list[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_id", require_text(self.asset_id, "asset_id"))
        object.__setattr__(self, "asset_name", require_text(self.asset_name, "asset_name"))
        for field_name in (
            "cert_number",
            "grade_issuer",
            "grade",
            "cost_currency",
            "market_currency",
            "valuation_source",
            "valuation_record_id",
            "fair_value_snapshot_id",
            "valuation_confidence",
            "freshness_status",
            "liquidity_level",
        ):
            object.__setattr__(self, field_name, optional_text(getattr(self, field_name)))
        for field_name in (
            "cost_basis",
            "market_value",
            "unrealized_gain_loss",
            "roi_percent",
            "evidence_quality_score",
        ):
            object.__setattr__(self, field_name, parse_optional_decimal(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "latest_sold_date",
            parse_date(self.latest_sold_date, "latest_sold_date") if self.latest_sold_date else None,
        )
        object.__setattr__(self, "warnings", parse_string_tuple(self.warnings, "warnings"))
        object.__setattr__(self, "reference_datetime", parse_datetime(self.reference_datetime, "reference_datetime"))

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic JSON-safe payload."""

        return {
            "asset_id": self.asset_id,
            "cert_number": self.cert_number,
            "asset_name": self.asset_name,
            "grade_issuer": self.grade_issuer,
            "grade": self.grade,
            "cost_basis": _decimal_text(self.cost_basis),
            "cost_currency": self.cost_currency,
            "market_value": _decimal_text(self.market_value),
            "market_currency": self.market_currency,
            "unrealized_gain_loss": _decimal_text(self.unrealized_gain_loss),
            "roi_percent": _decimal_text(self.roi_percent),
            "valuation_source": self.valuation_source,
            "valuation_record_id": self.valuation_record_id,
            "fair_value_snapshot_id": self.fair_value_snapshot_id,
            "evidence_quality_score": _decimal_text(self.evidence_quality_score),
            "valuation_confidence": self.valuation_confidence,
            "freshness_status": self.freshness_status,
            "liquidity_level": self.liquidity_level,
            "latest_sold_date": self.latest_sold_date.isoformat() if self.latest_sold_date else None,
            "valuation_coverage_status": self.valuation_coverage_status,
            "warnings": list(self.warnings),
            "reference_datetime": self.reference_datetime.isoformat(),
        }


@dataclass(frozen=True)
class PortfolioHistorySnapshot:
    """Immutable daily portfolio history snapshot."""

    history_snapshot_id: str
    snapshot_type: HistorySnapshotType | str
    snapshot_date: date | str
    reference_datetime: datetime | str
    generated_at: datetime | str
    currencies: tuple[str, ...] | list[str]
    total_assets: int
    collection_difference_count: int
    research_queue_total: int
    research_queue_ready: int
    research_queue_blocked: int
    evidence_verified_count: int
    evidence_review_count: int
    evidence_rejected_count: int
    evidence_no_match_count: int
    fair_value_count: int
    valuation_record_count: int
    total_cost_basis_by_currency: dict[str, Any]
    total_market_value_by_currency: dict[str, Any]
    unrealized_gain_loss_by_currency: dict[str, Any]
    roi_percent_by_currency: dict[str, Any]
    valuation_coverage_percent: Decimal | str | int
    verified_coverage_percent: Decimal | str | int
    nav_status_by_currency: dict[str, Any]
    missing_value_assets: int
    warning_count: int
    asset_lines: tuple[AssetHistoryLine | dict[str, Any], ...] | list[AssetHistoryLine | dict[str, Any]]
    warnings: tuple[str, ...] | list[str]
    status: HistoryRecordStatus | str
    schema_version: str = SCHEMA_VERSION
    runtime_version: str | None = None
    source_commit: str | None = None
    collection_health: int | None = None
    fingerprint: str | None = None

    def __post_init__(self) -> None:
        if str(self.schema_version).split(".", maxsplit=1)[0] != "1":
            raise PortfolioHistoryError(f"Unsupported schema_version: {self.schema_version}")
        object.__setattr__(self, "history_snapshot_id", require_text(self.history_snapshot_id, "history_snapshot_id"))
        object.__setattr__(self, "snapshot_type", parse_enum(HistorySnapshotType, self.snapshot_type, "snapshot_type"))
        snapshot_date = parse_date(self.snapshot_date, "snapshot_date")
        reference_datetime = parse_datetime(self.reference_datetime, "reference_datetime")
        if snapshot_date != reference_datetime.date():
            raise PortfolioHistoryError("snapshot_date is inconsistent with reference_datetime.")
        object.__setattr__(self, "snapshot_date", snapshot_date)
        object.__setattr__(self, "reference_datetime", reference_datetime)
        object.__setattr__(self, "generated_at", parse_datetime(self.generated_at, "generated_at"))
        object.__setattr__(self, "currencies", tuple(sorted(str(item).upper() for item in self.currencies)))
        for field_name in (
            "total_assets",
            "collection_difference_count",
            "research_queue_total",
            "research_queue_ready",
            "research_queue_blocked",
            "evidence_verified_count",
            "evidence_review_count",
            "evidence_rejected_count",
            "evidence_no_match_count",
            "fair_value_count",
            "valuation_record_count",
            "missing_value_assets",
            "warning_count",
        ):
            object.__setattr__(self, field_name, parse_non_negative_int(getattr(self, field_name), field_name))
        for field_name in (
            "total_cost_basis_by_currency",
            "total_market_value_by_currency",
            "unrealized_gain_loss_by_currency",
            "roi_percent_by_currency",
            "nav_status_by_currency",
        ):
            object.__setattr__(self, field_name, _decimal_dict(getattr(self, field_name), field_name))
        object.__setattr__(self, "valuation_coverage_percent", parse_optional_decimal(self.valuation_coverage_percent, "valuation_coverage_percent") or Decimal("0"))
        object.__setattr__(self, "verified_coverage_percent", parse_optional_decimal(self.verified_coverage_percent, "verified_coverage_percent") or Decimal("0"))
        validate_percent(self.valuation_coverage_percent, "valuation_coverage_percent")
        validate_percent(self.verified_coverage_percent, "verified_coverage_percent")
        lines = tuple(_asset_line(item) for item in self.asset_lines)
        if len({line.asset_id for line in lines}) != len(lines):
            raise PortfolioHistoryError("duplicate asset IDs inside one snapshot.")
        if self.total_assets != len(lines):
            raise PortfolioHistoryError("total_assets differs from asset-line count.")
        object.__setattr__(self, "asset_lines", lines)
        object.__setattr__(self, "warnings", parse_string_tuple(self.warnings, "warnings"))
        object.__setattr__(self, "status", parse_enum(HistoryRecordStatus, self.status, "status"))
        object.__setattr__(self, "runtime_version", optional_text(self.runtime_version))
        object.__setattr__(self, "source_commit", optional_text(self.source_commit))
        if self.collection_health is not None:
            object.__setattr__(self, "collection_health", parse_non_negative_int(self.collection_health, "collection_health"))
        object.__setattr__(self, "fingerprint", optional_text(self.fingerprint))

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic JSON-safe payload."""

        return {
            "schema_version": self.schema_version,
            "history_snapshot_id": self.history_snapshot_id,
            "snapshot_type": self.snapshot_type.value,
            "snapshot_date": self.snapshot_date.isoformat(),
            "reference_datetime": self.reference_datetime.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "runtime_version": self.runtime_version,
            "source_commit": self.source_commit,
            "currencies": list(self.currencies),
            "total_assets": self.total_assets,
            "collection_health": self.collection_health,
            "collection_difference_count": self.collection_difference_count,
            "research_queue_total": self.research_queue_total,
            "research_queue_ready": self.research_queue_ready,
            "research_queue_blocked": self.research_queue_blocked,
            "evidence_verified_count": self.evidence_verified_count,
            "evidence_review_count": self.evidence_review_count,
            "evidence_rejected_count": self.evidence_rejected_count,
            "evidence_no_match_count": self.evidence_no_match_count,
            "fair_value_count": self.fair_value_count,
            "valuation_record_count": self.valuation_record_count,
            "total_cost_basis_by_currency": _dict_text(self.total_cost_basis_by_currency),
            "total_market_value_by_currency": _dict_text(self.total_market_value_by_currency),
            "unrealized_gain_loss_by_currency": _dict_text(self.unrealized_gain_loss_by_currency),
            "roi_percent_by_currency": _dict_text(self.roi_percent_by_currency),
            "valuation_coverage_percent": _decimal_text(self.valuation_coverage_percent),
            "verified_coverage_percent": _decimal_text(self.verified_coverage_percent),
            "nav_status_by_currency": dict(self.nav_status_by_currency),
            "missing_value_assets": self.missing_value_assets,
            "warning_count": self.warning_count,
            "asset_lines": [line.to_dict() for line in self.asset_lines],
            "warnings": list(self.warnings),
            "status": self.status.value,
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True)
class PortfolioHistoryIndexEntry:
    """Index entry for a stored history snapshot."""

    history_snapshot_id: str
    snapshot_date: date | str
    snapshot_type: HistorySnapshotType | str
    reference_datetime: datetime | str
    currencies: tuple[str, ...] | list[str]
    total_assets: int
    valuation_record_count: int
    valuation_coverage_percent: Decimal | str | int
    status: HistoryRecordStatus | str
    file_path: str
    checksum: str
    created_at: datetime | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "history_snapshot_id", require_text(self.history_snapshot_id, "history_snapshot_id"))
        object.__setattr__(self, "snapshot_date", parse_date(self.snapshot_date, "snapshot_date"))
        object.__setattr__(self, "snapshot_type", parse_enum(HistorySnapshotType, self.snapshot_type, "snapshot_type"))
        object.__setattr__(self, "reference_datetime", parse_datetime(self.reference_datetime, "reference_datetime"))
        object.__setattr__(self, "currencies", tuple(sorted(str(item).upper() for item in self.currencies)))
        object.__setattr__(self, "total_assets", parse_non_negative_int(self.total_assets, "total_assets"))
        object.__setattr__(self, "valuation_record_count", parse_non_negative_int(self.valuation_record_count, "valuation_record_count"))
        object.__setattr__(self, "valuation_coverage_percent", parse_optional_decimal(self.valuation_coverage_percent, "valuation_coverage_percent") or Decimal("0"))
        validate_percent(self.valuation_coverage_percent, "valuation_coverage_percent")
        object.__setattr__(self, "status", parse_enum(HistoryRecordStatus, self.status, "status"))
        object.__setattr__(self, "file_path", require_text(self.file_path, "file_path"))
        object.__setattr__(self, "checksum", require_text(self.checksum, "checksum"))
        object.__setattr__(self, "created_at", parse_datetime(self.created_at, "created_at"))

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic JSON-safe payload."""

        return {
            "history_snapshot_id": self.history_snapshot_id,
            "snapshot_date": self.snapshot_date.isoformat(),
            "snapshot_type": self.snapshot_type.value,
            "reference_datetime": self.reference_datetime.isoformat(),
            "currencies": list(self.currencies),
            "total_assets": self.total_assets,
            "valuation_record_count": self.valuation_record_count,
            "valuation_coverage_percent": _decimal_text(self.valuation_coverage_percent),
            "status": self.status.value,
            "file_path": self.file_path,
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class PortfolioHistoryWriteResult:
    """Append-only history store write result."""

    status: HistoryWriteStatus | str
    snapshot: PortfolioHistorySnapshot
    file_path: str | None
    index_entry: PortfolioHistoryIndexEntry | None
    checksum: str
    warnings: tuple[str, ...] | list[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", parse_enum(HistoryWriteStatus, self.status, "status"))
        object.__setattr__(self, "warnings", parse_string_tuple(self.warnings, "warnings"))


def _asset_line(item: AssetHistoryLine | dict[str, Any]) -> AssetHistoryLine:
    if isinstance(item, AssetHistoryLine):
        return item
    if isinstance(item, dict):
        return AssetHistoryLine(**item)
    raise PortfolioHistoryError("asset_lines must contain AssetHistoryLine or dict items.")


def _decimal_dict(value: Any, field_name: str) -> dict[str, Decimal | str]:
    parsed = parse_dict(value, field_name)
    result: dict[str, Decimal | str] = {}
    for key, item in parsed.items():
        if field_name == "nav_status_by_currency":
            result[str(key).upper()] = str(item)
        else:
            result[str(key).upper()] = parse_optional_decimal(item, field_name) or Decimal("0")
    return result


def _dict_text(value: dict[str, Any]) -> dict[str, str]:
    return {key: _decimal_text(item) for key, item in sorted(value.items())}


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    text = format(value.quantize(Decimal("0.0001")), "f").rstrip("0").rstrip(".")
    return text or "0"
