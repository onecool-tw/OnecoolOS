"""JSON portfolio loader for demo imports."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from onecool_os.portfolio.engine import portfolio_to_demo_dict
from onecool_os.portfolio.models import Asset, Portfolio, PortfolioError, Position


class PortfolioLoaderError(PortfolioError):
    """Raised when a portfolio JSON file cannot be loaded."""


class PortfolioLoader:
    """Load an in-memory portfolio from a JSON file."""

    required_root_fields = frozenset({"portfolio_name", "positions"})
    required_position_fields = frozenset(
        {
            "asset_id",
            "symbol",
            "asset_type",
            "name",
            "currency",
            "quantity",
            "average_cost",
            "current_price",
        }
    )

    def load(self, json_path: str | Path) -> Portfolio:
        """Load and validate a portfolio JSON file."""

        path = Path(json_path)
        try:
            raw_payload = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise PortfolioLoaderError(
                f"Portfolio JSON file cannot be read: {path}"
            ) from exc

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise PortfolioLoaderError(
                f"Invalid portfolio JSON: {exc.msg}"
            ) from exc

        if not isinstance(payload, dict):
            raise PortfolioLoaderError("Portfolio JSON root must be an object.")

        self._validate_required_fields(payload, self.required_root_fields, "root")
        portfolio_name = self._require_text(payload["portfolio_name"], "root")
        positions_payload = payload["positions"]
        if not isinstance(positions_payload, list):
            raise PortfolioLoaderError("positions must be a list.")

        portfolio = Portfolio(portfolio_id="json-import", name=portfolio_name)
        for index, position_payload in enumerate(positions_payload):
            position = self._load_position(position_payload, index)
            portfolio.add_position(position)
        return portfolio

    def _load_position(self, payload: Any, index: int) -> Position:
        if not isinstance(payload, dict):
            raise PortfolioLoaderError(
                f"positions[{index}] must be an object."
            )
        self._validate_required_fields(
            payload,
            self.required_position_fields,
            f"positions[{index}]",
        )

        try:
            asset = Asset(
                asset_id=self._require_text(payload["asset_id"], "asset_id"),
                symbol=self._require_text(payload["symbol"], "symbol"),
                asset_type=self._require_text(
                    payload["asset_type"],
                    "asset_type",
                ),
                name=self._require_text(payload["name"], "name"),
                currency=self._require_text(payload["currency"], "currency"),
            )
        except PortfolioError as exc:
            raise PortfolioLoaderError(str(exc)) from exc

        return Position(
            asset=asset,
            quantity=self._parse_decimal(
                payload["quantity"],
                "quantity",
                require_positive=True,
            ),
            average_cost=self._parse_decimal(
                payload["average_cost"],
                "average_cost",
            ),
            current_price=self._parse_decimal(
                payload["current_price"],
                "current_price",
            ),
        )

    def _validate_required_fields(
        self,
        payload: dict[str, Any],
        required_fields: frozenset[str],
        location: str,
    ) -> None:
        missing_fields = sorted(required_fields - payload.keys())
        if missing_fields:
            fields = ", ".join(missing_fields)
            raise PortfolioLoaderError(
                f"Missing required field in {location}: {fields}"
            )

    def _require_text(self, value: Any, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise PortfolioLoaderError(f"{field_name} must be a non-empty string.")
        return value.strip()

    def _parse_decimal(
        self,
        value: Any,
        field_name: str,
        require_positive: bool = False,
    ) -> Decimal:
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise PortfolioLoaderError(f"Invalid {field_name}: {value}") from exc

        if not decimal_value.is_finite():
            raise PortfolioLoaderError(f"Invalid {field_name}: {value}")
        if require_positive and decimal_value <= Decimal("0"):
            raise PortfolioLoaderError(f"Invalid {field_name}: {value}")
        return decimal_value


def portfolio_to_import_summary(portfolio: Portfolio) -> dict[str, Any]:
    """Return a JSON-safe import summary payload."""

    payload = portfolio_to_demo_dict(portfolio)
    return {
        "portfolio_summary": "Portfolio Summary",
        **payload,
    }
