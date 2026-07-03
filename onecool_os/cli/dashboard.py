"""Dashboard command-line handlers."""

from __future__ import annotations

import argparse
import json

from onecool_os.dashboard import DashboardBuilder


def add_dashboard_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register dashboard CLI commands."""

    parser = subparsers.add_parser(
        "dashboard",
        help="Dashboard display-only commands.",
    )
    dashboard_subparsers = parser.add_subparsers(
        dest="dashboard_command",
        required=True,
    )
    dashboard_subparsers.add_parser(
        "demo",
        help="Show dashboard demo view.",
    ).set_defaults(command_handler=handle_dashboard_command)


def handle_dashboard_command(args: argparse.Namespace) -> int:
    """Handle dashboard CLI commands."""

    if args.dashboard_command == "demo":
        view = DashboardBuilder.demo()
        print(json.dumps(view.to_dict(), indent=2))
        return 0
    raise ValueError(
        f"Unsupported dashboard command: {args.dashboard_command}"
    )
