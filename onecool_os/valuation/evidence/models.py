"""Models for provider-independent eBay Sold evidence."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any

from onecool_os.valuation.evidence.enums import EvidenceConfidence
from onecool_os.valuation.evidence.enums import EvidenceStatus
from onecool_os.valuation.evidence.enums import ListingType
from onecool_os.valuation.evidence.enums import MatchField
from onecool_os.valuation.evidence.validation import EvidenceError
from onecool_os.valuation.evidence.validation import optional_text
from onecool_os.valuation.evidence.validation import parse_bool
from onecool_os.valuation.evidence.validation import parse_date
from onecool_os.valuation.evidence.validation import parse_datetime
from onecool_os.valuation.evidence.validation import parse_dict
from onecool_os.valuation.evidence.validation import parse_enum
from onecool_os.valuation.evidence.validation import parse_optional_bool
from onecool_os.valuation.evidence.validation import parse_optional_decimal
from onecool_os.valuation.evidence.validation import parse_required_decimal
from onecool_os.valuation.evidence.validation import parse_string_tuple
from onecool_os.valuation.evidence.validation import require_currency
from onecool_os.valuation.evidence.validation import require_text

CORE_VERIFIED_FIELDS = frozenset(
    {
        MatchField.YEAR,
        MatchField.SET,
        MatchField.CARD_NUMBER,
        MatchField.SUBJECT,
        MatchField.GRADE_ISSUER,
        MatchField.GRADE,
    }
)
REJECTION_WARNINGS = frozenset(
    {
        "Active Listing Used",
        "Missing Sold URL",
        "Missing Item ID",
        "Grade Issuer Mismatch",
        "Grade Mismatch",
        "Card Number Mismatch",
        "Player Mismatch",
        "Parallel Mismatch",
        "Black Label Mismatch",
        "Malformed Price",
        "Malformed Date",
    }
)
REVIEW_WARNINGS = frozenset(
    {
        "Only One Sold Comp",
        "Incomplete Identity Match",
        "Best Offer Price Unconfirmed",
        "Shipping Amount Unknown",
        "Ambiguous Title",
        "Variety Missing From Title",
        "Stale Sold Date",
    }
)


@dataclass(frozen=True)
class EbaySoldEvidence:
    """One eBay Sold evidence observation from any provider."""

    evidence_id: str
    asset_id: str
    cert_number: str
    provider_name: str
    search_url: str
    sold_item_url: str | None
    ebay_item_id: str | None
    title: str
    sold_price: Decimal | str | int | float | None
    currency: str | None
    shipping_amount: Decimal | str | int | float | None = None
    sold_date: date | str | None = None
    listing_type: ListingType | str = ListingType.UNKNOWN
    best_offer_used: bool | None = None
    exact_match: bool = False
    matched_fields: tuple[MatchField | str, ...] | list[MatchField | str] = ()
    mismatched_fields: tuple[MatchField | str, ...] | list[MatchField | str] = ()
    confidence: EvidenceConfidence | str = EvidenceConfidence.UNVERIFIED
    status: EvidenceStatus | str = EvidenceStatus.NEEDS_REVIEW
    collected_at: datetime | str | None = None
    reference_datetime: datetime | str | None = None
    raw_metadata: dict[str, Any] | None = None
    warnings: tuple[str, ...] | list[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", require_text(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "asset_id", require_text(self.asset_id, "asset_id"))
        object.__setattr__(self, "cert_number", require_text(self.cert_number, "cert_number"))
        object.__setattr__(self, "provider_name", require_text(self.provider_name, "provider_name"))
        object.__setattr__(self, "search_url", require_text(self.search_url, "search_url"))
        object.__setattr__(self, "sold_item_url", optional_text(self.sold_item_url, "sold_item_url"))
        object.__setattr__(self, "ebay_item_id", optional_text(self.ebay_item_id, "ebay_item_id"))
        object.__setattr__(self, "title", require_text(self.title, "title"))
        object.__setattr__(self, "listing_type", parse_enum(ListingType, self.listing_type, "listing_type"))
        object.__setattr__(self, "best_offer_used", parse_optional_bool(self.best_offer_used, "best_offer_used"))
        object.__setattr__(self, "exact_match", parse_bool(self.exact_match, "exact_match"))
        object.__setattr__(self, "confidence", parse_enum(EvidenceConfidence, self.confidence, "confidence"))
        object.__setattr__(self, "status", parse_enum(EvidenceStatus, self.status, "status"))
        object.__setattr__(self, "raw_metadata", parse_dict(self.raw_metadata, "raw_metadata"))
        object.__setattr__(self, "warnings", parse_string_tuple(self.warnings, "warnings"))
        object.__setattr__(
            self,
            "matched_fields",
            _parse_match_fields(self.matched_fields, "matched_fields"),
        )
        object.__setattr__(
            self,
            "mismatched_fields",
            _parse_match_fields(self.mismatched_fields, "mismatched_fields"),
        )

        object.__setattr__(self, "sold_price", _parse_price(self.sold_price))
        object.__setattr__(
            self,
            "shipping_amount",
            parse_optional_decimal(self.shipping_amount, "shipping_amount"),
        )
        object.__setattr__(self, "currency", _parse_currency(self.currency))
        object.__setattr__(self, "sold_date", _parse_sold_date(self.sold_date))
        object.__setattr__(self, "collected_at", _parse_optional_datetime(self.collected_at, "collected_at"))
        object.__setattr__(
            self,
            "reference_datetime",
            _parse_optional_datetime(self.reference_datetime, "reference_datetime"),
        )

        status, confidence, warnings = _validated_state(self)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "warnings", tuple(dict.fromkeys((*self.warnings, *warnings))))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "evidence_id": self.evidence_id,
            "asset_id": self.asset_id,
            "cert_number": self.cert_number,
            "provider_name": self.provider_name,
            "search_url": self.search_url,
            "sold_item_url": self.sold_item_url,
            "ebay_item_id": self.ebay_item_id,
            "title": self.title,
            "sold_price": _format_decimal(self.sold_price),
            "currency": self.currency,
            "shipping_amount": _format_decimal(self.shipping_amount),
            "sold_date": self.sold_date.isoformat() if self.sold_date else None,
            "listing_type": self.listing_type.value,
            "best_offer_used": self.best_offer_used,
            "exact_match": self.exact_match,
            "matched_fields": [field.value for field in self.matched_fields],
            "mismatched_fields": [field.value for field in self.mismatched_fields],
            "confidence": self.confidence.value,
            "status": self.status.value,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
            "reference_datetime": (
                self.reference_datetime.isoformat()
                if self.reference_datetime
                else None
            ),
            "raw_metadata": dict(self.raw_metadata),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class EbaySoldEvidenceBatch:
    """A provider-generated eBay Sold evidence batch for one asset."""

    asset_id: str
    cert_number: str
    provider_name: str
    search_url: str
    search_queries: tuple[str, ...] | list[str]
    evidence: tuple[EbaySoldEvidence | dict[str, Any], ...] | list[EbaySoldEvidence | dict[str, Any]]
    warnings: tuple[str, ...] | list[str] = ()
    generated_at: datetime | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_id", require_text(self.asset_id, "asset_id"))
        object.__setattr__(self, "cert_number", require_text(self.cert_number, "cert_number"))
        object.__setattr__(self, "provider_name", require_text(self.provider_name, "provider_name"))
        object.__setattr__(self, "search_url", require_text(self.search_url, "search_url"))
        object.__setattr__(self, "search_queries", parse_string_tuple(self.search_queries, "search_queries"))
        object.__setattr__(self, "warnings", parse_string_tuple(self.warnings, "warnings"))
        object.__setattr__(self, "generated_at", _parse_optional_datetime(self.generated_at, "generated_at"))
        evidence = tuple(_coerce_evidence(item, self) for item in self.evidence)
        if len(evidence) == 1 and evidence[0].status == EvidenceStatus.VERIFIED:
            updated = replace(
                evidence[0],
                status=EvidenceStatus.NEEDS_REVIEW,
                confidence=min_confidence(evidence[0].confidence, EvidenceConfidence.MEDIUM),
                warnings=(*evidence[0].warnings, "Only One Sold Comp"),
            )
            evidence = (updated,)
        object.__setattr__(self, "evidence", evidence)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "asset_id": self.asset_id,
            "cert_number": self.cert_number,
            "provider_name": self.provider_name,
            "search_url": self.search_url,
            "search_queries": list(self.search_queries),
            "evidence": [item.to_dict() for item in self.evidence],
            "warnings": list(self.warnings),
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }


def _coerce_evidence(
    item: EbaySoldEvidence | dict[str, Any],
    batch: EbaySoldEvidenceBatch,
) -> EbaySoldEvidence:
    if isinstance(item, EbaySoldEvidence):
        return item
    if not isinstance(item, dict):
        raise EvidenceError("evidence items must be dictionaries or EbaySoldEvidence.")
    payload = {
        "asset_id": batch.asset_id,
        "cert_number": batch.cert_number,
        "provider_name": batch.provider_name,
        "search_url": batch.search_url,
        "reference_datetime": batch.generated_at,
        **item,
    }
    return EbaySoldEvidence(**payload)


def _validated_state(
    evidence: EbaySoldEvidence,
) -> tuple[EvidenceStatus, EvidenceConfidence, tuple[str, ...]]:
    warnings: list[str] = []
    rejection_reasons = _rejection_reasons(evidence)
    if rejection_reasons:
        return EvidenceStatus.REJECTED, EvidenceConfidence.UNVERIFIED, tuple(rejection_reasons)
    if evidence.status == EvidenceStatus.NO_MATCH:
        return EvidenceStatus.NO_MATCH, EvidenceConfidence.UNVERIFIED, ()

    review_reasons = _review_reasons(evidence)
    if evidence.status == EvidenceStatus.VERIFIED and not review_reasons and _is_verified(evidence):
        return EvidenceStatus.VERIFIED, evidence.confidence, ()

    if evidence.status == EvidenceStatus.VERIFIED and not _is_verified(evidence):
        warnings.append("Incomplete Identity Match")
    warnings.extend(review_reasons)
    return (
        EvidenceStatus.NEEDS_REVIEW,
        min_confidence(evidence.confidence, EvidenceConfidence.MEDIUM),
        tuple(warnings),
    )


def _is_verified(evidence: EbaySoldEvidence) -> bool:
    if not evidence.exact_match:
        return False
    if evidence.sold_price is None or evidence.currency is None or evidence.sold_date is None:
        return False
    if not evidence.ebay_item_id or not evidence.sold_item_url:
        return False
    if evidence.mismatched_fields:
        return False
    matched = set(evidence.matched_fields)
    if not CORE_VERIFIED_FIELDS <= matched:
        return False
    if _expects_variety(evidence) and MatchField.VARIETY not in matched:
        return False
    if _expects_special_designation(evidence) and MatchField.SPECIAL_DESIGNATION not in matched:
        return False
    return True


def _rejection_reasons(evidence: EbaySoldEvidence) -> tuple[str, ...]:
    reasons = []
    metadata = evidence.raw_metadata
    if str(metadata.get("listing_status", "")).upper() == "ACTIVE":
        reasons.append("Active Listing Used")
    if not evidence.sold_item_url:
        reasons.append("Missing Sold URL")
    if not evidence.ebay_item_id:
        reasons.append("Missing Item ID")
    if evidence.sold_price is None:
        reasons.append("Malformed Price")
    if evidence.sold_date is None:
        reasons.append("Malformed Date")
    mismatched = set(evidence.mismatched_fields)
    mismatch_reasons = {
        MatchField.GRADE_ISSUER: "Grade Issuer Mismatch",
        MatchField.GRADE: "Grade Mismatch",
        MatchField.CARD_NUMBER: "Card Number Mismatch",
        MatchField.SUBJECT: "Player Mismatch",
        MatchField.VARIETY: "Parallel Mismatch",
        MatchField.SPECIAL_DESIGNATION: "Black Label Mismatch",
    }
    for field, reason in mismatch_reasons.items():
        if field in mismatched:
            reasons.append(reason)
    if _expects_special_designation(evidence) and MatchField.SPECIAL_DESIGNATION not in set(evidence.matched_fields):
        reasons.append("Black Label Mismatch")
    for warning in evidence.warnings:
        if warning in REJECTION_WARNINGS:
            reasons.append(warning)
    return tuple(dict.fromkeys(reasons))


def _review_reasons(evidence: EbaySoldEvidence) -> tuple[str, ...]:
    reasons = []
    metadata = evidence.raw_metadata
    if evidence.best_offer_used and metadata.get("best_offer_price_confirmed") is not True:
        reasons.append("Best Offer Price Unconfirmed")
    if evidence.shipping_amount is None:
        reasons.append("Shipping Amount Unknown")
    if metadata.get("title_ambiguous") is True:
        reasons.append("Ambiguous Title")
    if metadata.get("variety_missing_from_title") is True:
        reasons.append("Variety Missing From Title")
    if metadata.get("stale") is True:
        reasons.append("Stale Sold Date")
    if not evidence.exact_match:
        reasons.append("Incomplete Identity Match")
    if _expects_variety(evidence) and MatchField.VARIETY not in set(evidence.matched_fields):
        reasons.append("Variety Missing From Title")
    for warning in evidence.warnings:
        if warning in REVIEW_WARNINGS:
            reasons.append(warning)
    return tuple(dict.fromkeys(reasons))


def _expects_variety(evidence: EbaySoldEvidence) -> bool:
    value = evidence.raw_metadata.get("variety_expected")
    return bool(value and str(value).strip() not in {"-", "NONE", "N/A"})


def _expects_special_designation(evidence: EbaySoldEvidence) -> bool:
    value = evidence.raw_metadata.get("special_designation_expected")
    return bool(value and "BLACK LABEL" in str(value).upper())


def _parse_match_fields(value: Any, field_name: str) -> tuple[MatchField, ...]:
    items = parse_string_tuple(value, field_name)
    return tuple(parse_enum(MatchField, item, field_name) for item in items)


def _parse_price(value: Any) -> Decimal | None:
    try:
        return parse_required_decimal(value, "sold_price")
    except EvidenceError:
        return None


def _parse_currency(value: Any) -> str | None:
    try:
        return require_currency(value)
    except EvidenceError:
        return None


def _parse_sold_date(value: Any) -> date | None:
    try:
        return parse_date(value, "sold_date")
    except EvidenceError:
        return None


def _parse_optional_datetime(value: Any, field_name: str) -> datetime | None:
    if value in (None, ""):
        return None
    return parse_datetime(value, field_name)


def min_confidence(
    confidence: EvidenceConfidence,
    ceiling: EvidenceConfidence,
) -> EvidenceConfidence:
    """Return the lower confidence by deterministic rank."""

    rank = {
        EvidenceConfidence.HIGH: 3,
        EvidenceConfidence.MEDIUM: 2,
        EvidenceConfidence.LOW: 1,
        EvidenceConfidence.UNVERIFIED: 0,
    }
    return confidence if rank[confidence] <= rank[ceiling] else ceiling


def _format_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}"
