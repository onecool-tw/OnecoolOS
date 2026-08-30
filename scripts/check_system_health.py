#!/usr/bin/env python3
"""Evaluate scheduled cache health and expose GitHub Actions outputs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from onecool_os.health import build_health_report, write_health_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="data/market/system_health/system_health_latest.json")
    parser.add_argument("--scope", choices=("all", "morning", "asia", "weekly"), default="all")
    args = parser.parse_args()

    report = build_health_report(args.root)
    write_health_report(report, Path(args.root) / args.output)
    scope_status = report["status"] if args.scope == "all" else report["scope_status"][args.scope]
    scoped_issues = [item for item in report["issues"] if args.scope == "all" or item["scope"] == args.scope]
    recoveries = sorted({item["recovery_workflow"] for item in scoped_issues if item["status"] == "BLOCKED" and item["retryable"] and item["recovery_workflow"]})

    outputs = {
        "status": report["status"],
        "scope_status": scope_status,
        "blocked_count": sum(item["status"] == "BLOCKED" for item in scoped_issues),
        "recovery_workflows": json.dumps(recoveries),
        "issue_fingerprint": report["issue_fingerprint"],
    }
    if output_path := os.environ.get("GITHUB_OUTPUT"):
        with open(output_path, "a", encoding="utf-8") as handle:
            for key, value in outputs.items():
                handle.write(f"{key}={value}\n")

    lines = [
        "## Onecool unified schedule health",
        "",
        f"- Full status: `{report['status']}`",
        f"- Checked scope: `{args.scope}` → `{scope_status}`",
        f"- READY / PARTIAL / BLOCKED: `{report['counts']['ready']} / {report['counts']['partial']} / {report['counts']['blocked']}`",
        f"- Recovery workflows: `{', '.join(recoveries) or 'NONE'}`",
        "",
    ]
    if scoped_issues:
        lines.extend(["| Module | Status | Reason |", "|---|---|---|"])
        lines.extend(f"| {item['label']} | {item['status']} | {item['reason']} |" for item in scoped_issues)
    else:
        lines.append("All checked modules are ready.")
    text = "\n".join(lines) + "\n"
    print(text)
    if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
