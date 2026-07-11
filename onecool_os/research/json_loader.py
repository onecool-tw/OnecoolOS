"""Local JSON loader for Onecool Research Framework results."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from onecool_os.research.models import ResearchBatch
from onecool_os.research.models import ResearchResult
from onecool_os.research.validation import ResearchError
from onecool_os.research.validation import ensure_valid_research_result


@dataclass(frozen=True)
class ResearchJsonLoadResult:
    """Result returned by the local JSON loader."""

    batches: tuple[ResearchBatch, ...]
    warnings: tuple[str, ...]
    source_file: str

    @property
    def results(self) -> tuple[ResearchResult, ...]:
        """Return all loaded results in deterministic batch order."""

        return tuple(result for batch in self.batches for result in batch.results)


class ResearchJsonLoader:
    """Load provider-generated local JSON without mutating source files."""

    def load(self, path: str | Path) -> ResearchJsonLoadResult:
        """Load a ResearchBatch or ResearchResult JSON document."""

        source_path = Path(path)
        try:
            payload = json.loads(source_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ResearchError(f"Invalid research JSON: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise ResearchError("Research JSON root must be an object.")

        batches = _coerce_payload(payload)
        warnings = tuple(
            warning
            for batch in batches
            for warning in batch.warnings
        )
        for result in tuple(result for batch in batches for result in batch.results):
            ensure_valid_research_result(result)
        return ResearchJsonLoadResult(
            batches=batches,
            warnings=warnings,
            source_file=str(source_path),
        )


def _coerce_payload(payload: dict) -> tuple[ResearchBatch, ...]:
    if "batches" in payload:
        batches = payload["batches"]
        if not isinstance(batches, list):
            raise ResearchError("batches must be a list.")
        return tuple(ResearchBatch(**batch) for batch in batches)
    if "batch_id" in payload:
        return (ResearchBatch(**payload),)
    if "results" in payload:
        return (
            ResearchBatch(
                batch_id=payload.get("batch_id", "research-batch"),
                provider_name=payload.get("provider_name", "unknown"),
                results=payload["results"],
                warnings=payload.get("warnings", ()),
                generated_at=payload.get("generated_at"),
                reference_datetime=payload.get("reference_datetime"),
            ),
        )
    if "result_id" in payload:
        result = ResearchResult(**payload)
        return (
            ResearchBatch(
                batch_id=f"batch-{result.result_id}",
                provider_name=result.provider_name,
                results=(result,),
                reference_datetime=result.reference_datetime,
                generated_at=result.generated_at,
            ),
        )
    raise ResearchError("Research JSON must contain batches, a batch, or a result.")
