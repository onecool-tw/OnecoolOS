"""Collectible market record to valuation record mapping."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from onecool_os.connectors.collectibles.enums import CollectibleMarketSource
from onecool_os.connectors.collectibles.enums import CollectibleSourceRole
from onecool_os.connectors.collectibles.enums import source_role_for_source
from onecool_os.connectors.collectibles.models import CollectibleMarketRecord
from onecool_os.valuation.enums import ValuationConfidence
from onecool_os.valuation.enums import ValuationSource
from onecool_os.valuation.models import ValuationRecord
from onecool_os.valuation.validation import ValuationError


@dataclass(frozen=True)
class CollectibleValuationMapping:
    """ValuationRecord plus collectible source metadata."""

    valuation_record: ValuationRecord
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation for downstream layers."""

        return {
            "valuation_record": self.valuation_record.to_dict(),
            "metadata": self.metadata,
        }


class CollectibleValuationMapper:
    """Map collectible market records into valuation history records."""

    asset_type = "SPORTS_CARD"
    default_confidence = ValuationConfidence.LOW

    def map_record(
        self,
        market_record: CollectibleMarketRecord,
        *,
        asset_id: str | None = None,
    ) -> CollectibleValuationMapping:
        """Map one collectible market record without resolving consensus."""

        if not isinstance(market_record, CollectibleMarketRecord):
            raise ValuationError(
                "market_record must be a CollectibleMarketRecord."
            )
        if market_record.sale_price is None:
            raise ValuationError("sale_price is required.")
        if market_record.currency is None:
            raise ValuationError("currency is required.")
        if market_record.sale_date is None:
            raise ValuationError("sale_date is required.")

        source_role = source_role_for_source(market_record.source)
        valuation_record = ValuationRecord(
            valuation_id=self._valuation_id_for(market_record),
            asset_id=asset_id or self._asset_id_for(market_record),
            asset_type=self.asset_type,
            source=self._valuation_source_for(market_record.source),
            currency=market_record.currency,
            valuation_date=market_record.sale_date,
            confidence=self.default_confidence,
            market_value=market_record.sale_price,
            url=market_record.url,
            tags=["collectible", "market-record"],
        )
        metadata = {
            "primary_market_price": (
                source_role == CollectibleSourceRole.PRIMARY_MARKET_PRICE
            ),
            "validation_source": (
                source_role == CollectibleSourceRole.VALIDATION_SOURCE
            ),
            "source_agreement_status": None,
            "source_role": source_role.value,
            "raw_market_record_id": market_record.record_id,
            "external_id": market_record.external_id,
            "sale_price": f"{market_record.sale_price}",
            "currency": market_record.currency,
            "sale_date": market_record.sale_date.isoformat(),
            "url": market_record.url,
            "raw_payload": (
                dict(market_record.raw_payload)
                if market_record.raw_payload is not None
                else None
            ),
        }
        return CollectibleValuationMapping(
            valuation_record=valuation_record,
            metadata=metadata,
        )

    def to_dict(
        self,
        market_record: CollectibleMarketRecord,
        *,
        asset_id: str | None = None,
    ) -> dict[str, Any]:
        """Map one record and return a JSON-safe dictionary."""

        return self.map_record(market_record, asset_id=asset_id).to_dict()

    def _valuation_id_for(self, market_record: CollectibleMarketRecord) -> str:
        return f"collectible:{market_record.record_id}"

    def _asset_id_for(self, market_record: CollectibleMarketRecord) -> str:
        if market_record.external_id:
            return f"collectible:{market_record.external_id}"
        return f"collectible:{market_record.record_id}"

    def _valuation_source_for(
        self,
        source: CollectibleMarketSource | str,
    ) -> ValuationSource:
        normalized_source = (
            source
            if isinstance(source, CollectibleMarketSource)
            else CollectibleMarketSource(str(source).upper())
        )
        return ValuationSource(normalized_source.value)
