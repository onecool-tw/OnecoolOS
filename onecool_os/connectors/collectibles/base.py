"""Base interface for local collectible market connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable

from onecool_os.connectors.collectibles.enums import CollectibleMarketSource
from onecool_os.connectors.collectibles.models import (
    CollectibleConnectorError,
)
from onecool_os.connectors.collectibles.models import CollectibleMarketRecord


class BaseCollectibleConnector(ABC):
    """Connector interface for local collectible market records."""

    connector_name: str
    source: CollectibleMarketSource

    def __init__(
        self,
        records: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        self._records = tuple(dict(record) for record in records or ())

    def read_records(self) -> tuple[dict[str, Any], ...]:
        """Return local fixture records without mutating them."""

        return tuple(dict(record) for record in self._records)

    @abstractmethod
    def normalize_record(
        self,
        raw_record: dict[str, Any],
    ) -> CollectibleMarketRecord:
        """Normalize one local source record."""

    def normalize_records(self) -> tuple[CollectibleMarketRecord, ...]:
        """Normalize all local records loaded into the connector."""

        return tuple(
            self.normalize_record(raw_record)
            for raw_record in self.read_records()
        )

    def _ensure_record(self, raw_record: dict[str, Any]) -> None:
        if not isinstance(raw_record, dict):
            raise CollectibleConnectorError("raw_record must be a dictionary.")
