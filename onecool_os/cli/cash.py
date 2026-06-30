"""Cash / FX command-line handlers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from onecool_os.assets.cash.loader import (
    CashLoader,
    CashLoaderError,
    cash_import_to_dict,
)
from onecool_os.core.config import ConfigLoader
from onecool_os.core.logging import LoggingSystem


def add_cash_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register Cash / FX CLI commands."""

    cash_parser = subparsers.add_parser(
        "cash",
        help="Manage Cash / FX asset module.",
    )
    cash_parser.set_defaults(command_handler=handle_cash_command)
    cash_subparsers = cash_parser.add_subparsers(
        dest="cash_command",
        required=True,
    )
    cash_subparsers.add_parser(
        "demo",
        help="Show sample cash balances from JSON.",
    )


def handle_cash_command(args: argparse.Namespace) -> int:
    """Handle Cash / FX CLI commands."""

    loaded_config = ConfigLoader.from_environment().load()
    logging_system = LoggingSystem(loaded_config.config)
    logger = logging_system.get_logger("cash")
    if args.cash_command == "demo":
        try:
            result = CashLoader(logger=logger).load(
                Path("examples/cash_demo.json")
            )
        except CashLoaderError as exc:
            logger.error("Cash demo failed: %s", exc)
            print(json.dumps(
                {
                    "status": "failure",
                    "error_message": str(exc),
                },
                indent=2,
            ))
            return 1
        print(json.dumps(cash_import_to_dict(result), indent=2))
        return 0

    raise ValueError(f"Unsupported cash command: {args.cash_command}")
