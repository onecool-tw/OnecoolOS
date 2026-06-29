"""Command-line interface for Onecool OS."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from onecool_os.core import AppConfig, CoreEngine
from onecool_os.core.config import ConfigLoader
from onecool_os.core.logging import initialize_logging
from onecool_os.core.scheduler import create_scheduler
from onecool_os.market.engine import create_market_engine


def build_parser() -> argparse.ArgumentParser:
    """Build the command parser."""

    parser = argparse.ArgumentParser(prog="onecool-os")
    parser.add_argument(
        "--database",
        help="SQLite database path. Defaults to ONECOOL_OS_DB_PATH or data.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init", help="Initialize the database.")
    subparsers.add_parser("status", help="Show Core Engine status.")
    subparsers.add_parser("plugins", help="List loaded plugins.")
    subparsers.add_parser("config", help="Show sanitized configuration.")
    subparsers.add_parser("logs", help="Show logging status.")
    scheduler_parser = subparsers.add_parser(
        "scheduler",
        help="Manage scheduler jobs.",
    )
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
    market_parser = subparsers.add_parser(
        "market",
        help="Manage Market Engine.",
    )
    market_subparsers = market_parser.add_subparsers(
        dest="market_command",
        required=True,
    )
    market_subparsers.add_parser("status", help="Show Market Engine status.")
    market_fetch_parser = market_subparsers.add_parser(
        "fetch",
        help="Fetch normalized market data.",
    )
    market_fetch_parser.add_argument("symbol")
    market_fetch_parser.add_argument("--provider")
    market_validate_parser = market_subparsers.add_parser(
        "validate",
        help="Validate a market data fetch.",
    )
    market_validate_parser.add_argument("symbol")
    market_validate_parser.add_argument("--provider")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""

    parser = build_parser()
    args = parser.parse_args(argv)
    config = AppConfig.from_environment()
    if args.database:
        config = AppConfig(
            database_path=Path(args.database),
            plugin_paths=config.plugin_paths,
            load_builtin_plugins=config.load_builtin_plugins,
        )

    if args.command == "init":
        with CoreEngine(config) as engine:
            print(json.dumps(asdict(engine.status()), indent=2))
        return 0

    if args.command == "status":
        with CoreEngine(config) as engine:
            print(json.dumps(asdict(engine.status()), indent=2))
        return 0

    if args.command == "plugins":
        with CoreEngine(config) as engine:
            plugins = [
                {
                    "name": plugin.manifest.name,
                    "version": plugin.manifest.version,
                    "description": plugin.manifest.description,
                }
                for plugin in engine.plugins.plugins
            ]
            print(json.dumps(plugins, indent=2))
        return 0

    if args.command == "config":
        loaded_config = ConfigLoader.from_environment().load()
        print(json.dumps(loaded_config.to_sanitized_dict(), indent=2))
        return 0

    if args.command == "logs":
        loaded_config = ConfigLoader.from_environment().load()
        logging_system = initialize_logging(loaded_config.config)
        print(json.dumps(asdict(logging_system.status()), indent=2))
        return 0

    if args.command == "scheduler":
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

    if args.command == "market":
        loaded_config = ConfigLoader.from_environment().load()
        market_engine = create_market_engine(loaded_config.config)
        if args.market_command == "status":
            print(json.dumps(market_engine.status().to_dict(), indent=2))
            market_engine.shutdown()
            return 0
        if args.market_command == "fetch":
            provider_id = (
                args.provider or loaded_config.config.market.default_provider
            )
            payload = market_engine.fetch(provider_id, args.symbol)
            print(json.dumps(payload, indent=2))
            market_engine.shutdown()
            return 0
        if args.market_command == "validate":
            provider_id = (
                args.provider or loaded_config.config.market.default_provider
            )
            payload = market_engine.validate_fetch(provider_id, args.symbol)
            print(json.dumps(payload, indent=2))
            market_engine.shutdown()
            return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
