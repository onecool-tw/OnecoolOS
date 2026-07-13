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
        f"Health State: {report.health_state}",
        f"Health Explanation: {report.health_explanation}",
        f"Generated At: {report.generated_at.isoformat()}",
        "",
        "Health Report",
        "-------------",
    ]
    groups = report.issue_groups or {}
    if not groups:
        lines.append("None")
    for group_name in ("IDENTITY", "NORMALIZATION", "METADATA", "DECISION", "EVIDENCE"):
        group = groups.get(group_name, {})
        lines.extend(
            (
                group_name.title(),
                f"  Issue Count: {group.get('issue_count', 0)}",
                f"  Severity: {group.get('severity', 'INFO')}",
                f"  Recommended Action: {group.get('recommended_action', 'None')}",
            )
        )
    lines.extend(("", "Warnings", "--------"))
    if not report.warnings:
        lines.append("None")
    else:
        lines.extend(report.warnings)
    return tuple(lines)
