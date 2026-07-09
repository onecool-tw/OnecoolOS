"""PSA Collection CSV integration foundation."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation
from pathlib import Path
from typing import Any

from onecool_os.connectors.import_audit import ImportAudit
from onecool_os.core.exceptions import OnecoolOSError


PSA_REQUIRED_COLUMNS = (
    "Item",
    "Subject",
    "Year",
    "Set",
    "Card Number",
    "Grade Issuer",
    "Grade",
    "Cert Number",
    "My Cost",
    "Date Acquired",
    "Source",
    "My Notes",
)
SUPPORTED_GRADERS = frozenset(("PSA", "BGS"))
BGS_SUPPORTED_GRADES = frozenset(("8", "8.5", "9", "9.5", "10"))
BGS_BLACK_LABEL = "10 BLACK LABEL"


class PSAImportError(OnecoolOSError):
    """Raised when PSA Collection CSV import cannot proceed."""


@dataclass(frozen=True)
class ImportSummary:
    """Deterministic summary of an import attempt."""

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
                raise PSAImportError(
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
class PSAImportResult:
    """Result of a read-only PSA Collection import."""

    source_path: Path
    records: tuple[dict[str, Any], ...]
    summary: ImportSummary
    audit: ImportAudit

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe import result."""

        return {
            "source_path": str(self.source_path),
            "records": [dict(record) for record in self.records],
            "summary": self.summary.to_dict(),
            "audit": self.audit.to_dict(),
        }


