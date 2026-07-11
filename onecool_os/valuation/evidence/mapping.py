"""Map verified eBay Sold evidence into valuation records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from onecool_os.connectors.collectibles.enums import CollectibleSourceRole
from onecool_os.valuation.enums import ValuationConfidence
from onecool_os.valuation.enums import ValuationSource
from onecool_os.valuation.evidence.enums import EvidenceConfidence
from onecool_os.valuation.evidence.enums import EvidenceStatus
from onecool_os.valuation.evidence.models import EbaySoldEvidence
from onecool_os.valuation.evidence.validation import EvidenceError
from onecool_os.valuation.models import ValuationRecord


@dataclass(frozen=True)
class EbaySoldEvidenceValuationMapping:
    """ValuationRecord plus eBay Sold evidence metadata."""

    valuation_record: ValuationRecord
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "valuation_record": self.valuation_record.to_dict(),
            "metadata": dict(self.metadata),
        }


class EbaySoldEvidenceMapper:
    """Map verified eBay Sold evidence without selecting a final price."""

    asset_type = "SPORTS_CARD"

    def map_evidence(
        self,
        evidence: EbaySoldEvidence,
    ) -> EbaySoldEvidenceValuationMapping:
        """Map one verified evidence record into a ValuationRecord."""

        if not isinstance(evidence, EbaySoldEvidence):
            raise EvidenceError("evidence must be an EbaySoldEvidence.")
        if evidence.status != EvidenceStatus.VERIFIED:
            raise EvidenceError("Only VERIFIED eBay Sold evidence can be mapped.")
        if evidence.sold_price is None or evidence.currency is None or evidence.sold_date is None:
            raise EvidenceError("Verified evidence is missing valuation fields.")

        valuation_record = ValuationRecord(
            valuation_id=f"ebay-sold:{evidence.evidence_id}",
            asset_id=evidence.asset_id,
            asset_type=self.asset_type,
            source=ValuationSource.EBAY_SOLD,
            currency=evidence.currency,
            market_value=evidence.sold_price,
            valuation_date=evidence.sold_date,
            confidence=_valuation_confidence(evidence.confidence),
            url=evidence.sold_item_url,
            tags=["collectible", "ebay-sold", "evidence"],
        )
        metadata = {
            "source_role": CollectibleSourceRole.PRIMARY_MARKET_PRICE.value,
            "evidence_id": evidence.evidence_id,
            "provider_name": evidence.provider_name,
            "ebay_item_id": evidence.ebay_item_id,
            "sold_item_url": evidence.sold_item_url,
            "sold_date": evidence.sold_date.isoformat(),
            "evidence_confidence": evidence.confidence.value,
            "evidence_status": evidence.status.value,
            "search_url": evidence.search_url,
        }
        return EbaySoldEvidenceValuationMapping(
            valuation_record=valuation_record,
            metadata=metadata,
        )


def _valuation_confidence(confidence: EvidenceConfidence) -> ValuationConfidence:
    if confidence == EvidenceConfidence.HIGH:
        return ValuationConfidence.HIGH
    if confidence == EvidenceConfidence.MEDIUM:
        return ValuationConfidence.MEDIUM
    return ValuationConfidence.LOW
