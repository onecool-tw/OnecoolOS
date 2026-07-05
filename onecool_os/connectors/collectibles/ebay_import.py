"""eBay Sold manual import foundation."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation
from pathlib import Path
from typing import Any

from onecool_os.connectors.collectibles.enums import CollectibleMarketSource
from onecool_os.connectors.collectibles.enums import source_role_for_source
from onecool_os.connectors.collectibles.models import (
    CollectibleMarketRecord,
)
from onecool_os.connectors.collectibles.models import (
    CollectibleConnectorError,
)
from onecool_os.connectors.import_audit import ImportAudit
from onecool_os.core.exceptions import OnecoolOSError


class EbaySoldImportError(OnecoolOSError):
    """Raised when eBay Sold manual import cannot proceed."""


@dataclass(frozen=True)
class ImportSummary:
    """Deterministic summary of eBay Sold manual import."""

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
                raise EbaySoldImportError(
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
class EbaySoldImportResult:
    """Result of a read-only eBay Sold manual import."""

    source_path: Path
    records: tuple[CollectibleMarketRecord, ...]
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


class EbaySoldManualImporter:
    """Import user-provided eBay Sold CSV / JSON records."""

    source = CollectibleMarketSource.EBAY_SOLD

    def import_file(
        self,
        path: str | Path,
        *,
        reference_datetime: datetime,
    ) -> EbaySoldImportResult:
        """Load eBay Sold observations without writing files."""

        if not isinstance(reference_datetime, datetime):
            raise EbaySoldImportError("reference_datetime must be a datetime.")
        source_path = Path(path)
        source_bytes = _read_bytes(source_path)
        rows = _load_rows(source_path, source_bytes)
        records: list[CollectibleMarketRecord] = []
        warnings: list[str] = []
        seen_external_ids: set[str] = set()
        seen_references: set[str] = set()
        duplicate_rows = 0
        invalid_rows = 0
        skipped_rows = 0

        for index, row in enumerate(rows, start=1):
            row_number = index + 1
            validation_error = _validation_error(row, row_number)
            if validation_error:
                invalid_rows += 1
                warnings.append(validation_error)
                continue
            external_id = _external_id(row, row_number)
            reference = _reference(row)
            if external_id in seen_external_ids:
                duplicate_rows += 1
                skipped_rows += 1
                warnings.append(
                    f"Duplicate eBay external_id at row {row_number}: "
                    f"{external_id}"
                )
                continue
            if reference and reference in seen_references:
                duplicate_rows += 1
                skipped_rows += 1
                warnings.append(
                    f"Duplicate eBay url/reference at row {row_number}: "
                    f"{reference}"
                )
                continue
            seen_external_ids.add(external_id)
            if reference:
                seen_references.add(reference)
            records.append(_market_record_from_row(row, row_number))

        summary = ImportSummary(
            imported_rows=len(records),
            skipped_rows=skipped_rows,
            duplicate_rows=duplicate_rows,
            invalid_rows=invalid_rows,
            warnings=warnings,
        )
        audit = ImportAudit(
            import_id=(
                f"ebay-sold:{source_path.name}:"
                f"{reference_datetime.isoformat()}"
            ),
            source=self.source.value,
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
        return EbaySoldImportResult(
            source_path=source_path,
            records=tuple(records),
            summary=summary,
            audit=audit,
        )


def source_role() -> str:
    """Return the valuation role for eBay Sold imports."""

    return source_role_for_source(CollectibleMarketSource.EBAY_SOLD).value


def _market_record_from_row(
    row: dict[str, Any],
    row_number: int,
) -> CollectibleMarketRecord:
    raw_payload = _raw_payload(row)
    raw_payload.update(
        {
            "asset_id": _optional_text(row.get("asset_id")),
            "shipping": _optional_text(row.get("shipping")),
            "buyer_country": _optional_text(row.get("buyer_country")),
            "seller_country": _optional_text(row.get("seller_country")),
            "note": _optional_text(row.get("note")),
            "tags": _parse_tags(row.get("tags")),
            "reference": _reference(row),
            "source_role": source_role(),
        }
    )
    try:
        return CollectibleMarketRecord(
            record_id=f"ebay_sold:{_external_id(row, row_number)}",
            source=CollectibleMarketSource.EBAY_SOLD,
            external_id=_external_id(row, row_number),
            asset_hint=_asset_hint(row),
            title=_optional_text(row.get("title")),
            player=_optional_text(row.get("player")),
            year=_optional_text(row.get("year")),
            brand=_optional_text(row.get("brand")),
            card_number=_optional_text(row.get("card_number")),
            grade_company=_optional_text(row.get("grade_company")),
            grade=_optional_text(row.get("grade")),
            sale_price=_optional_text(row.get("sale_price")),
            currency=_required_text(row, "currency", row_number),
            sale_date=_required_text(row, "sale_date", row_number),
            url=_optional_text(row.get("url")),
            raw_payload=raw_payload,
        )
    except CollectibleConnectorError as exc:
        raise EbaySoldImportError(
            f"Invalid eBay Sold record at row {row_number}: {exc}"
        ) from exc


def _validation_error(row: dict[str, Any], row_number: int) -> str | None:
    for field_name in ("sale_price", "currency", "sale_date"):
        if not _optional_text(row.get(field_name)):
            return f"Missing eBay Sold value at row {row_number}: {field_name}"
    if not _optional_text(row.get("external_id")) and not _reference(row):
        return (
            f"Missing eBay Sold value at row {row_number}: "
            "external_id or url/reference"
        )
    if not _optional_text(row.get("asset_id")) and not _asset_hint(row):
        return (
            f"Missing eBay Sold value at row {row_number}: "
            "asset_id or asset_hint"
        )
    sale_price = _parse_non_negative_decimal(row.get("sale_price"))
    if sale_price is None:
        return (
            f"Invalid eBay Sold value at row {row_number}: sale_price"
        )
    if not _valid_date(row.get("sale_date")):
        return f"Invalid eBay Sold value at row {row_number}: sale_date"
    return None


def _asset_hint(row: dict[str, Any]) -> dict[str, Any]:
    raw_hint = row.get("asset_hint")
    if isinstance(raw_hint, dict):
        return dict(raw_hint)
    if isinstance(raw_hint, str) and raw_hint.strip():
        try:
            parsed = json.loads(raw_hint)
        except json.JSONDecodeError:
            parsed = {"description": raw_hint.strip()}
        if isinstance(parsed, dict):
            return parsed
    hint = {
        key: _optional_text(row.get(key))
        for key in (
            "player",
            "year",
            "brand",
            "card_number",
            "grade_company",
            "grade",
            "title",
        )
        if _optional_text(row.get(key))
    }
    return hint


def _external_id(row: dict[str, Any], row_number: int) -> str:
    external_id = _optional_text(row.get("external_id"))
    if external_id:
        return external_id
    reference = _reference(row)
    if reference:
        return f"reference:{hashlib.sha256(reference.encode()).hexdigest()[:16]}"
    raise EbaySoldImportError(
        f"Missing eBay Sold value at row {row_number}: external_id"
    )


def _reference(row: dict[str, Any]) -> str | None:
    return _optional_text(row.get("url")) or _optional_text(
        row.get("reference")
    )


def _raw_payload(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("raw_payload")
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"value": raw.strip()}
        if isinstance(parsed, dict):
            return parsed
        return {"value": parsed}
    return {}


def _parse_tags(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [
        item.strip()
        for item in str(value).replace(";", ",").split(",")
        if item.strip()
    ]


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise EbaySoldImportError(
            f"eBay Sold import file cannot be read: {path}"
        ) from exc


def _load_rows(path: Path, source_bytes: bytes) -> list[dict[str, Any]]:
    text = _decode(source_bytes)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _load_csv(text)
    if suffix == ".json":
        return _load_json(text)
    raise EbaySoldImportError(
        "eBay Sold manual import supports CSV and JSON files only."
    )


def _load_csv(text: str) -> list[dict[str, Any]]:
    try:
        reader = csv.DictReader(text.splitlines())
        if reader.fieldnames is None:
            raise EbaySoldImportError(
                "eBay Sold CSV is missing a header row."
            )
        return [dict(row) for row in reader]
    except csv.Error as exc:
        raise EbaySoldImportError(f"Invalid eBay Sold CSV: {exc}") from exc


def _load_json(text: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise EbaySoldImportError(f"Invalid eBay Sold JSON: {exc.msg}") from exc
    rows = payload.get("records") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise EbaySoldImportError(
            "eBay Sold JSON must be a list or contain records."
        )
    for row in rows:
        if not isinstance(row, dict):
            raise EbaySoldImportError("eBay Sold JSON rows must be objects.")
    return [dict(row) for row in rows]


def _decode(source_bytes: bytes) -> str:
    try:
        return source_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise EbaySoldImportError(
            "eBay Sold import file must be UTF-8 encoded."
        ) from exc


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _required_text(
    row: dict[str, Any],
    field_name: str,
    row_number: int,
) -> str:
    value = _optional_text(row.get(field_name))
    if value is None:
        raise EbaySoldImportError(
            f"Missing eBay Sold value at row {row_number}: {field_name}"
        )
    return value


def _parse_non_negative_decimal(value: Any) -> Decimal | None:
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None
    if not parsed.is_finite() or parsed < Decimal("0"):
        return None
    return parsed


def _valid_date(value: Any) -> bool:
    text = _optional_text(value)
    if text is None:
        return False
    try:
        datetime.fromisoformat(text)
    except ValueError:
        return False
    return True
