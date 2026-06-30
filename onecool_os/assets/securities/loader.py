"""JSON loader for the Securities asset module."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from onecool_os.assets.securities.models import (
    SecurityAsset,
    SecurityError,
    SecurityPosition,
)
from onecool_os.portfolio.models import PortfolioError


class SecurityLoaderError(PortfolioError):
    """Raised when a securities JSON file cannot be loaded."""


@dataclass(frozen=True)
class SecurityImportResult:
    """Loaded securities positions."""

    portfolio_name: str
    positions: tuple[SecurityPosition, ...]


class SecurityLoader:
    """Load listed securities from a local JSON file."""

    required_root_fields = frozenset({"portfolio_name", "positions"})
    required_position_fields = frozenset(
        {
            "asset_id",
            "symbol",
            "asset_type",
            "name",
            "currency",
            "market",
            "quantity",
            "average_cost",
        }
    )

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("onecool_os.securities")

    def load(self, json_path: str | Path) -> SecurityImportResult:
        """Load and validate a securities JSON file."""

        path = Path(json_path)
        self.logger.info("Starting securities import from %s", path)
        payload = self._read_payload(path)
        self._validate_required_fields(payload, self.required_root_fields, "root")
        portfolio_name = self._require_text(
            payload["portfolio_name"],
            "portfolio_name",
        )
        positions_payload = payload["positions"]
        if not isinstance(positions_payload, list):
            raise SecurityLoaderError("positions must be a list.")

        positions = []
        asset_ids = set()
        for index, position_payload in enumerate(positions_payload):
            position = self._load_position(position_payload, index)
            if position.asset.asset_id in asset_ids:
                raise SecurityLoaderError(
                    f"Duplicate asset_id: {position.asset.asset_id}"
                )
            asset_ids.add(position.asset.asset_id)
            positions.append(position)

        self.logger.info(
            "Securities import completed with %s positions.",
            len(positions),
        )
        return SecurityImportResult(
            portfolio_name=portfolio_name,
            positions=tuple(positions),
        )

    def _read_payload(self, path: Path) -> dict[str, Any]:
        try:
            raw_payload = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.logger.error("Securities JSON file cannot be read: %s", path)
            raise SecurityLoaderError(
                f"Securities JSON file cannot be read: {path}"
            ) from exc

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            self.logger.error("Invalid securities JSON: %s", exc.msg)
            raise SecurityLoaderError(
                f"Invalid securities JSON: {exc.msg}"
            ) from exc

        if not isinstance(payload, dict):
            raise SecurityLoaderError("Securities JSON root must be an object.")
        return payload

    def _load_position(self, payload: Any, index: int) -> SecurityPosition:
        if not isinstance(payload, dict):
            raise SecurityLoaderError(f"positions[{index}] must be an object.")
        self._validate_required_fields(
            payload,
            self.required_position_fields,
            f"positions[{index}]",
        )

        try:
            asset = SecurityAsset(
                asset_id=self._require_text(payload["asset_id"], "asset_id"),
                symbol=self._require_text(payload["symbol"], "symbol"),
                asset_type=self._require_text(
                    payload["asset_type"],
                    "asset_type",
                ),
                name=self._require_text(payload["name"], "name"),
                currency=self._require_text(payload["currency"], "currency"),
                market=self._require_text(payload["market"], "market"),
                exchange=self._optional_text(payload.get("exchange")),
                country=self._optional_text(payload.get("country")),
                sector=self._optional_text(payload.get("sector")),
                theme=self._optional_text(payload.get("theme")),
                notes=self._optional_text(payload.get("notes")) or "",
            )
            return SecurityPosition(
                asset=asset,
                quantity=self._parse_decimal(
                    payload["quantity"],
                    "quantity",
                ),
                average_cost=self._parse_decimal(
                    payload["average_cost"],
                    "average_cost",
                ),
                purchase_date=self._optional_text(
                    payload.get("purchase_date"),
                ),
                notes=self._optional_text(payload.get("notes")) or "",
            )
        except SecurityError as exc:
            raise SecurityLoaderError(str(exc)) from exc

    def _validate_required_fields(
        self,
        payload: dict[str, Any],
        required_fields: frozenset[str],
        location: str,
    ) -> None:
        missing_fields = sorted(required_fields - payload.keys())
        if missing_fields:
            fields = ", ".join(missing_fields)
            raise SecurityLoaderError(
                f"Missing required field in {location}: {fields}"
            )

    def _require_text(self, value: Any, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise SecurityLoaderError(f"{field_name} must be a non-empty string.")
        return value.strip()

    def _optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            return None
        return value.strip()

    def _parse_decimal(self, value: Any, field_name: str) -> Decimal:
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise SecurityLoaderError(f"Invalid {field_name}: {value}") from exc

        if not decimal_value.is_finite() or decimal_value <= Decimal("0"):
            raise SecurityLoaderError(f"Invalid {field_name}: {value}")
        return decimal_value


def security_import_to_dict(result: SecurityImportResult) -> dict[str, Any]:
    """Return JSON-safe securities import output."""

    return {
        "portfolio_name": result.portfolio_name,
        "securities": [
            _security_position_to_dict(position)
            for position in result.positions
        ],
    }


def _security_position_to_dict(
    position: SecurityPosition,
) -> dict[str, str]:
    return {
        "security": position.asset.name,
        "symbol": position.asset.symbol,
        "market": position.asset.market,
        "asset_type": position.asset.asset_type,
        "quantity": _format_decimal(position.quantity),
        "average_cost": _format_decimal(position.average_cost),
        "total_cost": _format_decimal(position.total_cost()),
    }


def _format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"
