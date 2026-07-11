"""Research workbench models for eBay Sold URL PoC."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from onecool_os.research.enums import ResearchCapability
from onecool_os.research.validation import ResearchError
from onecool_os.research.workbench.validation import parse_dict
from onecool_os.research.workbench.validation import parse_enum
from onecool_os.research.workbench.validation import parse_string_tuple
from onecool_os.research.workbench.validation import parse_url
from onecool_os.research.workbench.validation import require_text
from onecool_os.research.workbench.validation import optional_text
from onecool_os.research.workbench.validation import parse_datetime
from onecool_os.research.workbench.validation import parse_optional_datetime
from onecool_os.valuation.evidence import EbaySoldEvidence
from onecool_os.valuation.evidence import EbaySoldEvidenceBatch

REQUIRED_EBAY_SOLD_REQUEST_FIELDS = (
    "sold_item_url",
    "ebay_item_id",
    "title",
    "sold_price",
    "currency",
    "sold_date",
    "listing_type",
    "best_offer_used",
    "shipping_amount",
    "exact_match",
    "matched_fields",
    "mismatched_fields",
    "confidence",
    "warnings",
)

EBAY_RESEARCH_PROVIDER_INSTRUCTION = (
    "You are an eBay Sold research agent.\n\n"
    "Use only the provided eBay Sold Search URL.\n\n"
    "Do not invent results.\n\n"
    "Return structured JSON only.\n\n"
    "For each sold comp provide:\n"
    "- sold item URL\n"
    "- eBay item ID\n"
    "- title\n"
    "- sold price\n"
    "- currency\n"
    "- sold date\n"
    "- listing type\n"
    "- Best Offer status if known\n"
    "- shipping if known\n"
    "- exact-match determination\n"
    "- matched and mismatched identity fields\n"
    "- confidence\n"
    "- warnings\n\n"
    "If no exact sold comp can be verified, return NO_MATCH.\n\n"
    "Do not calculate portfolio NAV.\n"
    "Do not make buy/sell recommendations."
)


@dataclass(frozen=True)
class EbayUrlResearchRequest:
    """One immutable eBay Sold URL research request package."""

    request_id: str
    asset_id: str
    asset_name: str
    grade_issuer: str
    grade: str
    year: str
    set_name: str
    card_number: str
    subject: str
    ebay_sold_search_url: str
    requested_fields: tuple[str, ...] | list[str]
    provider_capability_required: ResearchCapability | str
    reference_datetime: datetime | str
    cert_number: str | None = None
    variety: str | None = None
    special_designation: str | None = None
    created_at: datetime | str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", require_text(self.request_id, "request_id"))
        object.__setattr__(self, "asset_id", require_text(self.asset_id, "asset_id"))
        object.__setattr__(self, "cert_number", optional_text(self.cert_number, "cert_number"))
        object.__setattr__(self, "asset_name", require_text(self.asset_name, "asset_name"))
        object.__setattr__(self, "grade_issuer", require_text(self.grade_issuer, "grade_issuer"))
        object.__setattr__(self, "grade", require_text(self.grade, "grade"))
        object.__setattr__(self, "year", require_text(self.year, "year"))
        object.__setattr__(self, "set_name", require_text(self.set_name, "set_name"))
        object.__setattr__(self, "card_number", require_text(self.card_number, "card_number"))
        object.__setattr__(self, "subject", require_text(self.subject, "subject"))
        object.__setattr__(self, "variety", optional_text(self.variety, "variety"))
        object.__setattr__(
            self,
            "special_designation",
            optional_text(self.special_designation, "special_designation"),
        )
        object.__setattr__(self, "ebay_sold_search_url", parse_url(self.ebay_sold_search_url, "ebay_sold_search_url"))
        fields = parse_string_tuple(self.requested_fields, "requested_fields")
        missing = sorted(set(REQUIRED_EBAY_SOLD_REQUEST_FIELDS) - set(fields))
        if missing:
            raise ResearchError(f"requested_fields missing required fields: {', '.join(missing)}")
        object.__setattr__(self, "requested_fields", fields)
        object.__setattr__(
            self,
            "provider_capability_required",
            parse_enum(ResearchCapability, self.provider_capability_required, "provider_capability_required"),
        )
        object.__setattr__(
            self,
            "reference_datetime",
            parse_datetime(self.reference_datetime, "reference_datetime"),
        )
        object.__setattr__(self, "created_at", parse_optional_datetime(self.created_at, "created_at"))
        object.__setattr__(self, "metadata", parse_dict(self.metadata, "metadata"))

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe request data."""

        return {
            "request_id": self.request_id,
            "asset_id": self.asset_id,
            "cert_number": self.cert_number,
            "asset_name": self.asset_name,
            "grade_issuer": self.grade_issuer,
            "grade": self.grade,
            "year": self.year,
            "set_name": self.set_name,
            "card_number": self.card_number,
            "subject": self.subject,
            "variety": self.variety,
            "special_designation": self.special_designation,
            "ebay_sold_search_url": self.ebay_sold_search_url,
            "requested_fields": list(self.requested_fields),
            "provider_capability_required": self.provider_capability_required.value,
            "provider_instruction": EBAY_RESEARCH_PROVIDER_INSTRUCTION,
            "reference_datetime": self.reference_datetime.isoformat(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class EbayUrlResearchRequestExport:
    """A deterministic export package for eBay URL research requests."""

    export_id: str
    requests: tuple[EbayUrlResearchRequest, ...] | list[EbayUrlResearchRequest]
    generated_at: datetime | str
    reference_datetime: datetime | str
    warnings: tuple[str, ...] | list[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "export_id", require_text(self.export_id, "export_id"))
        object.__setattr__(self, "requests", tuple(self.requests))
        object.__setattr__(self, "generated_at", parse_datetime(self.generated_at, "generated_at"))
        object.__setattr__(
            self,
            "reference_datetime",
            parse_datetime(self.reference_datetime, "reference_datetime"),
        )
        object.__setattr__(self, "warnings", parse_string_tuple(self.warnings, "warnings"))

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe export data."""

        return {
            "export_id": self.export_id,
            "request_count": len(self.requests),
            "requests": [request.to_dict() for request in self.requests],
            "warnings": list(self.warnings),
            "generated_at": self.generated_at.isoformat(),
            "reference_datetime": self.reference_datetime.isoformat(),
        }


@dataclass(frozen=True)
class ResearchWorkbenchImportResult:
    """Result of importing ORF-compatible provider output."""

    source_file: str
    batches: tuple[Any, ...]
    evidence_batches: tuple[EbaySoldEvidenceBatch, ...]
    evidence: tuple[EbaySoldEvidence, ...]
    warnings: tuple[str, ...]

    @property
    def evidence_count(self) -> int:
        """Return total eBay evidence records produced by the bridge."""

        return len(self.evidence)
