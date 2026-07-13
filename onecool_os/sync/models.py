"""Collection synchronization report models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


DIFFERENCE_TYPES = frozenset(
    {
        "NEW_CARD",
        "MISSING_IN_IMPORT",
        "MISSING_IN_ASSET_MASTER",
        "DUPLICATE_CERT",
        "DUPLICATE_ASSET",
        "YEAR_CHANGED",
        "SET_CHANGED",
        "CARD_NUMBER_CHANGED",
        "PLAYER_CHANGED",
        "GRADE_CHANGED",
        "GRADE_ISSUER_CHANGED",
        "VARIETY_CHANGED",
        "COST_OVERRIDE",
        "EBAY_URL_MISSING",
        "PSA_URL_MISSING",
        "TARGET_PRICE_MISSING",
        "NOTES_CHANGED",
    }
)
SYNC_SEVERITIES = frozenset(("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"))
TRUST_CATEGORIES = frozenset(
    ("IDENTITY", "NORMALIZATION", "METADATA", "DECISION", "EVIDENCE")
)
HEALTH_STATES = frozenset(("EXCELLENT", "GOOD", "FAIR", "ATTENTION", "CRITICAL"))

IDENTITY_DIFFERENCE_TYPES = frozenset(
    {
        "NEW_CARD",
        "MISSING_IN_IMPORT",
        "MISSING_IN_ASSET_MASTER",
        "DUPLICATE_CERT",
        "DUPLICATE_ASSET",
        "YEAR_CHANGED",
        "SET_CHANGED",
        "CARD_NUMBER_CHANGED",
        "PLAYER_CHANGED",
        "GRADE_CHANGED",
        "GRADE_ISSUER_CHANGED",
    }
)
NORMALIZATION_DIFFERENCE_TYPES = frozenset(("VARIETY_CHANGED",))
METADATA_DIFFERENCE_TYPES = frozenset(("PSA_URL_MISSING",))
DECISION_DIFFERENCE_TYPES = frozenset(
    ("COST_OVERRIDE", "TARGET_PRICE_MISSING", "NOTES_CHANGED")
)
EVIDENCE_DIFFERENCE_TYPES = frozenset(("EBAY_URL_MISSING",))


@dataclass(frozen=True)
class CollectionDifference:
    """One deterministic difference found during collection sync."""

    cert_number: str
    difference_type: str
    severity: str
    source_value: Any
    target_value: Any
    description: str
    asset_id: str | None = None
    trust_category: str | None = None
    recommended_action: str | None = None

    def __post_init__(self) -> None:
        if self.difference_type not in DIFFERENCE_TYPES:
            raise ValueError(f"Invalid difference_type: {self.difference_type}")
        if self.severity not in SYNC_SEVERITIES:
            raise ValueError(f"Invalid severity: {self.severity}")
        trust_category = self.trust_category or trust_category_for_difference(
            self.difference_type
        )
        if trust_category not in TRUST_CATEGORIES:
            raise ValueError(f"Invalid trust_category: {trust_category}")
        object.__setattr__(self, "cert_number", str(self.cert_number or ""))
        object.__setattr__(self, "asset_id", _optional_text(self.asset_id))
        object.__setattr__(self, "description", str(self.description))
        object.__setattr__(self, "trust_category", trust_category)
        object.__setattr__(
            self,
            "recommended_action",
            self.recommended_action
            or recommended_action_for_category(trust_category),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary."""

        return {
            "cert_number": self.cert_number,
            "asset_id": self.asset_id,
            "difference_type": self.difference_type,
            "severity": self.severity,
            "source_value": self.source_value,
            "target_value": self.target_value,
            "description": self.description,
            "trust_category": self.trust_category,
            "recommended_action": self.recommended_action,
        }


@dataclass(frozen=True)
class SyncReport:
    """Deterministic collection synchronization report."""

    imported_records: int
    asset_master_records: int
    matched_records: int
    differences: tuple[CollectionDifference, ...]
    warnings: tuple[str, ...]
    collection_health: int
    generated_at: datetime
    health_state: str | None = None
    health_explanation: str | None = None
    health_components: dict[str, Any] | None = None
    issue_groups: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.generated_at, datetime):
            raise ValueError("generated_at must be a datetime.")
        object.__setattr__(self, "differences", tuple(self.differences))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        health = max(0, min(100, int(self.collection_health)))
        health_state = self.health_state or health_state_for_score(health)
        if health_state not in HEALTH_STATES:
            raise ValueError(f"Invalid health_state: {health_state}")
        object.__setattr__(self, "collection_health", health)
        object.__setattr__(self, "health_state", health_state)
        object.__setattr__(
            self,
            "health_explanation",
            self.health_explanation or health_explanation(health_state),
        )
        object.__setattr__(
            self,
            "health_components",
            dict(self.health_components or {}),
        )
        object.__setattr__(self, "issue_groups", dict(self.issue_groups or {}))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary."""

        return {
            "imported_records": self.imported_records,
            "asset_master_records": self.asset_master_records,
            "matched_records": self.matched_records,
            "differences": [
                difference.to_dict() for difference in self.differences
            ],
            "warnings": list(self.warnings),
            "collection_health": self.collection_health,
            "generated_at": self.generated_at.isoformat(),
            "health_state": self.health_state,
            "health_explanation": self.health_explanation,
            "health_components": self.health_components,
            "issue_groups": self.issue_groups,
        }


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def trust_category_for_difference(difference_type: str) -> str:
    """Return the trust category for a difference type."""

    if difference_type in IDENTITY_DIFFERENCE_TYPES:
        return "IDENTITY"
    if difference_type in NORMALIZATION_DIFFERENCE_TYPES:
        return "NORMALIZATION"
    if difference_type in METADATA_DIFFERENCE_TYPES:
        return "METADATA"
    if difference_type in DECISION_DIFFERENCE_TYPES:
        return "DECISION"
    if difference_type in EVIDENCE_DIFFERENCE_TYPES:
        return "EVIDENCE"
    return "METADATA"


def recommended_action_for_category(category: str) -> str:
    """Return a concise review action for a trust category."""

    return {
        "IDENTITY": "Review identity before trusting runtime output.",
        "NORMALIZATION": "Review normalization mapping when convenient.",
        "METADATA": "Complete durable Asset Master metadata.",
        "DECISION": "Review in the Decision Layer; no health action required.",
        "EVIDENCE": "Prepare evidence research inputs.",
    }[category]


def health_state_for_score(score: int) -> str:
    """Return the collection health state for a score."""

    if score >= 95:
        return "EXCELLENT"
    if score >= 85:
        return "GOOD"
    if score >= 70:
        return "FAIR"
    if score >= 50:
        return "ATTENTION"
    return "CRITICAL"


def health_explanation(state: str) -> str:
    """Return a short explanation for a health state."""

    return {
        "EXCELLENT": "Collection data is highly trustworthy.",
        "GOOD": "Collection data is trustworthy with minor cleanup remaining.",
        "FAIR": "Collection data is usable, but review is recommended.",
        "ATTENTION": "Collection data needs review before full trust.",
        "CRITICAL": "Collection data has trust issues that must be resolved.",
    }[state]
