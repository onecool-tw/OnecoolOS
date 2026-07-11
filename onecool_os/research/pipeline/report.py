"""Concise reporting for single-asset research pipeline runs."""

from __future__ import annotations

import json
from pathlib import Path

from onecool_os.research.pipeline.models import SingleAssetPipelineResult


def pipeline_report_lines(result: SingleAssetPipelineResult, *, queue_status: str = "READY") -> tuple[str, ...]:
    """Return safe CLI report lines."""

    return (
        "Onecool Single Asset Research Pipeline",
        "",
        "Asset:",
        result.asset_name,
        "",
        "Cert Number:",
        result.cert_number,
        "",
        "Research Queue:",
        queue_status,
        "",
        "Research Request:",
        "Exported" if result.request_exported else "Not Exported",
        "",
        "Provider Result:",
        "Loaded" if result.provider_result_loaded else "Not Available",
        "",
        "ORF Validation:",
        "Passed" if result.orf_validation_passed else "Not Passed",
        "",
        "Evidence:",
        f"Verified: {result.verified_evidence_count}",
        f"Needs Review: {result.review_required_count}",
        f"Rejected: {result.rejected_count}",
        f"No Match: {result.no_match_count}",
        "",
        "Runtime Attachment:",
        "Completed" if result.runtime_attachment_completed else "Not Completed",
        "",
        "Pipeline Status:",
        result.status.value,
    )


def write_pipeline_report(result: SingleAssetPipelineResult, output_path: str | Path) -> Path:
    """Write a concise JSON report without raw provider metadata."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path
