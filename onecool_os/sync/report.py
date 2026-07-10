"""Presentation helpers for collection sync reports."""

from __future__ import annotations

from onecool_os.sync.models import SyncReport


def sync_report_lines(report: SyncReport) -> tuple[str, ...]:
    """Return deterministic human-readable sync report lines."""

    lines = [
        "Collection Sync Report",
        "----------------------",
        f"Imported Records: {report.imported_records}",
        f"Asset Master Records: {report.asset_master_records}",
        f"Matched Records: {report.matched_records}",
        f"Collection Health: {report.collection_health}",
        f"Generated At: {report.generated_at.isoformat()}",
        "",
        "Differences",
        "-----------",
    ]
    if not report.differences:
        lines.append("None")
    else:
        lines.extend(
            (
                f"{difference.severity} {difference.difference_type} "
                f"{difference.cert_number or difference.asset_id}: "
                f"{difference.description}"
            )
            for difference in report.differences
        )
    lines.extend(("", "Warnings", "--------"))
    if not report.warnings:
        lines.append("None")
    else:
        lines.extend(report.warnings)
    return tuple(lines)
