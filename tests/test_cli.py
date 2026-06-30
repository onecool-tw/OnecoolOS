from onecool_os.__main__ import build_parser
from onecool_os.cli.cards import handle_cards_command
from onecool_os.cli.cash import handle_cash_command
from onecool_os.cli.core import handle_core_command
from onecool_os.cli.funds import handle_funds_command
from onecool_os.cli.market import handle_market_command
from onecool_os.cli.portfolio import handle_portfolio_command
from onecool_os.cli.real_estate import handle_real_estate_command
from onecool_os.cli.scheduler import handle_scheduler_command


def test_cli_parser_delegates_to_core_handler() -> None:
    args = build_parser().parse_args(["status"])

    assert args.command_handler is handle_core_command


def test_cli_parser_delegates_to_module_handlers() -> None:
    parser = build_parser()

    cases = (
        (["cash", "demo"], handle_cash_command),
        (["cards", "demo"], handle_cards_command),
        (["funds", "import", "examples/funds_demo.json"], handle_funds_command),
        (["market", "status"], handle_market_command),
        (["portfolio", "status"], handle_portfolio_command),
        (["real-estate", "demo"], handle_real_estate_command),
        (["scheduler", "list"], handle_scheduler_command),
    )

    for argv, handler in cases:
        args = parser.parse_args(argv)
        assert args.command_handler is handler
