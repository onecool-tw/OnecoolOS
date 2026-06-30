"""Market command-line handlers."""

from __future__ import annotations

import argparse
import json

from onecool_os.core.config import ConfigLoader
from onecool_os.market.engine import create_market_engine


def add_market_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register Market CLI commands."""

    market_parser = subparsers.add_parser(
        "market",
        help="Manage Market Engine.",
    )
    market_parser.set_defaults(command_handler=handle_market_command)
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


def handle_market_command(args: argparse.Namespace) -> int:
    """Handle Market CLI commands."""

    loaded_config = ConfigLoader.from_environment().load()
    market_engine = create_market_engine(loaded_config.config)
    if args.market_command == "status":
        print(json.dumps(market_engine.status().to_dict(), indent=2))
        market_engine.shutdown()
        return 0
    if args.market_command == "fetch":
        provider_id = args.provider or loaded_config.config.market.default_provider
        payload = market_engine.fetch(provider_id, args.symbol)
        print(json.dumps(payload, indent=2))
        market_engine.shutdown()
        return 0
    if args.market_command == "validate":
        provider_id = args.provider or loaded_config.config.market.default_provider
        payload = market_engine.validate_fetch(provider_id, args.symbol)
        print(json.dumps(payload, indent=2))
        market_engine.shutdown()
        return 0

    raise ValueError(f"Unsupported market command: {args.market_command}")
