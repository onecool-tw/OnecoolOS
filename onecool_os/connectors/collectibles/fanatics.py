"""Local Fanatics Collect collectible connector."""

from __future__ import annotations

from typing import Any

from onecool_os.connectors.collectibles.base import BaseCollectibleConnector
from onecool_os.connectors.collectibles.enums import CollectibleMarketSource
from onecool_os.connectors.collectibles.models import CollectibleMarketRecord
from onecool_os.connectors.collectibles.normalization import (
    normalize_collectible_market_record,
)


class FanaticsConnector(BaseCollectibleConnector):
    """Normalize local Fanatics Collect records as validation source inputs."""

    connector_name = "fanatics"
    source = CollectibleMarketSource.FANATICS

    def normalize_record(
        self,
        raw_record: dict[str, Any],
    ) -> CollectibleMarketRecord:
        self._ensure_record(raw_record)
        return normalize_collectible_market_record(
            self.source,
            raw_record,
            record_prefix=self.connector_name,
        )
