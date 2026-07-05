"""Reusable connector import audit model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from onecool_os.core.exceptions import OnecoolOSError


class ImportAuditError(OnecoolOSError):
    """Raised when import audit data is invalid."""


@dataclass(frozen=True)
class ImportAudit:
    """Read-only audit record for connector imports."""

    import_id: str
    source: str
    imported_at: datetime | str
    source_filename: str
    reference_datetime: datetime | str
    total_rows: int
    imported_rows: int
    skipped_rows: int
    duplicate_rows: int
    invalid_rows: int
    warnings: list[str] | tuple[str, ...] | None = None
    checksum: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "import_id",
            _require_text(self.import_id, "import_id"),
        )
        object.__setattr__(self, "source", _require_text(self.source, "source"))
        object.__setattr__(
            self,
            "imported_at",
            _parse_datetime(self.imported_at, "imported_at"),
        )
        object.__setattr__(
            self,
            "source_filename",
            _require_text(self.source_filename, "source_filename"),
        )
        object.__setattr__(
            self,
            "reference_datetime",
            _parse_datetime(self.reference_datetime, "reference_datetime"),
        )
        for field_name in (
            "total_rows",
            "imported_rows",
            "skipped_rows",
            "duplicate_rows",
            "invalid_rows",
        ):
            object.__setattr__(
                self,
                field_name,
                _non_negative_int(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "warnings",
            _text_tuple(self.warnings, "warnings"),
        )
        object.__setattr__(
            self,
            "checksum",
            str(self.checksum) if self.checksum else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe audit payload."""

        return {
            "import_id": self.import_id,
            "source": self.source,
            "imported_at": self.imported_at.isoformat(),
            "source_filename": self.source_filename,
            "reference_datetime": self.reference_datetime.isoformat(),
            "statistics": {
                "total_rows": self.total_rows,
                "imported_rows": self.imported_rows,
                "skipped_rows": self.skipped_rows,
                "duplicate_rows": self.duplicate_rows,
                "invalid_rows": self.invalid_rows,
            },
            "warnings": list(self.warnings),
            "metadata": {
                "checksum": self.checksum,
            },
        }


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ImportAuditError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _parse_datetime(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ImportAuditError(f"{field_name} must be a datetime.")
    try:
        return datetime.fromisoformat(value.strip())
    except ValueError as exc:
        raise ImportAuditError(f"{field_name} must be an ISO datetime.") from exc


def _non_negative_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise ImportAuditError(f"{field_name} must be a non-negative integer.")
    return value


def _text_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise ImportAuditError(f"{field_name} must be a list or tuple.")
    return tuple(_require_text(item, field_name) for item in value)
