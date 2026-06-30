"""Command-line interface for Onecool OS."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from onecool_os.assets.cash.loader import (
    CashLoader,
    CashLoaderError,
    cash_import_to_dict,
)
from onecool_os.assets.funds.loader import (
    FundLoader,
    FundLoaderError,
    fund_import_to_dict,
)
from onecool_os.assets.real_estate.loader import (
    RealEstateLoader,
    RealEstateLoaderError,
    real_estate_import_to_dict,
)
from onecool_os.assets.sports_cards.loader import (
    CardLoader,
    CardLoaderError,
    card_import_to_dict,
)
from onecool_os.core import AppConfig, CoreEngine
from onecool_os.core.config import ConfigLoader
from onecool_os.core.logging import LoggingSystem, initialize_logging
from onecool_os.core.scheduler import create_scheduler
from onecool_os.market.engine import create_market_engine
from onecool_os.portfolio.engine import (
    create_portfolio_demo,
    create_portfolio_engine,
)
from onecool_os.portfolio.loader import (
    PortfolioLoader,
    PortfolioLoaderError,
    portfolio_to_import_summary,
)


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
    subparsers.add_parser("logs", help="Show logging status.")
    cash_parser = subparsers.add_parser(
        "cash",
        help="Manage Cash / FX asset module.",
    )
    cash_subparsers = cash_parser.add_subparsers(
        dest="cash_command",
        required=True,
    )
    cash_subparsers.add_parser(
        "demo",
        help="Show sample cash balances from JSON.",
    )
    cards_parser = subparsers.add_parser(
        "cards",
        help="Manage Sports Cards asset module.",
    )
    cards_subparsers = cards_parser.add_subparsers(
        dest="cards_command",
        required=True,
    )
    cards_subparsers.add_parser(
        "demo",
        help="Show sample sports cards from JSON.",
    )
    real_estate_parser = subparsers.add_parser(
        "real-estate",
        help="Manage Real Estate asset module.",
    )
    real_estate_subparsers = real_estate_parser.add_subparsers(
        dest="real_estate_command",
        required=True,
    )
    real_estate_subparsers.add_parser(
        "demo",
        help="Show sample real estate from JSON.",
    )
    funds_parser = subparsers.add_parser(
        "funds",
        help="Manage Funds asset module.",
    )
    funds_subparsers = funds_parser.add_subparsers(
        dest="funds_command",
        required=True,
    )
    funds_import_parser = funds_subparsers.add_parser(
        "import",
        help="Load sample funds from JSON.",
    )
    funds_import_parser.add_argument("json_path")
    scheduler_parser = subparsers.add_parser(
        "scheduler",
        help="Manage scheduler jobs.",
    )
    scheduler_subparsers = scheduler_parser.add_subparsers(
        dest="scheduler_command",
        required=True,
    )
    scheduler_subparsers.add_parser("list", help="List scheduler jobs.")
    scheduler_run_parser = scheduler_subparsers.add_parser(
        "run",
        help="Run a scheduler job manually.",
    )
    scheduler_run_parser.add_argument("job_id")
    market_parser = subparsers.add_parser(
        "market",
        help="Manage Market Engine.",
    )
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
    portfolio_parser = subparsers.add_parser(
        "portfolio",
        help="Manage Portfolio Engine.",
    )
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

    if args.command == "logs":
        loaded_config = ConfigLoader.from_environment().load()
        logging_system = initialize_logging(loaded_config.config)
        print(json.dumps(asdict(logging_system.status()), indent=2))
        return 0

    if args.command == "cash":
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

    if args.command == "cards":
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

    if args.command == "real-estate":
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

    if args.command == "funds":
        loaded_config = ConfigLoader.from_environment().load()
        logging_system = LoggingSystem(loaded_config.config)
        logger = logging_system.get_logger("funds")
        if args.funds_command == "import":
            try:
                result = FundLoader(logger=logger).load(args.json_path)
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

    if args.command == "scheduler":
        loaded_config = ConfigLoader.from_environment().load()
        scheduler = create_scheduler(loaded_config.config)
        if args.scheduler_command == "list":
            jobs = [job.to_dict() for job in scheduler.list_jobs()]
            print(json.dumps(jobs, indent=2))
            return 0
        if args.scheduler_command == "run":
            job = scheduler.run_job(args.job_id)
            print(json.dumps(job.to_dict(), indent=2))
            return 0

    if args.command == "market":
        loaded_config = ConfigLoader.from_environment().load()
        market_engine = create_market_engine(loaded_config.config)
        if args.market_command == "status":
            print(json.dumps(market_engine.status().to_dict(), indent=2))
            market_engine.shutdown()
            return 0
        if args.market_command == "fetch":
            provider_id = (
                args.provider or loaded_config.config.market.default_provider
            )
            payload = market_engine.fetch(provider_id, args.symbol)
            print(json.dumps(payload, indent=2))
            market_engine.shutdown()
            return 0
        if args.market_command == "validate":
            provider_id = (
                args.provider or loaded_config.config.market.default_provider
            )
            payload = market_engine.validate_fetch(provider_id, args.symbol)
            print(json.dumps(payload, indent=2))
            market_engine.shutdown()
            return 0

    if args.command == "portfolio":
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

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
