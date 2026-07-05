"""Manual valuation import foundation."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from onecool_os.connectors.import_audit import ImportAudit
from onecool_os.core.exceptions import OnecoolOSError
from onecool_os.valuation.enums import ValuationConfidence
from onecool_os.valuation.enums import ValuationSource
from onecool_os.valuation.models import ValuationRecord
from onecool_os.valuation.validation import ValuationError


MANUAL_VALUATION_SOURCE = "MANUAL_VALUATION"
REQUIRED_FIELDS = (
    "asset_id",
    "asset_type",
    "currency",
    "valuation_date",
)


class ManualValuationImportError(OnecoolOSError):
    """Raised when manual valuation import cannot proceed."""


@dataclass(frozen=True)
class ImportSummary:
    """Deterministic summary of manual valuation import."""

    imported_rows: int
    skipped_rows: int
    duplicate_rows: int
    invalid_rows: int
    warnings: list[str] | tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "imported_rows",
            "skipped_rows",
            "duplicate_rows",
            "invalid_rows",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or value < 0:
                raise ManualValuationImportError(
                    f"{field_name} must be a non-negative integer."
                )
        object.__setattr__(
            self,
            "warnings",
            tuple(str(warning) for warning in self.warnings or ()),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe summary."""

        return {
            "imported_rows": self.imported_rows,
            "skipped_rows": self.skipped_rows,
            "duplicate_rows": self.duplicate_rows,
            "invalid_rows": self.invalid_rows,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ManualValuationImportRecord:
    """Manual valuation record plus import metadata."""

    valuation_record: ValuationRecord
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.valuation_record, ValuationRecord):
            raise ManualValuationImportError(
                "valuation_record must be a ValuationRecord."
            )
        object.__setattr__(self, "metadata", dict(self.metadata or {}))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe manual valuation import record."""

        return {
            "valuation_record": self.valuation_record.to_dict(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ManualValuationImportResult:
    """Result of a read-only manual valuation import."""

    source_path: Path
    records: tuple[ManualValuationImportRecord, ...]
    summary: ImportSummary
    audit: ImportAudit

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe import result."""

        return {
            "source_path": str(self.source_path),
            "records": [record.to_dict() for record in self.records],
            "summary": self.summary.to_dict(),
            "audit": self.audit.to_dict(),
        }


class ManualValuationImporter:
    """Import user-provided manual valuation observations."""

    source = MANUAL_VALUATION_SOURCE

    def import_file(
        self,
        path: str | Path,
        *,
        reference_datetime: datetime,
    ) -> ManualValuationImportResult:
        """Load CSV or JSON manual valuation records without writing files."""

        if not isinstance(reference_datetime, datetime):
            raise ManualValuationImportError(
                "reference_datetime must be a datetime."
            )
        source_path = Path(path)
        source_bytes = _read_bytes(source_path)
        rows = _load_rows(source_path, source_bytes)
        records: list[ManualValuationImportRecord] = []
        warnings: list[str] = []
        seen_ids: set[str] = set()
        duplicate_rows = 0
        invalid_rows = 0
        skipped_rows = 0

        for index, row in enumerate(rows, start=1):
            row_number = index + 1
            valuation_id = _optional_text(row.get("valuation_id"))
            if valuation_id and valuation_id in seen_ids:
                duplicate_rows += 1
                skipped_rows += 1
                warnings.append(
                    f"Duplicate valuation_id at row {row_number}: "
                    f"{valuation_id}"
                )
                continue
            try:
                record = _record_from_row(row, row_number)
            except (ManualValuationImportError, ValuationError) as exc:
                invalid_rows += 1
                warnings.append(str(exc))
                continue
            seen_ids.add(record.valuation_record.valuation_id)
            records.append(record)

        summary = ImportSummary(
            imported_rows=len(records),
            skipped_rows=skipped_rows,
            duplicate_rows=duplicate_rows,
            invalid_rows=invalid_rows,
            warnings=warnings,
        )
        audit = ImportAudit(
            import_id=(
                f"manual-valuation:{source_path.name}:"
                f"{reference_datetime.isoformat()}"
            ),
            source=self.source,
            imported_at=reference_datetime,
            source_filename=source_path.name,
            reference_datetime=reference_datetime,
            total_rows=len(rows),
            imported_rows=summary.imported_rows,
            skipped_rows=summary.skipped_rows,
            duplicate_rows=summary.duplicate_rows,
            invalid_rows=summary.invalid_rows,
            warnings=summary.warnings,
            checksum=hashlib.sha256(source_bytes).hexdigest(),
        )
        return ManualValuationImportResult(
            source_path=source_path,
            records=tuple(records),
            summary=summary,
            audit=audit,
        )


