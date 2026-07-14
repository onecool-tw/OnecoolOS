"""Interactive builder for Work Response JSON files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from onecool_os.work.models import WORK_CONTRACT_SCHEMA_VERSION
from onecool_os.work.models import WorkRequest
from onecool_os.work.models import WorkResponse
from onecool_os.work.validation import WorkContractError

IDENTITY_FIELDS = (
    "YEAR",
    "SET",
    "CARD_NUMBER",
    "SUBJECT",
    "GRADE_ISSUER",
    "GRADE",
)


@dataclass(frozen=True)
class SoldComparableInput:
    """Manual input for one verified eBay sold comparable."""

    ebay_item_id: str
    sold_item_url: str
    title: str
    sold_price: str
    currency: str
    sold_date: str
    listing_type: str
    best_offer_used: bool | None
    shipping_amount: str | None
    exact_match: bool
    warnings: tuple[str, ...] = ()


class WorkResponseBuilder:
    """Build Work Response JSON from manually verified comparable inputs."""

    def load_request(self, request_path: str | Path) -> WorkRequest:
        """Load a Work Request JSON file."""

        path = Path(request_path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkContractError(f"Work Request load failed: {exc}") from exc
        return WorkRequest(**payload)

    def build_response(
        self,
        request: WorkRequest,
        comparables: tuple[SoldComparableInput, ...] | list[SoldComparableInput],
        *,
        provider: str = "Manual Work Response Builder",
        completed_at: datetime | None = None,
    ) -> WorkResponse:
        """Build a Work Response from manual comparable inputs."""

        completed = completed_at or datetime.now(UTC)
        comparable_tuple = tuple(comparables)
        orf_payload = self._orf_payload(
            request,
            comparable_tuple,
            provider=provider,
            generated_at=completed,
        )
        warnings = ("NO_MATCH",) if not comparable_tuple else ()
        return WorkResponse(
            schema_version=WORK_CONTRACT_SCHEMA_VERSION,
            request_id=request.request_id,
            status="COMPLETED",
            provider=provider,
            completed_at=completed,
            execution_time={"duration_seconds": 0},
            outputs={"orf_payload": orf_payload},
            warnings=warnings,
            errors=(),
        )

    def write_response(self, response: WorkResponse, output_path: str | Path) -> Path:
        """Write a Work Response JSON file."""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(response.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def build_interactive(
        self,
        request_path: str | Path,
        output_path: str | Path,
        *,
        input_func=None,
        print_func=None,
        completed_at: datetime | None = None,
    ) -> WorkResponse:
        """Run an interactive prompt and write the Work Response JSON."""

        resolved_input = input if input_func is None else input_func
        resolved_print = print if print_func is None else print_func
        request = self.load_request(request_path)
        research_request = _research_request(request)
        resolved_print("Onecool Interactive Work Response Builder")
        resolved_print("-----------------------------------------")
        resolved_print(f"Asset Name: {research_request.get('asset_name') or request.asset_id}")
        resolved_print(f"Cert Number: {research_request.get('cert_number') or ''}")
        resolved_print(f"Research URL: {_research_url(request)}")
        resolved_print("")

        count = _prompt_count(resolved_input)
        comparables = tuple(_prompt_comparable(resolved_input, index) for index in range(1, count + 1))
        response = self.build_response(
            request,
            comparables,
            completed_at=completed_at,
        )
        self.write_response(response, output_path)
        resolved_print("")
        resolved_print(f"Work Response written: {output_path}")
        resolved_print(f"Comparables: {len(comparables)}")
        resolved_print("Fair Value calculated: 0")
        resolved_print("Valuation records created: 0")
        resolved_print("NAV updated: 0")
        return response

    def _orf_payload(
        self,
        request: WorkRequest,
        comparables: tuple[SoldComparableInput, ...],
        *,
        provider: str,
        generated_at: datetime,
    ) -> dict[str, Any]:
        research_request = _research_request(request)
        request_id = str(research_request.get("request_id") or request.request_id)
        asset_id = str(research_request.get("asset_id") or request.asset_id or "")
        cert_number = str(research_request.get("cert_number") or "")
        status = "COMPLETED" if comparables else "NO_MATCH"
        confidence = _result_confidence(comparables)
        warnings = [] if comparables else ["NO_MATCH"]

        return {
            "batch_id": f"batch-{request_id}",
            "provider_name": provider,
            "results": [
                {
                    "result_id": f"result-{request_id}",
                    "request_id": request_id,
                    "provider_name": provider,
                    "provider_type": "MANUAL",
                    "provider_version": "v1",
                    "capabilities": ["SOLD_COMPARABLES"],
                    "research_type": "SOLD_COMPARABLES",
                    "asset_id": asset_id,
                    "cert_number": cert_number,
                    "status": status,
                    "confidence": confidence,
                    "evidence": [
                        _evidence_payload(comparable, request_id, generated_at)
                        for comparable in comparables
                    ],
                    "normalized_payload": {},
                    "warnings": warnings,
                    "provider_metadata": {
                        "search_url": _research_url(request),
                        "work_request_id": request.request_id,
                    },
                    "generated_at": generated_at.isoformat(),
                    "reference_datetime": request.reference_datetime.isoformat(),
                }
            ],
            "warnings": warnings,
            "generated_at": generated_at.isoformat(),
            "reference_datetime": request.reference_datetime.isoformat(),
        }


def _evidence_payload(
    comparable: SoldComparableInput,
    request_id: str,
    generated_at: datetime,
) -> dict[str, Any]:
    matched_fields = IDENTITY_FIELDS if comparable.exact_match else ()
    mismatched_fields = () if comparable.exact_match else ("IDENTITY_REVIEW_REQUIRED",)
    confidence = "HIGH" if comparable.exact_match else "MEDIUM"
    status = "COMPLETED" if comparable.exact_match else "NEEDS_REVIEW"
    return {
        "evidence_id": f"evidence-{comparable.ebay_item_id}",
        "evidence_type": "SOLD_COMPARABLES",
        "source_name": "eBay Sold",
        "source_url": comparable.sold_item_url,
        "item_id": comparable.ebay_item_id,
        "observed_value": comparable.sold_price,
        "currency": comparable.currency,
        "observed_date": comparable.sold_date,
        "title": comparable.title,
        "exact_match": comparable.exact_match,
        "matched_fields": list(matched_fields),
        "mismatched_fields": list(mismatched_fields),
        "confidence": confidence,
        "status": status,
        "warnings": list(comparable.warnings),
        "raw_metadata": {
            "listing_type": comparable.listing_type,
            "best_offer_used": comparable.best_offer_used,
            "shipping_amount": comparable.shipping_amount,
            "work_request_result_id": request_id,
            "canonical_comparable": {
                "ebay_item_id": comparable.ebay_item_id,
                "sold_item_url": comparable.sold_item_url,
                "title": comparable.title,
                "sold_price": comparable.sold_price,
                "currency": comparable.currency,
                "sold_date": comparable.sold_date,
                "listing_type": comparable.listing_type,
                "best_offer_used": comparable.best_offer_used,
                "shipping_amount": comparable.shipping_amount,
                "exact_match": comparable.exact_match,
                "matched_fields": list(matched_fields),
                "mismatched_fields": list(mismatched_fields),
                "confidence": confidence,
                "warnings": list(comparable.warnings),
            },
        },
        "created_at": generated_at.isoformat(),
    }


def _result_confidence(comparables: tuple[SoldComparableInput, ...]) -> str:
    if not comparables:
        return "UNVERIFIED"
    if all(comparable.exact_match for comparable in comparables):
        return "HIGH"
    return "MEDIUM"


def _prompt_count(input_func) -> int:
    raw = input_func("How many verified comparables? ").strip()
    try:
        count = int(raw)
    except ValueError as exc:
        raise WorkContractError("Comparable count must be an integer.") from exc
    if count < 0:
        raise WorkContractError("Comparable count must be non-negative.")
    return count


def _prompt_comparable(input_func, index: int) -> SoldComparableInput:
    print(f"Comparable {index}")
    return SoldComparableInput(
        ebay_item_id=_prompt_required(input_func, "eBay Item ID: "),
        sold_item_url=_prompt_required(input_func, "Sold URL: "),
        title=_prompt_required(input_func, "Title: "),
        sold_price=_prompt_required(input_func, "Sold Price: "),
        currency=_prompt_required(input_func, "Currency: ").upper(),
        sold_date=_prompt_required(input_func, "Sold Date: "),
        listing_type=_prompt_required(input_func, "Listing Type: ").upper(),
        best_offer_used=_prompt_optional_bool(input_func, "Best Offer Used (Y/N/UNKNOWN): "),
        shipping_amount=_prompt_optional(input_func, "Shipping Amount (optional): "),
        exact_match=_prompt_bool(input_func, "Exact Match (Y/N): "),
        warnings=_prompt_warnings(input_func),
    )


def _prompt_required(input_func, label: str) -> str:
    value = input_func(label).strip()
    if not value:
        raise WorkContractError(f"{label.strip(': ')} is required.")
    return value


def _prompt_optional(input_func, label: str) -> str | None:
    value = input_func(label).strip()
    return value or None


def _prompt_bool(input_func, label: str) -> bool:
    value = input_func(label).strip().upper()
    if value in {"Y", "YES"}:
        return True
    if value in {"N", "NO"}:
        return False
    raise WorkContractError(f"{label.strip(': ')} must be Y or N.")


def _prompt_optional_bool(input_func, label: str) -> bool | None:
    value = input_func(label).strip().upper()
    if value in {"", "UNKNOWN"}:
        return None
    if value in {"Y", "YES"}:
        return True
    if value in {"N", "NO"}:
        return False
    raise WorkContractError(f"{label.strip(': ')} must be Y, N, or UNKNOWN.")


def _prompt_warnings(input_func) -> tuple[str, ...]:
    value = input_func("Warnings (optional): ").strip()
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _research_request(request: WorkRequest) -> dict[str, Any]:
    value = request.context.get("research_request")
    return dict(value) if isinstance(value, dict) else {}


def _research_url(request: WorkRequest) -> str:
    if request.source_urls:
        return request.source_urls[0]
    research_request = _research_request(request)
    return str(research_request.get("ebay_sold_search_url") or "")