class PSACollectionImporter:
    """Import PSA Collection CSV rows into normalized asset records only."""

    source = "PSA Collection CSV"

    def import_csv(
        self,
        csv_path: str | Path,
        *,
        existing_assets: list[dict[str, Any]]
        | tuple[dict[str, Any], ...]
        | None = None,
        reference_datetime: datetime,
    ) -> PSAImportResult:
        """Load, validate, and normalize a PSA CSV without writing files."""

        if not isinstance(reference_datetime, datetime):
            raise PSAImportError("reference_datetime must be a datetime.")
        source_path = Path(csv_path)
        csv_bytes = self._read_bytes(source_path)
        rows = self._read_rows(csv_bytes)
        existing = tuple(dict(asset) for asset in existing_assets or ())
        records: list[dict[str, Any]] = []
        warnings: list[str] = []
        seen_cert_numbers: set[str] = set()
        duplicate_rows = 0
        invalid_rows = 0
        skipped_rows = 0

        for row_number, row in enumerate(rows, start=2):
            validation_error = self._validation_error(row, row_number)
            if validation_error:
                invalid_rows += 1
                warnings.append(validation_error)
                continue

            cert_number = _require_text(row.get("Cert Number"))
            if cert_number in seen_cert_numbers:
                duplicate_rows += 1
                skipped_rows += 1
                warnings.append(
                    f"Duplicate PSA cert number at row {row_number}: "
                    f"{cert_number}"
                )
                continue
            seen_cert_numbers.add(cert_number)

            if (
                _normalize_text(row.get("Grade Issuer")).upper()
                not in SUPPORTED_GRADERS
            ):
                skipped_rows += 1
                warnings.append(
                    f"Unsupported grader at row {row_number}: "
                    f"{row.get('Grade Issuer')}"
                )
                continue

            records.append(
                self._normalize_record(
                    row,
                    row_number=row_number,
                    existing_assets=existing,
                )
            )

        summary = ImportSummary(
            imported_rows=len(records),
            skipped_rows=skipped_rows,
            duplicate_rows=duplicate_rows,
            invalid_rows=invalid_rows,
            warnings=warnings,
        )
        audit = ImportAudit(
            import_id=(
                f"psa-collection:{source_path.name}:"
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
            checksum=hashlib.sha256(csv_bytes).hexdigest(),
        )
        return PSAImportResult(
            source_path=source_path,
            records=tuple(records),
            summary=summary,
            audit=audit,
        )

    def _read_bytes(self, path: Path) -> bytes:
        try:
            return path.read_bytes()
        except OSError as exc:
            raise PSAImportError(f"PSA CSV file cannot be read: {path}") from exc

    def _read_rows(self, csv_bytes: bytes) -> list[dict[str, str]]:
        try:
            text = csv_bytes.decode("utf-8-sig")
            reader = csv.DictReader(text.splitlines())
            self._validate_headers(reader.fieldnames)
            return [dict(row) for row in reader]
        except UnicodeDecodeError as exc:
            raise PSAImportError("PSA CSV must be UTF-8 encoded.") from exc
        except csv.Error as exc:
            raise PSAImportError(f"Invalid PSA CSV: {exc}") from exc

    def _validate_headers(self, fieldnames: list[str] | None) -> None:
        if fieldnames is None:
            raise PSAImportError("PSA CSV is missing a header row.")
        missing = sorted(set(PSA_REQUIRED_COLUMNS) - set(fieldnames))
        if missing:
            raise PSAImportError(
                f"Missing PSA CSV column: {', '.join(missing)}"
            )

    def _validation_error(
        self,
        row: dict[str, str],
        row_number: int,
    ) -> str | None:
        for column in PSA_REQUIRED_COLUMNS:
            if not _normalize_text(row.get(column)):
                return f"Missing PSA CSV value at row {row_number}: {column}"
        grader = _normalize_text(row.get("Grade Issuer")).upper()
        if grader in SUPPORTED_GRADERS:
            grade_info = _parse_grade_info(grader, row.get("Grade"))
            if grade_info is None:
                return (
                    f"Invalid {grader} grade at row {row_number}: "
                    f"{row.get('Grade')}"
                )
        cost = _parse_positive_decimal(row.get("My Cost"))
        if cost is None:
            return f"Invalid PSA cost at row {row_number}: {row.get('My Cost')}"
        return None

    def _normalize_record(
        self,
        row: dict[str, str],
        *,
        row_number: int,
        existing_assets: tuple[dict[str, Any], ...],
    ) -> dict[str, Any]:
        cert_number = _require_text(row.get("Cert Number"))
        cost = _parse_positive_decimal(row.get("My Cost"))
        grade_info = _parse_grade_info(
            _require_text(row.get("Grade Issuer")).upper(),
            row.get("Grade"),
        )
        if grade_info is None:
            raise PSAImportError("Expected supported grade value.")
        grade, special_designation = grade_info
        set_name = _require_text(row.get("Set"))
        item = _require_text(row.get("Item"))
        notes = _normalize_text(row.get("My Notes"))
        if notes:
            notes = f"{notes} | PSA Item: {item}"
        else:
            notes = f"PSA Item: {item}"

        record = {
            "account": "PSA Collection",
            "asset_class": "Sports Card",
            "status": "Owned",
            "currency": "USD",
            "base_currency": "TWD",
            "cost": _format_decimal(cost),
            "inventory_id": f"INV-PSA-{cert_number}",
            "cert_number": cert_number,
            "owned_quantity": "1",
            "available_quantity": "1",
            "listed_quantity": "0",
            "sold_quantity": "0",
            "location": "",
            "cabinet": "",
            "box": "",
            "row": "",
            "slot": "",
            "last_inventory_update": _require_text(row.get("Date Acquired")),
            "asset_id": f"PSA-{cert_number}",
            "player": _require_text(row.get("Subject")),
            "year": _require_text(row.get("Year")),
            "sport": "Unknown",
            "brand": set_name,
            "set": set_name,
            "card_number": _require_text(row.get("Card Number")),
            "parallel": "",
            "serial_number": cert_number,
            "grade_company": _require_text(row.get("Grade Issuer")),
            "grade": grade,
            "special_designation": special_designation,
            "purchase_date": _require_text(row.get("Date Acquired")),
            "purchase_platform": _normalize_text(row.get("Source")),
            "collection_type": "Investment",
            "valuation_source": "eBay Sold",
            "notes": notes,
            "source": "PSA Collection CSV",
            "source_row_number": row_number,
            "collection_identifier": cert_number,
        }
        record["matching"] = _match_record(record, existing_assets)
        return record


def _match_record(
    record: dict[str, Any],
    existing_assets: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    cert_number = record["cert_number"]
    asset_id = record["asset_id"]
    identity = _card_identity(record)

    for asset in existing_assets:
        if _normalize_text(
            asset.get("cert_number") or asset.get("serial_number")
        ) == cert_number:
            return {
                "status": "MATCHED",
                "matched_by": "PSA_CERT_NUMBER",
                "matched_asset_id": asset.get("asset_id"),
            }
    for asset in existing_assets:
        if _normalize_text(asset.get("asset_id")) == asset_id:
            return {
                "status": "MATCHED",
                "matched_by": "ASSET_IDENTIFIER",
                "matched_asset_id": asset.get("asset_id"),
            }
    for asset in existing_assets:
        if _card_identity(asset) == identity:
            return {
                "status": "NEEDS_REVIEW",
                "matched_by": "CARD_IDENTITY",
                "matched_asset_id": asset.get("asset_id"),
            }
    return {
        "status": "NEW",
        "matched_by": None,
        "matched_asset_id": None,
    }


def _card_identity(record: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        _normalize_text(record.get("player")).upper(),
        _normalize_text(record.get("year")).upper(),
        _normalize_text(record.get("set") or record.get("brand")).upper(),
        _normalize_text(record.get("card_number")).upper(),
        _normalize_text(record.get("grade")).upper(),
    )


def _require_text(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        raise PSAImportError("Expected non-empty text.")
    return text


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _parse_grade_info(grader: str, value: Any) -> tuple[str, str] | None:
    grade_text = _normalize_text(value)
    normalized_grade = grade_text.upper()
    if grader == "BGS":
        if normalized_grade == BGS_BLACK_LABEL:
            return "10", "Black Label"
        if grade_text in BGS_SUPPORTED_GRADES:
            return grade_text, ""
        return None
    grade = _parse_psa_grade(grade_text)
    if grade is None:
        return None
    return _format_decimal(grade), ""


def _parse_psa_grade(value: Any) -> Decimal | None:
    try:
        grade = Decimal(_normalize_text(value))
    except (InvalidOperation, ValueError):
        return None
    if not grade.is_finite() or grade < Decimal("1") or grade > Decimal("10"):
        return None
    return grade


def _parse_positive_decimal(value: Any) -> Decimal | None:
    try:
        parsed = Decimal(_normalize_text(value))
    except (InvalidOperation, ValueError):
        return None
    if not parsed.is_finite() or parsed <= Decimal("0"):
        return None
    return parsed


def _format_decimal(value: Decimal | None) -> str:
    if value is None:
        raise PSAImportError("Expected decimal value.")
    return f"{value.normalize():f}"
