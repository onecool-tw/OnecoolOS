"""eBay Sold evidence enumerations."""

from __future__ import annotations

from enum import StrEnum


class EvidenceStatus(StrEnum):
    """Validation status for a market evidence observation."""

    VERIFIED = "VERIFIED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECTED = "REJECTED"
    NO_MATCH = "NO_MATCH"


class EvidenceConfidence(StrEnum):
    """Provider/evidence confidence after deterministic validation."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNVERIFIED = "UNVERIFIED"


class ListingType(StrEnum):
    """Supported sold listing types."""

    AUCTION = "AUCTION"
    BUY_IT_NOW = "BUY_IT_NOW"
    BEST_OFFER = "BEST_OFFER"
    UNKNOWN = "UNKNOWN"


class MatchField(StrEnum):
    """Collectible identity fields used to validate an eBay Sold comp."""

    YEAR = "YEAR"
    SET = "SET"
    CARD_NUMBER = "CARD_NUMBER"
    SUBJECT = "SUBJECT"
    VARIETY = "VARIETY"
    GRADE_ISSUER = "GRADE_ISSUER"
    GRADE = "GRADE"
    SPECIAL_DESIGNATION = "SPECIAL_DESIGNATION"
