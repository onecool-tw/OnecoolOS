"""Single-asset collectible research pipeline."""

from __future__ import annotations

from collections import Counter
from datetime import UTC
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from onecool_os.assets.master import AssetMasterLoader
from onecool_os.connectors.collectibles import PSACollectionImporter
from onecool_os.research.enums import ResearchType
from onecool_os.research.pipeline.models import PipelineStatus
from onecool_os.research.pipeline.models import SingleAssetPipelineOutcome
from onecool_os.research.pipeline.models import SingleAssetPipelineRequest
from onecool_os.research.pipeline.models import SingleAssetPipelineResult
from onecool_os.research.pipeline.validation import SingleAssetPipelineError
from onecool_os.research.queue import ResearchQueueEngine
from onecool_os.research.queue import ResearchQueueStatus
from onecool_os.research.workbench import ResearchRequestExporter
from onecool_os.research.workbench import ResearchResultImporter
from onecool_os.research.workbench import ResearchWorkbenchError
from onecool_os.runtime import RuntimeSession
from onecool_os.valuation.evidence import EvidenceStatus

DEFAULT_CERT_NUMBER = "111003720"
DEFAULT_REQUEST_OUTPUT = Path("imports/research/kobe_111003720_request.json")
DEFAULT_RESULT_INPUT = Path("imports/research/kobe_111003720_result.json")
DEFAULT_REPORT_OUTPUT = Path("outputs/research/kobe_111003720_pipeline_report.json")
DEFAULT_EXPECTED_IDENTITY = {
    "year": "2008",
    "set": "TOPPS",
    "card_number": "24",
    "subject": "KOBE BRYANT",
    "grade_issuer": "PSA",
    "grade": "9",
}


