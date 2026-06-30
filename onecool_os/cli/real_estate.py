"""Real Estate command-line handlers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from onecool_os.assets.real_estate.loader import (
    RealEstateLoader,
    RealEstateLoaderError,
    real_estate_import_to_dict,
)
from onecool_os.core.config import ConfigLoader
from onecool_os.core.logging import LoggingSystem


def add_real_estate_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register Real Estate CLI commands."""

    real_estate_parser = subparsers.add_parser(
        "real-estate",
        help="Manage Real Estate asset module.",
    )
    real_estate_parser.set_defaults(command_handler=handle_real_estate_command)
    real_estate_subparsers = real_estate_parser.add_subparsers(
        dest="real_estate_command",
        required=True,
    )
    real_estate_subparsers.add_parser(
        "demo",
        help="Show sample real estate from JSON.",
    )


def handle_real_estate_command(args: argparse.Namespace) -> int:
    """Handle Real Estate CLI commands."""

    loaded_config = ConfigLoader.from_environment().load()
    logging_system = LoggingSystem(loaded_config.config)
    logger = logging_system.get_logger("real_estate")
    if args.real_estate_command == "demo":
        try:
            result = RealEstateLoader(logger=logger).load(
                Path("examples/real_estate_demo.json")
            )
        except RealEstateLoaderError as exc:
            logger.error("Real estate demo failed: %s", exc)
            print(json.dumps(
                {
                    "status": "failure",
                    "error_message": str(exc),
                },
                indent=2,
            ))
            return 1
        print(json.dumps(real_estate_import_to_dict(result), indent=2))
        return 0

    raise ValueError(
        f"Unsupported real estate command: {args.real_estate_command}"
    )
