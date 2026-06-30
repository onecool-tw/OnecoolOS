"""Allocation command-line handlers."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from onecool_os.intelligence.allocation.engine import AllocationEngine
from onecool_os.intelligence.allocation.models import AllocationResult
from onecool_os.intelligence.valuation.models import ValuationResult


def add_allocation_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register Allocation Engine CLI commands."""

    allocation_parser = subparsers.add_parser(
        "allocation",
        help="Manage Allocation Engine.",
    )
    allocation_parser.set_defaults(command_handler=handle_allocation_command)
    allocation_subparsers = allocation_parser.add_subparsers(
        dest="allocation_command",
        required=True,
    )
    allocation_subparsers.add_parser(
        "demo",
        help="Show mocked allocation results.",
    )


def handle_allocation_command(args: argparse.Namespace) -> int:
    """Handle Allocation Engine CLI commands."""

    if args.allocation_command == "demo":
        valuations = _demo_valuation_results()
        engine = AllocationEngine()
        allocations = engine.calculate(valuations)
        portfolio_total = engine.portfolio_total(valuations)
        print(
            json.dumps(
                _allocation_demo_to_dict(allocations, portfolio_total),
                indent=2,
            )
        )
        return 0

    raise ValueError(
        f"Unsupported allocation command: {args.allocation_command}"
    )


def _demo_valuation_results() -> list[ValuationResult]:
    valuation_time = datetime(2026, 6, 30, tzinfo=UTC)
    return [
        ValuationResult(
            asset_id="Demo Fund",
            asset_type="MUTUAL_FUND",
            provider="demo",
            estimated_value=Decimal("10000"),
            currency="USD",
            valuation_time=valuation_time,
            confidence=0.5,
            notes="Mock allocation demo value.",
        ),
        ValuationResult(
            asset_id="Demo Card",
            asset_type="SPORTS_CARD",
            provider="demo",
            estimated_value=Decimal("5000"),
            currency="USD",
            valuation_time=valuation_time,
            confidence=0.5,
            notes="Mock allocation demo value.",
        ),
        ValuationResult(
            asset_id="Demo Property",
            asset_type="REAL_ESTATE",
            provider="demo",
            estimated_value=Decimal("30000000"),
            currency="TWD",
            valuation_time=valuation_time,
            confidence=0.5,
            notes="Mock allocation demo value.",
        ),
        ValuationResult(
            asset_id="Demo Cash",
            asset_type="CASH",
            provider="demo",
            estimated_value=Decimal("100000"),
            currency="TWD",
            valuation_time=valuation_time,
            confidence=0.5,
            notes="Mock allocation demo value.",
        ),
    ]


def _allocation_demo_to_dict(
    allocations: tuple[AllocationResult, ...],
    portfolio_total: Decimal,
) -> dict[str, Any]:
    return {
        "allocations": [
            {
                "asset": result.asset_name,
                "asset_type": result.asset_type,
                "market_value": result.to_dict()["market_value"],
                "allocation_percent": result.to_dict()[
                    "allocation_percent"
                ],
            }
            for result in allocations
        ],
        "portfolio_total": f"{portfolio_total.quantize(Decimal('0.01'))}",
    }
