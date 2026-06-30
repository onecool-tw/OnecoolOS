"""Command-line entry point for Onecool OS."""

from __future__ import annotations

import argparse

from onecool_os.cli.cards import add_cards_parser
from onecool_os.cli.cash import add_cash_parser
from onecool_os.cli.core import add_core_parsers
from onecool_os.cli.funds import add_funds_parser
from onecool_os.cli.market import add_market_parser
from onecool_os.cli.portfolio import add_portfolio_parser
from onecool_os.cli.real_estate import add_real_estate_parser
from onecool_os.cli.scheduler import add_scheduler_parser


def build_parser() -> argparse.ArgumentParser:
    """Build the command parser."""

    parser = argparse.ArgumentParser(prog="onecool-os")
    parser.add_argument(
        "--database",
        help="SQLite database path. Defaults to ONECOOL_OS_DB_PATH or data.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_core_parsers(subparsers)
    add_cash_parser(subparsers)
    add_cards_parser(subparsers)
    add_real_estate_parser(subparsers)
    add_funds_parser(subparsers)
    add_scheduler_parser(subparsers)
    add_market_parser(subparsers)
    add_portfolio_parser(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""

    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "command_handler", None)
    if handler is None:
        parser.error(f"Unsupported command: {args.command}")
        return 2
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
