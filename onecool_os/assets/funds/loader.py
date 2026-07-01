"""JSON loader for the Funds asset module."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from onecool_os.assets.funds.models import FundAsset, FundPosition
from onecool_os.portfolio.models import Portfolio, PortfolioError


class FundLoaderError(PortfolioError):
    """Raised when a funds JSON file cannot be loaded."""


@dataclass(frozen=True)
class FundImportResult:
    """Loaded funds and shared portfolio projection."""

    portfolio: Portfolio
    positions: tuple[FundPosition, ...]


class FundLoader:
    """Load sample fund holdings into an in-memory portfolio."""

    legacy_root_key = "funds"
    portfolio_root_key = "positions"
    required_position_fields = frozenset(
        {
            "asset_id",
            "symbol",
            "name",
            "currency",
            "quantity",
            "average_cost",
        }
    )

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("onecool_os.funds")

    def load(self, json_path: str | Path) -> FundImportResult:
        """Load and validate a funds JSON file."""

        path = Path(json_path)
        self.logger.info("Starting funds import from %s", path)
        payload = self._read_payload(path)
        portfolio_name = self._portfolio_name(payload)
        funds_payload = self._positions_payload(payload)
        if not isinstance(funds_payload, list):
            raise FundLoaderError("positions must be a list.")

        portfolio = Portfolio(portfolio_id="funds-import", name=portfolio_name)
        positions = []
        asset_ids = set()
        for index, fund_payload in enumerate(funds_payload):
            position = self._load_position(fund_payload, index)
            if position.asset.asset_id in asset_ids:
                raise FundLoaderError(
                    f"Duplicate asset_id: {position.asset.asset_id}"
                )
            asset_ids.add(position.asset.asset_id)
            positions.append(position)
            portfolio.add_position(position.to_position())

        self.logger.info("Funds import completed with %s funds.", len(positions))
        return FundImportResult(
            portfolio=portfolio,
            positions=tuple(positions),
        )

    def _read_payload(self, path: Path) -> dict[str, Any]:
        try:
            raw_payload = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.logger.error("Funds JSON file cannot be read: %s", path)
            raise FundLoaderError(
                f"Funds JSON file cannot be read: {path}"
            ) from exc

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            self.logger.error("Invalid funds JSON: %s", exc.msg)
            raise FundLoaderError(f"Invalid funds JSON: {exc.msg}") from exc

        if not isinstance(payload, dict):
            raise FundLoaderError("Funds JSON root must be an object.")
        return payload

    def _portfolio_name(self, payload: dict[str, Any]) -> str:
        if self.portfolio_root_key not in payload:
            return "Funds Import"
        if "portfolio_name" not in payload:
            raise FundLoaderError("Missing required field in root: portfolio_name")
        return self._require_text(payload["portfolio_name"], "portfolio_name")

    def _positions_payload(self, payload: dict[str, Any]) -> Any:
        if self.portfolio_root_key in payload:
            return payload[self.portfolio_root_key]
        if self.legacy_root_key in payload:
            return payload[self.legacy_root_key]
        raise FundLoaderError("Missing required field in root: positions")

    def _load_position(self, payload: Any, index: int) -> FundPosition:
        if not isinstance(payload, dict):
            raise FundLoaderError(f"positions[{index}] must be an object.")
        self._validate_required_fields(
            payload,
            self.required_position_fields,
            f"positions[{index}]",
        )
        asset_type = self._optional_text(payload.get("asset_type"))
        current_price = payload.get("current_price")
        cost = payload.get("cost")

        try:
            asset = FundAsset(
                asset_id=self._require_text(payload["asset_id"], "asset_id"),
                symbol=self._require_text(payload["symbol"], "symbol"),
                asset_type=asset_type or "MUTUAL_FUND",
                name=self._require_text(payload["name"], "name"),
                currency=self._require_text(payload["currency"], "currency"),
                fund_house=self._optional_text(payload.get("fund_house")),
                region=self._optional_text(payload.get("region")),
                theme=self._optional_text(payload.get("theme")),
            )
        except PortfolioError as exc:
            raise FundLoaderError(str(exc)) from exc
        return FundPosition(
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
            current_price=(
                self._parse_decimal(current_price, "current_price")
                if current_price is not None
                else None
            ),
            account=self._optional_text(payload.get("account")),
            asset_class=self._optional_text(payload.get("asset_class")),
            status=self._optional_text(payload.get("status")),
            base_currency=self._optional_text(payload.get("base_currency")),
            cost=(
                self._parse_decimal(cost, "cost")
                if cost is not None
                else None
            ),
            notes=self._optional_text(payload.get("notes")) or "",
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
            raise FundLoaderError(
                f"Missing required field in {location}: {fields}"
            )

    def _require_text(self, value: Any, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise FundLoaderError(f"{field_name} must be a non-empty string.")
        return value.strip()

    def _optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            return None
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
            raise FundLoaderError(f"Invalid {field_name}: {value}") from exc

        if not decimal_value.is_finite():
            raise FundLoaderError(f"Invalid {field_name}: {value}")
        if require_positive and decimal_value <= Decimal("0"):
            raise FundLoaderError(f"Invalid {field_name}: {value}")
        return decimal_value


def fund_import_to_dict(result: FundImportResult) -> dict[str, Any]:
    """Return JSON-safe funds import output."""

    total_cost = result.portfolio.total_cost()
    total_market_value = result.portfolio.total_market_value()
    return {
        "funds": [
            _fund_position_to_dict(position)
            for position in result.positions
        ],
        "total_cost": _format_decimal(total_cost),
        "total_market_value": _format_decimal(total_market_value),
        "total_unrealized_pnl": _format_decimal(
            total_market_value - total_cost
        ),
    }


def _fund_position_to_dict(position: FundPosition) -> dict[str, str | None]:
    return {
        "asset_id": position.asset.asset_id,
        "symbol": position.asset.symbol,
        "asset_type": position.asset.asset_type,
        "name": position.asset.name,
        "currency": position.asset.currency,
        "account": position.account,
        "asset_class": position.asset_class,
        "status": position.status,
        "base_currency": position.base_currency,
        "cost": _format_decimal(position.cost),
        "fund_house": position.asset.fund_house,
        "region": position.asset.region,
        "theme": position.asset.theme,
        "quantity": _format_decimal(position.quantity),
        "average_cost": _format_decimal(position.average_cost),
        "current_price": _format_decimal(position.current_price),
        "market_value": _format_decimal(position.market_value()),
        "unrealized_pnl": _format_decimal(position.unrealized_pnl()),
    }


def _format_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}"
