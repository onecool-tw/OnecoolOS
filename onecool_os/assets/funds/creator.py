"""Interactive creator for local fund portfolio files."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable

from onecool_os.assets.funds.loader import FundLoader, FundLoaderError

FUNDS_PORTFOLIO_PATH = Path("data/portfolio/funds.json")
SUPPORTED_CURRENCIES = frozenset({"TWD", "USD"})


class FundCreatorError(FundLoaderError):
    """Raised when an interactive fund portfolio cannot be created."""


@dataclass(frozen=True)
class FundCreateResult:
    """Result of an interactive fund portfolio create operation."""

    status: str
    path: Path
    portfolio_name: str | None = None
    position_count: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, str | int | None]:
        """Return a JSON-safe representation."""

        return {
            "status": self.status,
            "path": str(self.path),
            "portfolio_name": self.portfolio_name,
            "position_count": self.position_count,
            "message": self.message,
        }


class FundPortfolioCreator:
    """Create or update a local real fund portfolio JSON file."""

    def __init__(
        self,
        input_func: Callable[[str], str] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.input_func = input_func or input
        self.logger = logger or logging.getLogger("onecool_os.funds")

    def create(
        self,
        path: str | Path = FUNDS_PORTFOLIO_PATH,
    ) -> FundCreateResult:
        """Run the interactive creator and write a funds portfolio file."""

        portfolio_path = Path(path)
        existing_payload = self._load_existing_payload(portfolio_path)
        if existing_payload is None:
            mode = "replace"
            portfolio_name = self._ask_required_text("Portfolio name: ")
            positions: list[dict[str, str]] = []
        else:
            print("Existing portfolio found.")
            print("1. Append new fund")
            print("2. Replace portfolio")
            print("3. Cancel")
            mode = self._ask_existing_mode()
            if mode == "cancel":
                return FundCreateResult(
                    status="cancelled",
                    path=portfolio_path,
                    message="Portfolio creation cancelled.",
                )
            if mode == "append":
                portfolio_name = self._require_existing_name(existing_payload)
                positions = list(existing_payload.get("positions", []))
            else:
                portfolio_name = self._ask_required_text("Portfolio name: ")
                positions = []

        asset_ids = self._asset_ids(positions)
        while True:
            position = self._ask_position(asset_ids)
            positions.append(position)
            asset_ids.add(position["asset_id"])
            if not self._ask_yes_no("Add another fund? (Y/N): "):
                break

        payload = {
            "portfolio_name": portfolio_name,
            "positions": positions,
        }
        self._write_payload(portfolio_path, payload)
        self.logger.info(
            "Fund portfolio file saved with %s positions: %s",
            len(positions),
            portfolio_path,
        )
        return FundCreateResult(
            status="success",
            path=portfolio_path,
            portfolio_name=portfolio_name,
            position_count=len(positions),
            message="Fund portfolio saved.",
        )

    def _load_existing_payload(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        result = FundLoader(logger=self.logger).load(path)
        return {
            "portfolio_name": result.portfolio.name,
            "positions": [
                self._position_to_payload(position)
                for position in result.positions
            ],
        }

    def _position_to_payload(self, position: Any) -> dict[str, str]:
        payload = {
            "asset_id": position.asset.asset_id,
            "symbol": position.asset.symbol,
            "name": position.asset.name,
            "currency": position.asset.currency,
            "quantity": str(position.quantity),
            "average_cost": str(position.average_cost),
        }
        optional_fields = {
            "fund_house": position.asset.fund_house,
            "theme": position.asset.theme,
            "region": position.asset.region,
            "notes": position.notes,
        }
        for field_name, value in optional_fields.items():
            if value:
                payload[field_name] = value
        return payload

    def _ask_existing_mode(self) -> str:
        while True:
            choice = self.input_func("Choose an option (1/2/3): ").strip()
            if choice == "1":
                return "append"
            if choice == "2":
                return "replace"
            if choice == "3":
                return "cancel"
            print("Please choose 1, 2, or 3.")

    def _ask_position(self, existing_asset_ids: set[str]) -> dict[str, str]:
        while True:
            fund_code = self.input_func("Fund code (optional): ").strip()
            fund_name = self._ask_required_text("Fund name: ")
            asset_id = self._asset_id(fund_code, fund_name)
            if asset_id not in existing_asset_ids:
                break
            print(f"Duplicate asset_id is not allowed: {asset_id}")

        position = {
            "asset_id": asset_id,
            "symbol": fund_code.strip().upper() if fund_code else asset_id,
            "name": fund_name,
            "currency": self._ask_currency("Currency (TWD/USD): "),
            "quantity": self._ask_positive_decimal("Quantity: "),
            "average_cost": self._ask_positive_decimal("Average cost: "),
        }
        optional_values = {
            "fund_house": self.input_func("Fund house (optional): ").strip(),
            "theme": self.input_func("Theme (optional): ").strip(),
            "region": self.input_func("Region (optional): ").strip(),
            "notes": self.input_func("Notes (optional): ").strip(),
        }
        for field_name, value in optional_values.items():
            if value:
                position[field_name] = value
        return position

    def _ask_required_text(self, prompt: str) -> str:
        while True:
            value = self.input_func(prompt).strip()
            if value:
                return value
            print("This field is required.")

    def _ask_currency(self, prompt: str) -> str:
        while True:
            value = self.input_func(prompt).strip().upper()
            if value in SUPPORTED_CURRENCIES:
                return value
            print("Currency must be TWD or USD.")

    def _ask_positive_decimal(self, prompt: str) -> str:
        while True:
            value = self.input_func(prompt).strip()
            try:
                decimal_value = Decimal(value)
            except (InvalidOperation, ValueError):
                print("Please enter a valid positive number.")
                continue
            if decimal_value.is_finite() and decimal_value > Decimal("0"):
                return str(decimal_value)
            print("Please enter a valid positive number.")

    def _ask_yes_no(self, prompt: str) -> bool:
        while True:
            value = self.input_func(prompt).strip().upper()
            if value == "Y":
                return True
            if value == "N":
                return False
            print("Please enter Y or N.")

    def _require_existing_name(self, payload: dict[str, Any]) -> str:
        value = payload.get("portfolio_name")
        if not isinstance(value, str) or not value.strip():
            raise FundCreatorError("Existing portfolio_name is invalid.")
        return value.strip()

    def _asset_ids(self, positions: list[dict[str, Any]]) -> set[str]:
        asset_ids = set()
        for position in positions:
            asset_id = position.get("asset_id")
            if not isinstance(asset_id, str) or not asset_id.strip():
                raise FundCreatorError("Existing position asset_id is invalid.")
            asset_ids.add(asset_id.strip())
        return asset_ids

    def _asset_id(self, fund_code: str, fund_name: str) -> str:
        source = fund_code.strip() or fund_name.strip()
        normalized = re.sub(r"[^A-Z0-9]+", "-", source.upper()).strip("-")
        if not normalized:
            raise FundCreatorError("Fund asset_id cannot be generated.")
        return f"FUND-{normalized}"

    def _write_payload(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
