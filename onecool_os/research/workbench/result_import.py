"""Import ORF-compatible research JSON into eBay Sold evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from onecool_os.research import ResearchJsonLoader
from onecool_os.research import ResearchJsonLoadResult
from onecool_os.research import research_evidence_to_ebay_sold_evidence
from onecool_os.research.validation import ResearchError
from onecool_os.research.workbench.models import ResearchWorkbenchImportResult
from onecool_os.research.workbench.validation import ResearchWorkbenchError
from onecool_os.valuation.evidence import EbaySoldEvidence
from onecool_os.valuation.evidence import EbaySoldEvidenceBatch


class ResearchResultImporter:
    """Load provider-returned ORF JSON and bridge it to eBay evidence."""

    def import_json(self, input_path: str | Path) -> ResearchWorkbenchImportResult:
        """Import a local JSON result without mutating source data."""

        source_path = Path(input_path)
        try:
            loaded = ResearchJsonLoader().load(source_path)
        except ResearchError as exc:
            raise ResearchWorkbenchError(f"Research result import failed: {exc}") from exc
        return self.import_loaded(loaded)

    def import_payload(
        self,
        payload: dict[str, Any],
        *,
        source_file: str = "<work-response>",
    ) -> ResearchWorkbenchImportResult:
        """Import an in-memory ORF payload without mutating source data."""

        try:
            loaded = ResearchJsonLoader().load_payload(
                payload,
                source_file=source_file,
            )
        except ResearchError as exc:
            raise ResearchWorkbenchError(f"Research result import failed: {exc}") from exc
        return self.import_loaded(loaded)

    def import_loaded(
        self,
        loaded: ResearchJsonLoadResult,
    ) -> ResearchWorkbenchImportResult:
        """Bridge loaded ORF results to eBay Sold evidence."""

        evidence_batches: list[EbaySoldEvidenceBatch] = []
        evidence_records: list[EbaySoldEvidence] = []
        warnings: list[str] = list(loaded.warnings)

        for batch in loaded.batches:
            for result in batch.results:
                bridged: list[EbaySoldEvidence] = []
                for evidence in result.evidence:
                    try:
                        bridged.append(research_evidence_to_ebay_sold_evidence(result, evidence))
                    except ResearchError as exc:
                        raise ResearchWorkbenchError(f"Evidence bridge failed: {exc}") from exc
                if not bridged:
                    continue
                evidence_batch = EbaySoldEvidenceBatch(
                    asset_id=result.asset_id or "",
                    cert_number=result.cert_number or "",
                    provider_name=result.provider_name,
                    search_url=(
                        result.provider_metadata.get("search_url")
                        or bridged[0].search_url
                    ),
                    search_queries=tuple(result.provider_metadata.get("search_queries", ())),
                    evidence=tuple(bridged),
                    warnings=tuple(result.warnings),
                    generated_at=result.generated_at,
                )
                evidence_batches.append(evidence_batch)
                evidence_records.extend(evidence_batch.evidence)

        return ResearchWorkbenchImportResult(
            source_file=loaded.source_file,
            batches=loaded.batches,
            evidence_batches=tuple(evidence_batches),
            evidence=tuple(evidence_records),
            warnings=tuple(warnings),
        )
