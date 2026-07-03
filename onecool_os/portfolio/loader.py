"""JSON portfolio loader for demo imports."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from onecool_os.portfolio.engine import portfolio_to_demo_dict
from onecool_os.portfolio.models import Asset
from onecool_os.portfolio.models import Holding
from onecool_os.portfolio.models import Portfolio
from onecool_os.portfolio.models import PortfolioError
from onecool_os.portfolio.models import Position


class PortfolioLoaderError(PortfolioError):
    """Raised when a portfolio JSON file cannot be loaded."""


class PortfolioLoader:
    """Load an in-memory portfolio from a JSON file."""

    required_root_fields = frozenset({"portfolio_name"})
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
    required_holding_fields = frozenset(
        {
            "asset_id",
            "asset_type",
            "quantity",
        }
    )

    def load(self, json_path: str | Path) -> Portfolio:
        """Load and validate a portfolio JSON file."""

        payload = self._read_payload(json_path)
        if "portfolios" in payload:
            portfolios = self.load_all(json_path)
            if len(portfolios) != 1:
                raise PortfolioLoaderError(
                    "Portfolio JSON must contain exactly one portfolio."
                )
            return portfolios[0]
        return self._load_portfolio(
            payload,
            default_portfolio_id="json-import",
        )

    def load_all(self, json_path: str | Path) -> tuple[Portfolio, ...]:
        """Load one or more aggregation portfolios from JSON."""

        payload = self._read_payload(json_path)
        if "portfolios" not in payload:
            return (self._load_portfolio(payload, "json-import"),)
        portfolios_payload = payload["portfolios"]
        if not isinstance(portfolios_payload, list):
            raise PortfolioLoaderError("portfolios must be a list.")
        portfolios = tuple(
            self._load_portfolio(portfolio_payload, f"portfolio-{index + 1}")
            for index, portfolio_payload in enumerate(portfolios_payload)
        )
        self._validate_duplicate_portfolio_ids(portfolios)
        return portfolios

    def _read_payload(self, json_path: str | Path) -> dict[str, Any]:
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
            raise PortfolioLoaderError(
                "Portfolio JSON root must be an object."
            )
        return payload

    def _load_portfolio(
        self,
        payload: Any,
        default_portfolio_id: str,
    ) -> Portfolio:
        if not isinstance(payload, dict):
            raise PortfolioLoaderError("portfolio must be an object.")
        self._validate_required_fields(
            payload,
            self.required_root_fields,
            "root",
        )
        portfolio_name = self._require_text(payload["portfolio_name"], "root")
        portfolio = Portfolio(
            portfolio_id=self._optional_text(
                payload.get("portfolio_id"),
            ) or default_portfolio_id,
            portfolio_name=portfolio_name,
            base_currency=payload.get("base_currency", "TWD"),
            total_assets=payload.get("total_assets"),
            total_market_value=payload.get("total_market_value"),
            total_cost=payload.get("total_cost"),
            cash_balance=payload.get("cash_balance"),
            note=payload.get("note"),
            tags=payload.get("tags"),
        )
        if "holdings" in payload:
            holdings_payload = payload["holdings"]
            if not isinstance(holdings_payload, list):
                raise PortfolioLoaderError("holdings must be a list.")
            for index, holding_payload in enumerate(holdings_payload):
                portfolio.add_holding(
                    self._load_holding(holding_payload, index)
                )
        elif "positions" in payload:
            positions_payload = payload["positions"]
            if not isinstance(positions_payload, list):
                raise PortfolioLoaderError("positions must be a list.")
            for index, position_payload in enumerate(positions_payload):
                position = self._load_position(position_payload, index)
                portfolio.add_position(position)
        else:
            raise PortfolioLoaderError(
                "holdings or positions must be provided."
            )
        return portfolio

    def _load_holding(self, payload: Any, index: int) -> Holding:
        if not isinstance(payload, dict):
            raise PortfolioLoaderError(
                f"holdings[{index}] must be an object."
            )
        self._validate_required_fields(
            payload,
            self.required_holding_fields,
            f"holdings[{index}]",
        )
        try:
            return Holding(
                asset_id=payload["asset_id"],
                asset_type=payload["asset_type"],
                quantity=payload["quantity"],
                average_cost=payload.get("average_cost"),
                market_value=payload.get("market_value"),
            )
        except PortfolioError as exc:
            raise PortfolioLoaderError(str(exc)) from exc

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
            raise PortfolioLoaderError(
                f"{field_name} must be a non-empty string."
            )
        return value.strip()

    def _optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise PortfolioLoaderError("value must be a string.")
        value = value.strip()
        return value or None

    def _parse_decimal(
        self,
        value: Any,
        field_name: str,
        require_positive: bool = False,
    ) -> Decimal:
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise PortfolioLoaderError(
                f"Invalid {field_name}: {value}"
            ) from exc

        if not decimal_value.is_finite():
            raise PortfolioLoaderError(f"Invalid {field_name}: {value}")
        if require_positive and decimal_value <= Decimal("0"):
            raise PortfolioLoaderError(f"Invalid {field_name}: {value}")
        return decimal_value

    def _validate_duplicate_portfolio_ids(
        self,
        portfolios: tuple[Portfolio, ...],
    ) -> None:
        seen: set[str] = set()
        for portfolio in portfolios:
            if portfolio.portfolio_id in seen:
                raise PortfolioLoaderError(
                    f"Duplicate portfolio_id: {portfolio.portfolio_id}"
                )
            seen.add(portfolio.portfolio_id)


def portfolio_to_import_summary(portfolio: Portfolio) -> dict[str, Any]:
    """Return a JSON-safe import summary payload."""

    payload = portfolio_to_demo_dict(portfolio)
    return {
        "portfolio_summary": "Portfolio Summary",
        **payload,
    }