class SingleAssetResearchPipeline:
    """Run one collectible asset through research request and evidence import."""

    def run(
        self,
        *,
        cert_number: str = DEFAULT_CERT_NUMBER,
        request_output: str | Path = DEFAULT_REQUEST_OUTPUT,
        result_input: str | Path = DEFAULT_RESULT_INPUT,
        report_output: str | Path | None = None,
        reference_datetime: datetime | None = None,
        runtime_session: RuntimeSession | None = None,
        expected_identity: dict[str, str] | None = None,
    ) -> SingleAssetPipelineOutcome:
        """Run the two-stage single-asset pipeline."""

        reference = reference_datetime or datetime.now(UTC)
        session = runtime_session or load_local_runtime_session(reference)
        pipeline_id = f"single-asset-research:{cert_number}:{reference.isoformat()}"
        try:
            asset = locate_asset_by_cert(session, cert_number)
            validate_target_identity(asset, expected_identity or DEFAULT_EXPECTED_IDENTITY)
            snapshot = ResearchQueueEngine().build(
                session,
                reference_datetime=reference,
                generated_at=reference,
            )
            queue_item = _ready_sold_comparable_item(snapshot, asset)
            export = ResearchRequestExporter().export(
                session,
                queue_snapshot=SimpleNamespace(items=(queue_item,)),
                limit=1,
                cert_number=cert_number,
                reference_datetime=reference,
                generated_at=reference,
            )
            if len(export.requests) != 1:
                raise SingleAssetPipelineError("Exactly one research request must be exported.")
            request_path = ResearchRequestExporter().write_json(export, request_output)
            request = SingleAssetPipelineRequest(
                pipeline_id=pipeline_id,
                asset_id=asset["asset_id"],
                cert_number=cert_number,
                asset_name=queue_item.asset_name,
                ebay_sold_search_url=queue_item.source_url or "",
                research_request_id=export.requests[0].request_id,
                reference_datetime=reference,
                created_at=reference,
                metadata={"queue_item_id": queue_item.queue_item_id},
            )
            result_path = Path(result_input)
            if not result_path.exists():
                result = _pipeline_result(
                    pipeline_id,
                    asset,
                    queue_item.asset_name,
                    request_exported=True,
                    provider_result_loaded=False,
                    orf_validation_passed=False,
                    status=PipelineStatus.PARTIAL,
                    warnings=("Research request exported. Provider result is not available yet.",),
                    reference_datetime=reference,
                )
                _write_report_if_requested(result, report_output)
                return SingleAssetPipelineOutcome(
                    request=request,
                    result=result,
                    runtime_session=session,
                    request_output_path=str(request_path),
                    provider_result_path=str(result_path),
                )

            try:
                import_result = ResearchResultImporter().import_json(result_path)
            except ResearchWorkbenchError as exc:
                result = _pipeline_result(
                    pipeline_id,
                    asset,
                    queue_item.asset_name,
                    request_exported=True,
                    provider_result_loaded=True,
                    orf_validation_passed=False,
                    status=PipelineStatus.FAILED,
                    warnings=(str(exc),),
                    reference_datetime=reference,
                )
                _write_report_if_requested(result, report_output)
                return SingleAssetPipelineOutcome(
                    request=request,
                    result=result,
                    runtime_session=session,
                    request_output_path=str(request_path),
                    provider_result_path=str(result_path),
                )
            matching_batches = tuple(
                batch
                for batch in import_result.evidence_batches
                if batch.cert_number == cert_number and batch.asset_id == asset["asset_id"]
            )
            if not matching_batches:
                raise SingleAssetPipelineError("Provider result contains no matching evidence batch.")
            updated_session = session
            for batch in matching_batches:
                updated_session = updated_session.attach_ebay_evidence_batch(batch)
            evidence = tuple(item for batch in matching_batches for item in batch.evidence)
            counts = Counter(item.status for item in evidence)
            result = _pipeline_result(
                pipeline_id,
                asset,
                queue_item.asset_name,
                request_exported=True,
                provider_result_loaded=True,
                orf_validation_passed=True,
                evidence_records_created=len(evidence),
                verified_evidence_count=counts[EvidenceStatus.VERIFIED],
                review_required_count=counts[EvidenceStatus.NEEDS_REVIEW],
                rejected_count=counts[EvidenceStatus.REJECTED],
                no_match_count=counts[EvidenceStatus.NO_MATCH],
                runtime_attachment_completed=True,
                status=PipelineStatus.COMPLETED,
                warnings=tuple(import_result.warnings),
                reference_datetime=reference,
            )
            _write_report_if_requested(result, report_output)
            return SingleAssetPipelineOutcome(
                request=request,
                result=result,
                runtime_session=updated_session,
                request_output_path=str(request_path),
                provider_result_path=str(result_path),
            )
        except SingleAssetPipelineError as exc:
            result = SingleAssetPipelineResult(
                pipeline_id=pipeline_id,
                asset_id="UNKNOWN",
                cert_number=cert_number,
                asset_name="Unknown Asset",
                request_exported=False,
                provider_result_loaded=Path(result_input).exists(),
                orf_validation_passed=False,
                evidence_records_created=0,
                verified_evidence_count=0,
                review_required_count=0,
                rejected_count=0,
                no_match_count=0,
                runtime_attachment_completed=False,
                warnings=(str(exc),),
                status=PipelineStatus.BLOCKED,
                generated_at=reference,
                reference_datetime=reference,
            )
            _write_report_if_requested(result, report_output)
            return SingleAssetPipelineOutcome(
                request=None,
                result=result,
                runtime_session=session,
                request_output_path=str(request_output),
                provider_result_path=str(result_input),
            )


def load_local_runtime_session(reference_datetime: datetime) -> RuntimeSession:
    """Load local PSA/BGS collection and Asset Master without mutating files."""

    psa_result = PSACollectionImporter().import_csv(
        Path("imports/psa/collection.csv"),
        reference_datetime=reference_datetime,
    )
    asset_master_path = _select_asset_master_path()
    asset_master_records = ()
    if asset_master_path is not None:
        asset_master_records = AssetMasterLoader().load(
            asset_master_path,
            reference_datetime=reference_datetime,
        ).records
    return RuntimeSession(
        imported_records=psa_result.records,
        asset_master_records=asset_master_records,
        generated_at=reference_datetime,
    )