def _record_from_row(
    row: dict[str, Any],
    row_number: int,
) -> ManualValuationImportRecord:
    for field_name in REQUIRED_FIELDS:
        if not _optional_text(row.get(field_name)):
            raise ManualValuationImportError(
                f"Missing manual valuation value at row {row_number}: "
                f"{field_name}"
            )
    if not _has_value(row):
        raise ManualValuationImportError(
            f"Missing manual valuation value at row {row_number}: "
            "estimated_value or market_value"
        )
    valuation_id = _optional_text(row.get("valuation_id")) or _valuation_id(
        row,
        row_number,
    )
    try:
        valuation_record = ValuationRecord(
            valuation_id=valuation_id,
            asset_id=_required_text(row, "asset_id", row_number),
            asset_type=_required_text(row, "asset_type", row_number),
            source=ValuationSource.MANUAL,
            currency=_required_text(row, "currency", row_number),
            valuation_date=_required_text(row, "valuation_date", row_number),
            confidence=ValuationConfidence.LOW,
            market_value=_optional_value(row.get("market_value")),
            estimated_value=_optional_value(row.get("estimated_value")),
            low_value=_optional_value(row.get("low_value")),
            high_value=_optional_value(row.get("high_value")),
            note=_optional_text(row.get("note")),
            url=_optional_text(row.get("url")),
            tags=_parse_tags(row.get("tags")),
        )
    except ValuationError as exc:
        raise ManualValuationImportError(
            f"Invalid manual valuation at row {row_number}: {exc}"
        ) from exc
    metadata = {
        "primary_market_price": False,
        "validation_source": True,
        "source_role": "MANUAL_FALLBACK",
        "reference": _optional_text(row.get("reference")),
        "raw_payload": _optional_raw_payload(row.get("raw_payload")),
    }
    return ManualValuationImportRecord(
        valuation_record=valuation_record,
        metadata=metadata,
    )


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ManualValuationImportError(
            f"Manual valuation file cannot be read: {path}"
        ) from exc


def _load_rows(path: Path, source_bytes: bytes) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    text = _decode(source_bytes)
    if suffix == ".csv":
        return _load_csv(text)
    if suffix == ".json":
        return _load_json(text)
    raise ManualValuationImportError(
        "Manual valuation import supports CSV and JSON files only."
    )


def _load_csv(text: str) -> list[dict[str, Any]]:
    try:
        reader = csv.DictReader(text.splitlines())
        if reader.fieldnames is None:
            raise ManualValuationImportError(
                "Manual valuation CSV is missing a header row."
            )
        return [dict(row) for row in reader]
    except csv.Error as exc:
        raise ManualValuationImportError(
            f"Invalid manual valuation CSV: {exc}"
        ) from exc


def _load_json(text: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManualValuationImportError(
            f"Invalid manual valuation JSON: {exc.msg}"
        ) from exc
    rows = payload.get("valuations") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ManualValuationImportError(
            "Manual valuation JSON must be a list or contain valuations."
        )
    for row in rows:
        if not isinstance(row, dict):
            raise ManualValuationImportError(
                "Manual valuation JSON rows must be objects."
            )
    return [dict(row) for row in rows]


def _decode(source_bytes: bytes) -> str:
    try:
        return source_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ManualValuationImportError(
            "Manual valuation file must be UTF-8 encoded."
        ) from exc


def _valuation_id(row: dict[str, Any], row_number: int) -> str:
    asset_id = _required_text(row, "asset_id", row_number)
    valuation_date = _required_text(row, "valuation_date", row_number)
    return f"manual:{asset_id}:{valuation_date}:{row_number}"


def _required_text(
    row: dict[str, Any],
    field_name: str,
    row_number: int,
) -> str:
    value = _optional_text(row.get(field_name))
    if value is None:
        raise ManualValuationImportError(
            f"Missing manual valuation value at row {row_number}: {field_name}"
        )
    return value


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_value(row: dict[str, Any]) -> bool:
    return (
        _optional_text(row.get("market_value")) is not None
        or _optional_text(row.get("estimated_value")) is not None
    )


def _optional_value(value: Any) -> Any | None:
    return _optional_text(value)


def _parse_tags(value: Any) -> list[str]:
    if value in (None, ""):
        return ["manual", "collectible"]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [
        item.strip()
        for item in str(value).replace(";", ",").split(",")
        if item.strip()
    ]


def _optional_raw_payload(value: Any) -> dict[str, Any] | None:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {"value": value}
        if isinstance(parsed, dict):
            return parsed
        return {"value": parsed}
    return {"value": value}
