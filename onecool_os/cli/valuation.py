"""Valuation command-line handlers."""

from __future__ import annotations

import argparse
import json
from typing import Any

from onecool_os.assets.base import BaseAsset
from onecool_os.intelligence.valuation.engine import ValuationEngine
from onecool_os.intelligence.valuation.models import ValuationResult


def add_valuation_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register Valuation Engine CLI commands."""

    valuation_parser = subparsers.add_parser(
        "valuation",
        help="Manage Valuation Engine.",
    )
    valuation_parser.set_defaults(command_handler=handle_valuation_command)
    valuation_subparsers = valuation_parser.add_subparsers(
        dest="valuation_command",
        required=True,
    )
    valuation_subparsers.add_parser(
        "demo",
        help="Show mocked valuation results.",
    )


def handle_valuation_command(args: argparse.Namespace) -> int:
    """Handle Valuation Engine CLI commands."""

    if args.valuation_command == "demo":
        engine = ValuationEngine().initialize()
        assets = _demo_assets()
        results = engine.valuate_many(assets)
        print(json.dumps(_valuation_demo_to_dict(assets, results), indent=2))
        return 0

    raise ValueError(f"Unsupported valuation command: {args.valuation_command}")


def _demo_assets() -> list[BaseAsset]:
    return [
        BaseAsset("VALUATION-FUND-DEMO", "MUTUAL_FUND", "Demo Fund", "USD"),
        BaseAsset("VALUATION-CARD-DEMO", "SPORTS_CARD", "Demo Card", "USD"),
        BaseAsset(
            "VALUATION-REAL-ESTATE-DEMO",
            "REAL_ESTATE",
            "Demo Property",
            "TWD",
        ),
        BaseAsset("VALUATION-CASH-DEMO", "CASH", "Demo Cash", "TWD"),
    ]


def _valuation_demo_to_dict(
    assets: list[BaseAsset],
    results: tuple[ValuationResult, ...],
) -> dict[str, Any]:
    asset_names = {asset.asset_id: asset.name for asset in assets}
    return {
        "valuations": [
            {
                "asset": asset_names[result.asset_id],
                "provider": result.provider,
                "estimated_value": result.to_dict()["estimated_value"],
                "confidence": result.confidence,
            }
            for result in results
        ]
    }
