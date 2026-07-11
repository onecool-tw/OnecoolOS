"""Load local provider-generated eBay Sold evidence JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from onecool_os.valuation.evidence.models import EbaySoldEvidenceBatch
from onecool_os.valuation.evidence.validation import EvidenceError


@dataclass(frozen=True)
class EbaySoldEvidenceLoadResult:
    """Result of loading one local eBay Sold evidence JSON file."""

    batches: tuple[EbaySoldEvidenceBatch, ...]
    warnings: tuple[str, ...]
    source_file: str


class EbaySoldEvidenceJsonLoader:
    """Load local eBay Sold evidence JSON without mutating source files."""

    def load(self, path: str | Path) -> EbaySoldEvidenceLoadResult:
        """Load one JSON file."""

        source_path = Path(path)
        try:
            content = source_path.read_text(encoding="utf-8")
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise EvidenceError(f"Invalid eBay Sold evidence JSON: {exc}") from exc
        except OSError as exc:
            raise EvidenceError(f"Cannot read eBay Sold evidence JSON: {source_path}") from exc

        batches_payload = payload.get("batches") if isinstance(payload, dict) else None
        if batches_payload is None and isinstance(payload, dict):
            batches_payload = [payload]
        if not isinstance(batches_payload, list):
            raise EvidenceError("eBay Sold evidence JSON must contain batches list.")

        batches = []
        warnings = []
        for index, item in enumerate(batches_payload, start=1):
            if not isinstance(item, dict):
                raise EvidenceError(f"Evidence batch {index} must be an object.")
            batch = EbaySoldEvidenceBatch(**item)
            batches.append(batch)
            warnings.extend(batch.warnings)
        return EbaySoldEvidenceLoadResult(
            batches=tuple(batches),
            warnings=tuple(warnings),
            source_file=str(source_path),
        )
