"""JSON loader for the Sports Cards asset module."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from onecool_os.assets.sports_cards.models import (
    CardAsset,
    CardError,
    CardPosition,
    VALUATION_SOURCE_PRIORITY,
)
from onecool_os.portfolio.models import PortfolioError


class CardLoaderError(PortfolioError):
    """Raised when a cards JSON file cannot be loaded."""


@dataclass(frozen=True)
class CardImportResult:
    """Loaded sports card positions."""

    portfolio_name: str | None
    base_currency: str | None
    positions: tuple[CardPosition, ...]


class CardLoader:
    """Load sample sports card holdings from JSON."""

    required_root_fields = frozenset({"cards"})
    required_card_fields = frozenset(
        {
            "asset_id",
            "player",
            "sport",
            "year",
            "brand",
            "set",
            "card_number",
            "grader",
            "grade",
            "parallel",
            "serial_number",
            "currency",
            "quantity",
            "purchase_price",
            "purchase_date",
            "notes",
        }
    )

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("onecool_os.cards")

    def load(self, json_path: str | Path) -> CardImportResult:
        """Load and validate a cards JSON file."""

        path = Path(json_path)
        self.logger.info("Starting cards import from %s", path)
        payload = self._read_payload(path)
        self._validate_required_fields(payload, self.required_root_fields, "root")
        portfolio_name = self._optional_text(payload.get("portfolio_name"))
        base_currency = self._optional_text(payload.get("base_currency"))
        cards_payload = payload["cards"]
        if not isinstance(cards_payload, list):
            raise CardLoaderError("cards must be a list.")

        positions = tuple(
            self._load_position(card_payload, index)
            for index, card_payload in enumerate(cards_payload)
        )
        self.logger.info("Cards import completed with %s cards.", len(positions))
        return CardImportResult(
            portfolio_name=portfolio_name,
            base_currency=base_currency,
            positions=positions,
        )

    def _read_payload(self, path: Path) -> dict[str, Any]:
        try:
            raw_payload = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.logger.error("Cards JSON file cannot be read: %s", path)
            raise CardLoaderError(
                f"Cards JSON file cannot be read: {path}"
            ) from exc

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            self.logger.error("Invalid cards JSON: %s", exc.msg)
            raise CardLoaderError(f"Invalid cards JSON: {exc.msg}") from exc

        if not isinstance(payload, dict):
            raise CardLoaderError("Cards JSON root must be an object.")
        return payload

    def _load_position(self, payload: Any, index: int) -> CardPosition:
        if not isinstance(payload, dict):
            raise CardLoaderError(f"cards[{index}] must be an object.")
        self._validate_card_fields(payload, index)
        grade_company = payload.get("grade_company", payload.get("grader"))
        purchase_price = payload.get("purchase_price", payload.get("cost"))

        try:
            asset = CardAsset(
                asset_id=self._require_text(payload["asset_id"], "asset_id"),
                player=self._require_text(payload["player"], "player"),
                sport=self._require_text(payload["sport"], "sport"),
                year=self._require_text(payload["year"], "year"),
                brand=self._require_text(payload["brand"], "brand"),
                set=self._require_text(payload["set"], "set"),
                card_number=self._require_text(
                    payload["card_number"],
                    "card_number",
                ),
                grader=self._require_text(grade_company, "grade_company"),
                grade=self._require_text(payload["grade"], "grade"),
                parallel=self._optional_text(payload.get("parallel")),
                serial_number=self._optional_text(
                    payload.get("serial_number"),
                ),
                currency=self._require_text(payload["currency"], "currency"),
            )
            return CardPosition(
                asset=asset,
                quantity=self._parse_decimal(
                    payload.get("quantity", "1"),
                    "quantity",
                    require_positive=True,
                ),
                purchase_price=self._parse_decimal(
                    purchase_price,
                    "purchase_price",
                    require_positive=True,
                ),
                purchase_date=self._require_text(
                    payload["purchase_date"],
                    "purchase_date",
                ),
                notes=self._optional_text(payload.get("notes")),
                account=self._optional_text(payload.get("account")),
                asset_class=self._optional_text(payload.get("asset_class")),
                status=self._optional_text(payload.get("status")),
                base_currency=self._optional_text(payload.get("base_currency")),
                cost=(
                    self._parse_decimal(payload["cost"], "cost")
                    if "cost" in payload
                    else None
                ),
                purchase_platform=self._optional_text(
                    payload.get("purchase_platform"),
                ),
                collection_type=self._optional_text(
                    payload.get("collection_type"),
                ),
                valuation_source=self._optional_text(
                    payload.get("valuation_source"),
                ),
            )
        except CardError as exc:
            raise CardLoaderError(str(exc)) from exc

    def _validate_card_fields(self, payload: dict[str, Any], index: int) -> None:
        required_fields = set(self.required_card_fields)
        if "grade_company" in payload:
            required_fields.discard("grader")
        if "cost" in payload:
            required_fields.discard("purchase_price")
        required_fields.discard("notes")
        required_fields.discard("quantity")
        self._validate_required_fields(
            payload,
            frozenset(required_fields),
            f"cards[{index}]",
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
            raise CardLoaderError(
                f"Missing required field in {location}: {fields}"
            )

    def _require_text(self, value: Any, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise CardLoaderError(f"{field_name} must be a non-empty string.")
        return value.strip()

    def _optional_text(self, value: Any) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            return ""
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
            raise CardLoaderError(f"Invalid {field_name}: {value}") from exc

        if not decimal_value.is_finite():
            raise CardLoaderError(f"Invalid {field_name}: {value}")
        if require_positive and decimal_value <= Decimal("0"):
            raise CardLoaderError(f"Invalid {field_name}: {value}")
        return decimal_value


def card_import_to_dict(result: CardImportResult) -> dict[str, Any]:
    """Return JSON-safe cards demo output."""

    return {
        "portfolio_name": result.portfolio_name,
        "base_currency": result.base_currency,
        "valuation_source_priority": list(VALUATION_SOURCE_PRIORITY),
        "cards": [
            _card_position_to_dict(position)
            for position in result.positions
        ]
    }


def _card_position_to_dict(position: CardPosition) -> dict[str, Any]:
    return {
        "player": position.asset.player,
        "card": position.asset.display_name(),
        "grade_company": position.asset.grade_company,
        "grade": f"{position.asset.grade_company} {position.asset.grade}",
        "account": position.account,
        "asset_class": position.asset_class,
        "status": position.status,
        "currency": position.asset.currency,
        "base_currency": position.base_currency,
        "cost": _format_optional_decimal(position.cost),
        "purchase_date": position.purchase_date,
        "purchase_platform": position.purchase_platform,
        "collection_type": position.collection_type,
        "valuation_source": position.valuation_source,
        "quantity": _format_decimal(position.quantity),
        "purchase_price": _format_decimal(position.purchase_price),
    }


def _format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def _format_optional_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _format_decimal(value)
