"""Shared base models for asset modules."""

from __future__ import annotations

from datetime import datetime
from typing import Any


class BaseAsset:
    """Minimum shared asset contract for asset modules."""

    asset_id: str
    asset_type: str
    name: str
    currency: str
    created_at: datetime | None
    updated_at: datetime | None

    def __init__(
        self,
        asset_id: str,
        asset_type: str,
        name: str,
        currency: str,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.asset_id = asset_id
        self.asset_type = asset_type
        self.name = name
        self.currency = currency
        self.created_at = created_at
        self.updated_at = updated_at


class BasePosition:
    """Minimum shared position contract for asset modules."""

    asset: BaseAsset
    notes: str

    def __init__(self, asset: BaseAsset, notes: str = "") -> None:
        self.asset = asset
        self.notes = notes

    def metadata(self) -> dict[str, Any]:
        """Return simple shared position metadata."""

        return {
            "asset_id": self.asset.asset_id,
            "asset_type": self.asset.asset_type,
            "notes": self.notes,
        }
