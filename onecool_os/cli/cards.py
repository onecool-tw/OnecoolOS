"""Sports Cards command-line handlers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from onecool_os.assets.sports_cards.loader import (
    CardLoader,
    CardLoaderError,
    card_import_to_dict,
)
from onecool_os.core.config import ConfigLoader
from onecool_os.core.logging import LoggingSystem


def add_cards_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register Sports Cards CLI commands."""

    cards_parser = subparsers.add_parser(
        "cards",
        help="Manage Sports Cards asset module.",
    )
    cards_parser.set_defaults(command_handler=handle_cards_command)
    cards_subparsers = cards_parser.add_subparsers(
        dest="cards_command",
        required=True,
    )
    cards_subparsers.add_parser(
        "demo",
        help="Show sample sports cards from JSON.",
    )
    cards_import_parser = cards_subparsers.add_parser(
        "import",
        help="Load local sports cards from JSON.",
    )
    cards_import_parser.add_argument("json_path")


def handle_cards_command(args: argparse.Namespace) -> int:
    """Handle Sports Cards CLI commands."""

    loaded_config = ConfigLoader.from_environment().load()
    logging_system = LoggingSystem(loaded_config.config)
    logger = logging_system.get_logger("cards")
    if args.cards_command == "demo":
        try:
            result = CardLoader(logger=logger).load(
                Path("examples/cards_demo.json")
            )
        except CardLoaderError as exc:
            logger.error("Cards demo failed: %s", exc)
            print(json.dumps(
                {
                    "status": "failure",
                    "error_message": str(exc),
                },
                indent=2,
            ))
            return 1
        print(json.dumps(card_import_to_dict(result), indent=2))
        return 0
    if args.cards_command == "import":
        try:
            result = CardLoader(logger=logger).load(Path(args.json_path))
        except CardLoaderError as exc:
            logger.error("Cards import failed: %s", exc)
            print(json.dumps(
                {
                    "status": "failure",
                    "error_message": str(exc),
                },
                indent=2,
            ))
            return 1
        print(json.dumps(card_import_to_dict(result), indent=2))
        return 0

    raise ValueError(f"Unsupported cards command: {args.cards_command}")
