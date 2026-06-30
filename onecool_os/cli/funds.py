"""Funds command-line handlers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from onecool_os.assets.funds.loader import (
    FundLoader,
    FundLoaderError,
    fund_import_to_dict,
)
from onecool_os.core.config import ConfigLoader
from onecool_os.core.logging import LoggingSystem


def add_funds_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register Funds CLI commands."""

    funds_parser = subparsers.add_parser(
        "funds",
        help="Manage Funds asset module.",
    )
    funds_parser.set_defaults(command_handler=handle_funds_command)
    funds_subparsers = funds_parser.add_subparsers(
        dest="funds_command",
        required=True,
    )
    funds_import_parser = funds_subparsers.add_parser(
        "import",
        help="Load sample funds from JSON.",
    )
    funds_import_parser.add_argument("json_path")


def handle_funds_command(args: argparse.Namespace) -> int:
    """Handle Funds CLI commands."""

    loaded_config = ConfigLoader.from_environment().load()
    logging_system = LoggingSystem(loaded_config.config)
    logger = logging_system.get_logger("funds")
    if args.funds_command == "import":
        json_path = Path(args.json_path)
        if not json_path.exists():
            logger.error("Funds import file does not exist: %s", json_path)
            print(json.dumps(
                {
                    "status": "failure",
                    "error_message": (
                        "Funds portfolio file not found. Copy "
                        "data/portfolio/funds.example.json to "
                        "data/portfolio/funds.json and update it with your "
                        "local fund data."
                    ),
                },
                indent=2,
            ))
            return 1
        try:
            result = FundLoader(logger=logger).load(json_path)
        except FundLoaderError as exc:
            logger.error("Funds import failed: %s", exc)
            print(json.dumps(
                {
                    "status": "failure",
                    "error_message": str(exc),
                },
                indent=2,
            ))
            return 1
        print(json.dumps(fund_import_to_dict(result), indent=2))
        return 0

    raise ValueError(f"Unsupported funds command: {args.funds_command}")
