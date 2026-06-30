"""Core command-line handlers."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from onecool_os.core import AppConfig, CoreEngine
from onecool_os.core.config import ConfigLoader
from onecool_os.core.logging import initialize_logging


def add_core_parsers(subparsers: argparse._SubParsersAction) -> None:
    """Register core CLI commands."""

    subparsers.add_parser(
        "init",
        help="Initialize the database.",
    ).set_defaults(command_handler=handle_core_command)
    subparsers.add_parser(
        "status",
        help="Show Core Engine status.",
    ).set_defaults(command_handler=handle_core_command)
    subparsers.add_parser(
        "plugins",
        help="List loaded plugins.",
    ).set_defaults(command_handler=handle_core_command)
    subparsers.add_parser(
        "config",
        help="Show sanitized configuration.",
    ).set_defaults(command_handler=handle_core_command)
    subparsers.add_parser(
        "logs",
        help="Show logging status.",
    ).set_defaults(command_handler=handle_core_command)


def handle_core_command(args: argparse.Namespace) -> int:
    """Handle core CLI commands."""

    if args.command == "init":
        with CoreEngine(_runtime_config(args)) as engine:
            print(json.dumps(asdict(engine.status()), indent=2))
        return 0

    if args.command == "status":
        with CoreEngine(_runtime_config(args)) as engine:
            print(json.dumps(asdict(engine.status()), indent=2))
        return 0

    if args.command == "plugins":
        with CoreEngine(_runtime_config(args)) as engine:
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

    raise ValueError(f"Unsupported core command: {args.command}")


def _runtime_config(args: argparse.Namespace) -> AppConfig:
    config = AppConfig.from_environment()
    database = getattr(args, "database", None)
    if not database:
        return config
    return AppConfig(
        database_path=Path(database),
        plugin_paths=config.plugin_paths,
        load_builtin_plugins=config.load_builtin_plugins,
    )
