"""Deterministic normalization and evidence bridge helpers for ORF."""

from __future__ import annotations

from typing import Any

from onecool_os.research.enums import ResearchConfidence
from onecool_os.research.enums import ResearchStatus
from onecool_os.research.enums import ResearchType
from onecool_os.research.models import ResearchEvidence
from onecool_os.research.models import ResearchResult
from onecool_os.research.validation import ResearchError
from onecool_os.research.validation import parse_optional_date
from onecool_os.research.validation import parse_optional_url
from onecool_os.research.validation import require_currency
from onecool_os.research.validation import require_text
from onecool_os.research.validation import validate_provider_version
from onecool_os.valuation.evidence import EbaySoldEvidence
from onecool_os.valuation.evidence import EvidenceConfidence
from onecool_os.valuation.evidence import EvidenceStatus
from onecool_os.valuation.evidence import MatchField


def normalize_provider_name(value: str) -> str:
    """Normalize a provider name for registry-style use."""

    return require_text(value, "provider_name").strip().lower()


def normalize_provider_version(value: str) -> str:
    """Validate and return a provider version."""

    return validate_provider_version(value)


def normalize_confidence(value: str | ResearchConfidence) -> ResearchConfidence:
    """Normalize confidence without upgrading it."""

    if isinstance(value, ResearchConfidence):
        return value
    return ResearchConfidence(str(value).upper())


def normalize_status(value: str | ResearchStatus) -> ResearchStatus:
    """Normalize research status."""

    if isinstance(value, ResearchStatus):
        return value
    return ResearchStatus(str(value).upper())


def normalize_url(value: str | None, field_name: str = "url") -> str | None:
    """Normalize an optional URL."""

    return parse_optional_url(value, field_name)


def normalize_currency(value: str) -> str:
    """Normalize a currency code."""

    return require_currency(value)


def normalize_date(value: Any, field_name: str = "date") -> Any:
    """Normalize an optional date value."""

    return parse_optional_date(value, field_name)


def normalize_evidence_identifier(value: str) -> str:
    """Normalize an evidence identifier."""

    return require_text(value, "evidence_id")


def normalize_warnings(value: Any) -> tuple[str, ...]:
    """Normalize warning messages while preserving order."""

    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise ResearchError("warnings must be a list.")
    return tuple(dict.fromkeys(require_text(item, "warnings") for item in value))


def research_evidence_to_ebay_sold_evidence(
    result: ResearchResult,
    evidence: ResearchEvidence,
    *,
    search_url: str | None = None,
) -> EbaySoldEvidence:
    """Bridge compatible ORF SOLD_COMPARABLES evidence into eBay evidence.

    The bridge creates an EbaySoldEvidence object and lets the existing eBay
    evidence layer decide whether it is verified, review-only, or rejected.
    """

    if result.research_type != ResearchType.SOLD_COMPARABLES:
        raise ResearchError("Only SOLD_COMPARABLES results can bridge to eBay evidence.")
    if evidence.evidence_type != ResearchType.SOLD_COMPARABLES:
        raise ResearchError("Only SOLD_COMPARABLES evidence can bridge to eBay evidence.")
    if not result.asset_id:
        raise ResearchError("asset_id is required for eBay evidence bridge.")
    if not result.cert_number:
        raise ResearchError("cert_number is required for eBay evidence bridge.")
    if not evidence.title:
        raise ResearchError("title is required for eBay evidence bridge.")
    resolved_search_url = (
        search_url
        or result.provider_metadata.get("search_url")
        or evidence.raw_metadata.get("search_url")
        or evidence.source_url
    )
    if not resolved_search_url:
        raise ResearchError("search_url is required for eBay evidence bridge.")

    raw_metadata = {
        **dict(evidence.raw_metadata),
        "orf_result_id": result.result_id,
        "orf_request_id": result.request_id,
        "provider_type": result.provider_type.value,
        "provider_version": result.provider_version,
        "provider_metadata": dict(result.provider_metadata),
    }
    return EbaySoldEvidence(
        evidence_id=evidence.evidence_id,
        asset_id=result.asset_id,
        cert_number=result.cert_number,
        provider_name=result.provider_name,
        search_url=resolved_search_url,
        sold_item_url=evidence.source_url,
        ebay_item_id=evidence.item_id,
        title=evidence.title,
        sold_price=evidence.observed_value,
        currency=evidence.currency,
        shipping_amount=evidence.raw_metadata.get("shipping_amount"),
        sold_date=evidence.observed_date,
        listing_type=evidence.raw_metadata.get("listing_type", "UNKNOWN"),
        best_offer_used=evidence.raw_metadata.get("best_offer_used"),
        exact_match=bool(evidence.exact_match),
        matched_fields=_bridge_match_fields(evidence.matched_fields),
        mismatched_fields=_bridge_match_fields(evidence.mismatched_fields),
        confidence=_bridge_confidence(evidence.confidence),
        status=_bridge_status(evidence.status),
        collected_at=evidence.created_at,
        reference_datetime=result.reference_datetime,
        raw_metadata=raw_metadata,
        warnings=evidence.warnings,
    )


def _bridge_confidence(confidence: ResearchConfidence) -> EvidenceConfidence:
    return EvidenceConfidence(confidence.value)


def _bridge_status(status: ResearchStatus) -> EvidenceStatus:
    if status == ResearchStatus.COMPLETED:
        return EvidenceStatus.VERIFIED
    if status == ResearchStatus.NO_MATCH:
        return EvidenceStatus.NO_MATCH
    if status == ResearchStatus.FAILED:
        return EvidenceStatus.REJECTED
    return EvidenceStatus.NEEDS_REVIEW


def _bridge_match_fields(fields: tuple[str, ...]) -> tuple[str, ...]:
    values = {field.value for field in MatchField}
    return tuple(field for field in fields if field in values)
