"""Portfolio command-line handlers."""

from __future__ import annotations

import argparse
import json

from onecool_os.core.config import ConfigLoader
from onecool_os.portfolio.engine import (
    create_portfolio_demo,
    create_portfolio_engine,
)
from onecool_os.portfolio.loader import (
    PortfolioLoader,
    PortfolioLoaderError,
    portfolio_to_import_summary,
)


def add_portfolio_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register Portfolio CLI commands."""

    portfolio_parser = subparsers.add_parser(
        "portfolio",
        help="Manage Portfolio Engine.",
    )
    portfolio_parser.set_defaults(command_handler=handle_portfolio_command)
    portfolio_subparsers = portfolio_parser.add_subparsers(
        dest="portfolio_command",
        required=True,
    )
    portfolio_subparsers.add_parser(
        "status",
        help="Show Portfolio Engine status.",
    )
    portfolio_subparsers.add_parser(
        "demo",
        help="Show an in-memory demo portfolio.",
    )
    portfolio_import_parser = portfolio_subparsers.add_parser(
        "import",
        help="Load a demo portfolio from JSON.",
    )
    portfolio_import_parser.add_argument("json_path")


def handle_portfolio_command(args: argparse.Namespace) -> int:
    """Handle Portfolio CLI commands."""

    loaded_config = ConfigLoader.from_environment().load()
    if args.portfolio_command == "demo":
        print(json.dumps(create_portfolio_demo(loaded_config.config), indent=2))
        return 0
    if args.portfolio_command == "import":
        try:
            portfolio = PortfolioLoader().load(args.json_path)
        except PortfolioLoaderError as exc:
            print(json.dumps(
                {
                    "portfolio_summary": "Portfolio Summary",
                    "status": "failure",
                    "error_message": str(exc),
                },
                indent=2,
            ))
            return 1
        print(json.dumps(portfolio_to_import_summary(portfolio), indent=2))
        return 0

    portfolio_engine = create_portfolio_engine(loaded_config.config)
    if args.portfolio_command == "status":
        print(json.dumps(portfolio_engine.status().to_dict(), indent=2))
        return 0

    raise ValueError(f"Unsupported portfolio command: {args.portfolio_command}")
