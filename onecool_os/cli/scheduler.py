"""Scheduler command-line handlers."""

from __future__ import annotations

import argparse
import json

from onecool_os.core.config import ConfigLoader
from onecool_os.core.scheduler import create_scheduler


def add_scheduler_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register scheduler CLI commands."""

    scheduler_parser = subparsers.add_parser(
        "scheduler",
        help="Manage scheduler jobs.",
    )
    scheduler_parser.set_defaults(command_handler=handle_scheduler_command)
    scheduler_subparsers = scheduler_parser.add_subparsers(
        dest="scheduler_command",
        required=True,
    )
    scheduler_subparsers.add_parser("list", help="List scheduler jobs.")
    scheduler_run_parser = scheduler_subparsers.add_parser(
        "run",
        help="Run a scheduler job manually.",
    )
    scheduler_run_parser.add_argument("job_id")


def handle_scheduler_command(args: argparse.Namespace) -> int:
    """Handle scheduler CLI commands."""

    loaded_config = ConfigLoader.from_environment().load()
    scheduler = create_scheduler(loaded_config.config)
    if args.scheduler_command == "list":
        jobs = [job.to_dict() for job in scheduler.list_jobs()]
        print(json.dumps(jobs, indent=2))
        return 0
    if args.scheduler_command == "run":
        job = scheduler.run_job(args.job_id)
        print(json.dumps(job.to_dict(), indent=2))
        return 0

    raise ValueError(f"Unsupported scheduler command: {args.scheduler_command}")
