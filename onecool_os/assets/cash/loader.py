"""JSON loader for the Cash / FX asset module."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from onecool_os.assets.cash.models import CashAsset, CashError, CashPosition
from onecool_os.portfolio.models import PortfolioError


class CashLoaderError(PortfolioError):
    """Raised when a cash JSON file cannot be loaded."""


@dataclass(frozen=True)
class CashImportResult:
    """Loaded cash positions."""

    positions: tuple[CashPosition, ...]


class CashLoader:
    """Load demo cash balances from JSON."""

    required_root_fields = frozenset({"cash_accounts"})
    required_cash_fields = frozenset(
        {
            "asset_id",
            "asset_type",
            "name",
            "currency",
            "account_type",
            "amount",
            "fx_rate_to_base",
            "base_currency",
            "notes",
        }
    )

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("onecool_os.cash")

    def load(self, json_path: str | Path) -> CashImportResult:
        """Load and validate a cash JSON file."""

        path = Path(json_path)
        self.logger.info("Starting cash import from %s", path)
        payload = self._read_payload(path)
        self._validate_required_fields(payload, self.required_root_fields, "root")
        accounts_payload = payload["cash_accounts"]
        if not isinstance(accounts_payload, list):
            raise CashLoaderError("cash_accounts must be a list.")

        positions = tuple(
            self._load_position(account_payload, index)
            for index, account_payload in enumerate(accounts_payload)
        )
        self.logger.info(
            "Cash import completed with %s accounts.",
            len(positions),
        )
        return CashImportResult(positions=positions)

    def _read_payload(self, path: Path) -> dict[str, Any]:
        try:
            raw_payload = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.logger.error("Cash JSON file cannot be read: %s", path)
            raise CashLoaderError(f"Cash JSON file cannot be read: {path}") from exc

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            self.logger.error("Invalid cash JSON: %s", exc.msg)
            raise CashLoaderError(f"Invalid cash JSON: {exc.msg}") from exc

        if not isinstance(payload, dict):
            raise CashLoaderError("Cash JSON root must be an object.")
        return payload

    def _load_position(self, payload: Any, index: int) -> CashPosition:
        if not isinstance(payload, dict):
            raise CashLoaderError(f"cash_accounts[{index}] must be an object.")
        self._validate_required_fields(
            payload,
            self.required_cash_fields,
            f"cash_accounts[{index}]",
        )

        try:
            asset = CashAsset(
                asset_id=self._require_text(payload["asset_id"], "asset_id"),
                asset_type=self._require_text(
                    payload["asset_type"],
                    "asset_type",
                ),
                name=self._require_text(payload["name"], "name"),
                currency=self._require_text(payload["currency"], "currency"),
                account_type=self._require_text(
                    payload["account_type"],
                    "account_type",
                ),
                institution=self._optional_text(payload.get("institution")),
                country=self._optional_text(payload.get("country")),
            )
            return CashPosition(
                asset=asset,
                amount=self._parse_decimal(
                    payload["amount"],
                    "amount",
                    allow_zero=True,
                ),
                currency=self._require_text(payload["currency"], "currency"),
                fx_rate_to_base=self._parse_optional_decimal(
                    payload.get("fx_rate_to_base"),
                    "fx_rate_to_base",
                ),
                base_currency=self._require_text(
                    payload["base_currency"],
                    "base_currency",
                ),
                notes=self._optional_text(payload.get("notes")) or "",
            )
        except CashError as exc:
            raise CashLoaderError(str(exc)) from exc

    def _validate_required_fields(
        self,
        payload: dict[str, Any],
        required_fields: frozenset[str],
        location: str,
    ) -> None:
        missing_fields = sorted(required_fields - payload.keys())
        if missing_fields:
            fields = ", ".join(missing_fields)
            raise CashLoaderError(
                f"Missing required field in {location}: {fields}"
            )

    def _require_text(self, value: Any, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise CashLoaderError(f"{field_name} must be a non-empty string.")
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
        allow_zero: bool = False,
    ) -> Decimal:
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise CashLoaderError(f"Invalid {field_name}: {value}") from exc

        if not decimal_value.is_finite():
            raise CashLoaderError(f"Invalid {field_name}: {value}")
        if allow_zero:
            if decimal_value < Decimal("0"):
                raise CashLoaderError(f"Invalid {field_name}: {value}")
        elif decimal_value <= Decimal("0"):
            raise CashLoaderError(f"Invalid {field_name}: {value}")
        return decimal_value

    def _parse_optional_decimal(
        self,
        value: Any,
        field_name: str,
    ) -> Decimal | None:
        if value is None or value == "":
            return None
        return self._parse_decimal(value, field_name)


def cash_import_to_dict(result: CashImportResult) -> dict[str, Any]:
    """Return JSON-safe cash demo output."""

    return {
        "cash_accounts": [
            _cash_position_to_dict(position)
            for position in result.positions
        ]
    }


def _cash_position_to_dict(position: CashPosition) -> dict[str, str | None]:
    return {
        "cash_account": position.asset.name,
        "currency": position.currency,
        "amount": _format_decimal(position.amount),
        "fx_rate_to_base": _format_decimal(position.fx_rate_to_base),
        "base_currency_value": _format_decimal(position.market_value_base()),
    }


def _format_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}"
