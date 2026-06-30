"""Interactive creator for local securities portfolio files."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable

from onecool_os.assets.securities.loader import (
    SecurityLoader,
    SecurityLoaderError,
)
from onecool_os.assets.securities.models import (
    SUPPORTED_CURRENCIES,
    SUPPORTED_MARKETS,
    SUPPORTED_SECURITY_TYPES,
)

SECURITIES_PORTFOLIO_PATH = Path("data/portfolio/securities.json")


class SecurityCreatorError(SecurityLoaderError):
    """Raised when an interactive securities portfolio cannot be created."""


@dataclass(frozen=True)
class SecurityCreateResult:
    """Result of an interactive securities create operation."""

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


class SecurityCreator:
    """Create or update a local real securities portfolio JSON file."""

    def __init__(
        self,
        input_func: Callable[[str], str] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.input_func = input_func or input
        self.logger = logger or logging.getLogger("onecool_os.securities")

    def create(
        self,
        path: str | Path = SECURITIES_PORTFOLIO_PATH,
    ) -> SecurityCreateResult:
        """Run the interactive creator and write a securities file."""

        portfolio_path = Path(path)
        existing_payload = self._load_existing_payload(portfolio_path)
        if existing_payload is None:
            portfolio_name = self._ask_required_text("Portfolio name: ")
            positions: list[dict[str, str]] = []
        else:
            print("Existing portfolio found.")
            print("1. Append new security")
            print("2. Replace portfolio")
            print("3. Cancel")
            mode = self._ask_existing_mode()
            if mode == "cancel":
                return SecurityCreateResult(
                    status="cancelled",
                    path=portfolio_path,
                    message="Securities portfolio creation cancelled.",
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
            if not self._ask_yes_no("Add another security? (Y/N): "):
                break

        payload = {
            "portfolio_name": portfolio_name,
            "positions": positions,
        }
        self._write_payload(portfolio_path, payload)
        self.logger.info(
            "Securities portfolio file saved with %s positions: %s",
            len(positions),
            portfolio_path,
        )
        return SecurityCreateResult(
            status="success",
            path=portfolio_path,
            portfolio_name=portfolio_name,
            position_count=len(positions),
            message="Securities portfolio saved.",
        )

    def _load_existing_payload(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        result = SecurityLoader(logger=self.logger).load(path)
        return {
            "portfolio_name": result.portfolio_name,
            "positions": [
                self._position_to_payload(position)
                for position in result.positions
            ],
        }

    def _position_to_payload(self, position: Any) -> dict[str, str]:
        payload = {
            "asset_id": position.asset.asset_id,
            "symbol": position.asset.symbol,
            "asset_type": position.asset.asset_type,
            "name": position.asset.name,
            "currency": position.asset.currency,
            "market": position.asset.market,
            "quantity": str(position.quantity),
            "average_cost": str(position.average_cost),
        }
        optional_fields = {
            "exchange": position.asset.exchange,
            "country": position.asset.country,
            "sector": position.asset.sector,
            "theme": position.asset.theme,
            "purchase_date": position.purchase_date,
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
            symbol = self._ask_required_text("Symbol: ").upper()
            name = self._ask_required_text("Security name: ")
            market = self._ask_choice("Market (US/TW/OTHER): ", SUPPORTED_MARKETS)
            asset_type = self._ask_choice(
                "Asset type (STOCK/ETF/OTHER): ",
                SUPPORTED_SECURITY_TYPES,
            )
            asset_id = self._asset_id(symbol, market)
            if asset_id not in existing_asset_ids:
                break
            print(f"Duplicate asset_id is not allowed: {asset_id}")

        position = {
            "asset_id": asset_id,
            "symbol": symbol,
            "name": name,
            "market": market,
            "asset_type": asset_type,
            "currency": self._ask_choice(
                "Currency (USD/TWD): ",
                SUPPORTED_CURRENCIES,
            ),
            "quantity": self._ask_positive_decimal("Quantity: "),
            "average_cost": self._ask_positive_decimal("Average cost: "),
        }
        optional_values = {
            "exchange": self.input_func("Exchange optional: ").strip(),
            "country": self.input_func("Country optional: ").strip(),
            "sector": self.input_func("Sector optional: ").strip(),
            "theme": self.input_func("Theme optional: ").strip(),
            "notes": self.input_func("Notes optional: ").strip(),
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

    def _ask_choice(self, prompt: str, choices: frozenset[str]) -> str:
        while True:
            value = self.input_func(prompt).strip().upper()
            if value in choices:
                return value
            print(f"Value must be one of: {', '.join(sorted(choices))}.")

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
            raise SecurityCreatorError("Existing portfolio_name is invalid.")
        return value.strip()

    def _asset_ids(self, positions: list[dict[str, Any]]) -> set[str]:
        asset_ids = set()
        for position in positions:
            asset_id = position.get("asset_id")
            if not isinstance(asset_id, str) or not asset_id.strip():
                raise SecurityCreatorError(
                    "Existing position asset_id is invalid."
                )
            asset_ids.add(asset_id.strip())
        return asset_ids

    def _asset_id(self, symbol: str, market: str) -> str:
        source = f"{market}-{symbol}"
        normalized = re.sub(r"[^A-Z0-9]+", "-", source.upper()).strip("-")
        if not normalized:
            raise SecurityCreatorError("Security asset_id cannot be generated.")
        return f"SECURITY-{normalized}"

    def _write_payload(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
