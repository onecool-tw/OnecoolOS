"""Executable Work bridge for manual research workflows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from onecool_os.research.workbench import ResearchRequestExporter
from onecool_os.research.workbench import ResearchResultImporter
from onecool_os.research.workbench import ResearchWorkbenchError
from onecool_os.research.workbench.models import ResearchWorkbenchImportResult
from onecool_os.work.enums import WorkPriority
from onecool_os.work.enums import WorkRequestType
from onecool_os.work.enums import WorkStatus
from onecool_os.work.models import WORK_CONTRACT_SCHEMA_VERSION
from onecool_os.work.models import WorkRequest
from onecool_os.work.models import WorkResponse
from onecool_os.work.validation import WorkContractError


@dataclass(frozen=True)
class WorkRequestExportResult:
    """Result of exporting one research item as a Work request."""

    request: WorkRequest
    output_path: str | None = None
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe data."""

        return {
            "request": self.request.to_dict(),
            "output_path": self.output_path,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class WorkResponseImportResult:
    """Result of importing a Work response through existing validators."""

    response: WorkResponse
    work_request_id: str
    evidence_batches: tuple[Any, ...]
    evidence: tuple[Any, ...]
    warnings: tuple[str, ...]

    @property
    def evidence_count(self) -> int:
        """Return the number of validated evidence records."""

        return len(self.evidence)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe result data."""

        return {
            "work_request_id": self.work_request_id,
            "response": self.response.to_dict(),
            "evidence_batch_count": len(self.evidence_batches),
            "evidence_count": self.evidence_count,
            "warnings": list(self.warnings),
        }


class ResearchWorkBridge:
    """Bridge one READY Research Queue item to and from Work Contract JSON."""

    def export_ready_research_request(
        self,
        runtime_session: Any,
        *,
        output_path: str | Path | None = None,
        asset_id: str | None = None,
        cert_number: str | None = None,
        reference_datetime: datetime | None = None,
        generated_at: datetime | None = None,
    ) -> WorkRequestExportResult:
        """Export one READY research item as a Work Request envelope."""

        reference = reference_datetime or getattr(runtime_session, "generated_at", None) or datetime.now(UTC)
        generated = generated_at or reference
        export = ResearchRequestExporter().export(
            runtime_session,
            limit=1,
            asset_id=asset_id,
            cert_number=cert_number,
            reference_datetime=reference,
            generated_at=generated,
        )
        if not export.requests:
            raise WorkContractError("No READY research queue item available for Work export.")

        research_request = export.requests[0]
        request = WorkRequest(
            schema_version=WORK_CONTRACT_SCHEMA_VERSION,
            request_id=f"work:{research_request.request_id}",
            request_type=WorkRequestType.COLLECTION_RESEARCH,
            asset_id=research_request.asset_id,
            reference_datetime=reference,
            priority=WorkPriority.HIGH,
            requested_action="Find verified eBay Sold evidence for this asset.",
            context={
                "work_contract": "Onecool Work Contract v1.0",
                "research_request": research_request.to_dict(),
                "provider_instruction": research_request.to_dict()["provider_instruction"],
                "expected_output": "Return outputs.orf_payload using Onecool Research Framework JSON.",
            },
            source_urls=(research_request.ebay_sold_search_url,),
            constraints={
                "manual_execution_required": True,
                "provider_calls_inside_onecool_os": False,
                "no_scraping_inside_onecool_os": True,
                "no_recommendations": True,
                "return_evidence_only": True,
                "do_not_calculate_fair_value": True,
                "do_not_create_valuation": True,
                "do_not_update_nav": True,
            },
        )

        written_path = None
        if output_path is not None:
            written_path = str(self.write_request(request, output_path))
        return WorkRequestExportResult(
            request=request,
            output_path=written_path,
            warnings=tuple(export.warnings),
        )

    def write_request(self, request: WorkRequest, output_path: str | Path) -> Path:
        """Write one Work Request envelope to disk."""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(request.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def import_response(
        self,
        input_path: str | Path,
        *,
        expected_request_id: str | None = None,
    ) -> WorkResponseImportResult:
        """Import a Work Response and validate its ORF evidence output."""

        path = Path(input_path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkContractError(f"Work response import failed: {exc}") from exc

        response = WorkResponse(**payload)
        self._validate_response(response, expected_request_id=expected_request_id)
        orf_payload = self._orf_payload(response)
        try:
            imported = ResearchResultImporter().import_payload(
                orf_payload,
                source_file=str(path),
            )
        except ResearchWorkbenchError as exc:
            raise WorkContractError(str(exc)) from exc

        return self._import_result(response, imported)

    def _validate_response(
        self,
        response: WorkResponse,
        *,
        expected_request_id: str | None = None,
    ) -> None:
        if response.schema_version != WORK_CONTRACT_SCHEMA_VERSION:
            raise WorkContractError(
                f"Unsupported Work Contract schema_version: {response.schema_version}"
            )
        if expected_request_id and response.request_id != expected_request_id:
            raise WorkContractError("Work response request_id does not match expected request_id.")
        if response.status != WorkStatus.COMPLETED:
            raise WorkContractError(f"Work response status is not COMPLETED: {response.status.value}")
        if response.errors:
            categories = ", ".join(error.category.value for error in response.errors)
            raise WorkContractError(f"Work response contains errors: {categories}")

    def _orf_payload(self, response: WorkResponse) -> dict[str, Any]:
        for key in ("orf_payload", "research_result", "research_payload"):
            payload = response.outputs.get(key)
            if isinstance(payload, dict):
                return payload
        raise WorkContractError("Work response outputs must include an ORF payload.")

    def _import_result(
        self,
        response: WorkResponse,
        imported: ResearchWorkbenchImportResult,
    ) -> WorkResponseImportResult:
        return WorkResponseImportResult(
            response=response,
            work_request_id=response.request_id,
            evidence_batches=tuple(imported.evidence_batches),
            evidence=tuple(imported.evidence),
            warnings=tuple(response.warnings) + tuple(imported.warnings),
        )