def locate_asset_by_cert(runtime_session: RuntimeSession, cert_number: str) -> dict[str, Any]:
    """Locate exactly one runtime asset by cert number."""

    matches = tuple(
        dict(asset)
        for asset in runtime_session.enriched_runtime_assets
        if str(asset.get("cert_number") or asset.get("serial_number") or "").strip() == cert_number
    )
    if not matches:
        raise SingleAssetPipelineError(f"Asset not found for cert number: {cert_number}")
    if len(matches) > 1:
        raise SingleAssetPipelineError(f"Duplicate cert number in runtime session: {cert_number}")
    return matches[0]


def validate_target_identity(asset: dict[str, Any], expected: dict[str, str]) -> None:
    """Validate target identity before exporting research work."""

    actual = {
        "year": _norm(asset.get("year")),
        "set": _norm(asset.get("set") or asset.get("brand")),
        "card_number": _norm(asset.get("card_number")),
        "subject": _norm(asset.get("subject") or asset.get("player")),
        "grade_issuer": _norm(asset.get("grade_issuer") or asset.get("grade_company")),
        "grade": _norm(asset.get("grade")),
    }
    expected_normalized = {key: _norm(value) for key, value in expected.items()}
    if actual != expected_normalized:
        raise SingleAssetPipelineError("Target asset identity is ambiguous.")


def _ready_sold_comparable_item(snapshot: Any, asset: dict[str, Any]) -> Any:
    cert_number = str(asset.get("cert_number") or asset.get("serial_number") or "").strip()
    candidates = tuple(
        item
        for item in snapshot.items
        if item.cert_number == cert_number and item.research_type == ResearchType.SOLD_COMPARABLES
    )
    if len(candidates) != 1:
        raise SingleAssetPipelineError("Expected exactly one SOLD_COMPARABLES Research Queue item.")
    item = candidates[0]
    if item.status == ResearchQueueStatus.BLOCKED:
        raise SingleAssetPipelineError("Research Queue item is BLOCKED.")
    if item.status != ResearchQueueStatus.READY:
        raise SingleAssetPipelineError("Research Queue item must be READY.")
    if not item.source_url:
        raise SingleAssetPipelineError("eBay Sold Search URL is missing.")
    return item


def _pipeline_result(
    pipeline_id: str,
    asset: dict[str, Any],
    asset_name: str,
    *,
    request_exported: bool,
    provider_result_loaded: bool,
    orf_validation_passed: bool,
    status: PipelineStatus,
    warnings: tuple[str, ...],
    reference_datetime: datetime,
    evidence_records_created: int = 0,
    verified_evidence_count: int = 0,
    review_required_count: int = 0,
    rejected_count: int = 0,
    no_match_count: int = 0,
    runtime_attachment_completed: bool = False,
) -> SingleAssetPipelineResult:
    return SingleAssetPipelineResult(
        pipeline_id=pipeline_id,
        asset_id=str(asset.get("asset_id") or ""),
        cert_number=str(asset.get("cert_number") or asset.get("serial_number") or ""),
        asset_name=asset_name,
        request_exported=request_exported,
        provider_result_loaded=provider_result_loaded,
        orf_validation_passed=orf_validation_passed,
        evidence_records_created=evidence_records_created,
        verified_evidence_count=verified_evidence_count,
        review_required_count=review_required_count,
        rejected_count=rejected_count,
        no_match_count=no_match_count,
        runtime_attachment_completed=runtime_attachment_completed,
        warnings=warnings,
        status=status,
        generated_at=reference_datetime,
        reference_datetime=reference_datetime,
    )


def _write_report_if_requested(result: SingleAssetPipelineResult, report_output: str | Path | None) -> None:
    if report_output is None:
        return
    from onecool_os.research.pipeline.report import write_pipeline_report

    write_pipeline_report(result, report_output)


def _select_asset_master_path() -> Path | None:
    xlsx = Path("imports/asset_master/asset_master.xlsx")
    csv = Path("imports/asset_master/asset_master.csv")
    if xlsx.exists():
        return xlsx
    if csv.exists():
        return csv
    return None


def _norm(value: Any) -> str:
    return str(value or "").strip().upper()
