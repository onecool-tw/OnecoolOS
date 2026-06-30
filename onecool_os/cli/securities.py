"""Securities command-line handlers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from onecool_os.assets.securities.creator import SecurityCreator
from onecool_os.assets.securities.loader import (
    SecurityLoader,
    SecurityLoaderError,
    security_import_to_dict,
)
from onecool_os.core.config import ConfigLoader
from onecool_os.core.logging import LoggingSystem


def add_securities_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register Securities CLI commands."""

    securities_parser = subparsers.add_parser(
        "securities",
        help="Manage Securities asset module.",
    )
    securities_parser.set_defaults(command_handler=handle_securities_command)
    securities_subparsers = securities_parser.add_subparsers(
        dest="securities_command",
        required=True,
    )
    import_parser = securities_subparsers.add_parser(
        "import",
        help="Load local securities from JSON.",
    )
    import_parser.add_argument("json_path")
    securities_subparsers.add_parser(
        "create",
        help="Create or update a local real securities portfolio file.",
    )


def handle_securities_command(args: argparse.Namespace) -> int:
    """Handle Securities CLI commands."""

    loaded_config = ConfigLoader.from_environment().load()
    logging_system = LoggingSystem(loaded_config.config)
    logger = logging_system.get_logger("securities")
    if args.securities_command == "import":
        json_path = Path(args.json_path)
        if not json_path.exists():
            logger.error("Securities import file does not exist: %s", json_path)
            print(json.dumps(
                {
                    "status": "failure",
                    "error_message": (
                        "Securities portfolio file not found. Copy "
                        "data/portfolio/securities.example.json to "
                        "data/portfolio/securities.json and update it with "
                        "your local securities data."
                    ),
                },
                indent=2,
            ))
            return 1
        try:
            result = SecurityLoader(logger=logger).load(json_path)
        except SecurityLoaderError as exc:
            logger.error("Securities import failed: %s", exc)
            print(json.dumps(
                {
                    "status": "failure",
                    "error_message": str(exc),
                },
                indent=2,
            ))
            return 1
        print(json.dumps(security_import_to_dict(result), indent=2))
        return 0
    if args.securities_command == "create":
        try:
            result = SecurityCreator(logger=logger).create()
        except SecurityLoaderError as exc:
            logger.error("Securities portfolio create failed: %s", exc)
            print(json.dumps(
                {
                    "status": "failure",
                    "error_message": str(exc),
                },
                indent=2,
            ))
            return 1
        print(json.dumps(result.to_dict(), indent=2))
        return 0

    raise ValueError(
        f"Unsupported securities command: {args.securities_command}"
    )
