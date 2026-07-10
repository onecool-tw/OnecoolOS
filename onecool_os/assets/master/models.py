"""Asset Master metadata models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from onecool_os.assets.master.validation import AssetMasterError
from onecool_os.assets.master.validation import normalize_optional_decimal
from onecool_os.assets.master.validation import normalize_optional_int
from onecool_os.assets.master.validation import normalize_optional_text
from onecool_os.assets.master.validation import normalize_required_text


@dataclass(frozen=True)
class AssetMasterRecord:
    """User-owned durable metadata for one collectible asset."""

    cert_number: str
    asset_id: str | None = None
    card_name: str | None = None
    grade_issuer: str | None = None
    grade: str | None = None
    cost_override: Decimal | str | int | float | None = None
    cost_currency: str | None = None
    ebay_sold_search_url: str | None = None
    psa_url: str | None = None
    ref_score: int | str | None = None
    watch_status: str | None = None
    target_price: Decimal | str | int | float | None = None
    notes: str | None = None
    metadata: dict[str, Any] | None = None
    source_row: int | str | None = None
    imported_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cert_number",
            normalize_required_text(self.cert_number, "cert_number"),
        )
        for field_name in (
            "asset_id",
            "card_name",
            "grade_issuer",
            "grade",
            "cost_currency",
            "ebay_sold_search_url",
            "psa_url",
            "watch_status",
            "notes",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_optional_text(getattr(self, field_name)),
            )
        object.__setattr__(
            self,
            "cost_override",
            normalize_optional_decimal(self.cost_override, "cost_override"),
        )
        object.__setattr__(
            self,
            "target_price",
            normalize_optional_decimal(self.target_price, "target_price"),
        )
        object.__setattr__(
            self,
            "ref_score",
            normalize_optional_int(self.ref_score, "ref_score"),
        )
        metadata = self.metadata or {}
        if not isinstance(metadata, dict):
            raise AssetMasterError("metadata must be a dictionary.")
        object.__setattr__(self, "metadata", dict(metadata))
        object.__setattr__(
            self,
            "source_row",
            normalize_optional_int(self.source_row, "source_row"),
        )
        if self.imported_at is not None and not isinstance(
            self.imported_at,
            datetime,
        ):
            raise AssetMasterError("imported_at must be a datetime.")

    def to_metadata(self) -> dict[str, Any]:
        """Return merge-safe Asset Master metadata."""

        metadata = {
            "asset_id": self.asset_id,
            "card_name": self.card_name,
            "grade_issuer": self.grade_issuer,
            "grade": self.grade,
            "ebay_sold_search_url": self.ebay_sold_search_url,
            "psa_url": self.psa_url,
            "ref_score": self.ref_score,
            "watch_status": self.watch_status,
            "target_price": _format_decimal(self.target_price),
            "notes": self.notes,
            "metadata": dict(self.metadata),
            "source_row": self.source_row,
            "imported_at": (
                self.imported_at.isoformat() if self.imported_at else None
            ),
        }
        return {
            key: value
            for key, value in metadata.items()
            if value not in (None, "", {})
        }

    def cost_override_payload(self) -> dict[str, str] | None:
        """Return explicit cost override payload without replacing cost."""

        if self.cost_override is None:
            return None
        payload = {"amount": _format_decimal(self.cost_override)}
        if self.cost_currency:
            payload["currency"] = self.cost_currency
        return payload


@dataclass(frozen=True)
class AssetMasterLoadResult:
    """Result of loading one Asset Master file."""

    records: tuple[AssetMasterRecord, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    duplicate_cert_numbers: tuple[str, ...]
    source_file: str
    generated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.generated_at, datetime):
            raise AssetMasterError("generated_at must be a datetime.")
        object.__setattr__(self, "records", tuple(self.records))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "errors", tuple(self.errors))
        object.__setattr__(
            self,
            "duplicate_cert_numbers",
            tuple(self.duplicate_cert_numbers),
        )


def _format_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.normalize():f}"
