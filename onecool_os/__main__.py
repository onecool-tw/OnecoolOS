"""Command-line interface for Onecool OS."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from onecool_os.core import AppConfig, CoreEngine
from onecool_os.core.config import ConfigLoader


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

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
