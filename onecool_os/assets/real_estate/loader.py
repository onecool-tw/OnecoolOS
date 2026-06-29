"""JSON loader for the Real Estate asset module."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from onecool_os.assets.real_estate.models import (
    RealEstateAsset,
    RealEstateError,
    RealEstatePosition,
)
from onecool_os.portfolio.models import PortfolioError


class RealEstateLoaderError(PortfolioError):
    """Raised when a real estate JSON file cannot be loaded."""


@dataclass(frozen=True)
class RealEstateImportResult:
    """Loaded real estate positions."""

    positions: tuple[RealEstatePosition, ...]


class RealEstateLoader:
    """Load sample real estate holdings from JSON."""

    required_root_fields = frozenset({"properties"})
    required_property_fields = frozenset(
        {
            "asset_id",
            "asset_type",
            "name",
            "country",
            "city",
            "district",
            "address_label",
            "property_type",
            "currency",
            "area_ping",
            "building_age_years",
            "floor",
            "total_floors",
            "has_parking",
            "quantity",
            "purchase_price",
            "purchase_date",
            "current_estimated_value",
            "notes",
        }
    )

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("onecool_os.real_estate")

    def load(self, json_path: str | Path) -> RealEstateImportResult:
        """Load and validate a real estate JSON file."""

        path = Path(json_path)
        self.logger.info("Starting real estate import from %s", path)
        payload = self._read_payload(path)
        self._validate_required_fields(payload, self.required_root_fields, "root")
        properties_payload = payload["properties"]
        if not isinstance(properties_payload, list):
            raise RealEstateLoaderError("properties must be a list.")

        positions = tuple(
            self._load_position(property_payload, index)
            for index, property_payload in enumerate(properties_payload)
        )
        self.logger.info(
            "Real estate import completed with %s properties.",
            len(positions),
        )
        return RealEstateImportResult(positions=positions)

    def _read_payload(self, path: Path) -> dict[str, Any]:
        try:
            raw_payload = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.logger.error("Real estate JSON file cannot be read: %s", path)
            raise RealEstateLoaderError(
                f"Real estate JSON file cannot be read: {path}"
            ) from exc

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            self.logger.error("Invalid real estate JSON: %s", exc.msg)
            raise RealEstateLoaderError(
                f"Invalid real estate JSON: {exc.msg}"
            ) from exc

        if not isinstance(payload, dict):
            raise RealEstateLoaderError(
                "Real estate JSON root must be an object."
            )
        return payload

    def _load_position(self, payload: Any, index: int) -> RealEstatePosition:
        if not isinstance(payload, dict):
            raise RealEstateLoaderError(f"properties[{index}] must be an object.")
        self._validate_required_fields(
            payload,
            self.required_property_fields,
            f"properties[{index}]",
        )

        try:
            asset = RealEstateAsset(
                asset_id=self._require_text(payload["asset_id"], "asset_id"),
                asset_type=self._require_text(
                    payload["asset_type"],
                    "asset_type",
                ),
                name=self._require_text(payload["name"], "name"),
                country=self._require_text(payload["country"], "country"),
                city=self._require_text(payload["city"], "city"),
                district=self._require_text(payload["district"], "district"),
                address_label=self._require_text(
                    payload["address_label"],
                    "address_label",
                ),
                property_type=self._require_text(
                    payload["property_type"],
                    "property_type",
                ),
                currency=self._require_text(payload["currency"], "currency"),
                area_ping=self._parse_decimal(
                    payload["area_ping"],
                    "area_ping",
                    require_positive=True,
                ),
                building_age_years=self._parse_decimal(
                    payload["building_age_years"],
                    "building_age_years",
                ),
                floor=self._parse_int(payload["floor"], "floor"),
                total_floors=self._parse_int(
                    payload["total_floors"],
                    "total_floors",
                ),
                has_parking=self._parse_bool(
                    payload["has_parking"],
                    "has_parking",
                ),
            )
        except RealEstateError as exc:
            raise RealEstateLoaderError(str(exc)) from exc

        return RealEstatePosition(
            asset=asset,
            quantity=self._parse_decimal(
                payload["quantity"],
                "quantity",
                require_positive=True,
            ),
            purchase_price=self._parse_decimal(
                payload["purchase_price"],
                "purchase_price",
                require_positive=True,
            ),
            purchase_date=self._require_text(
                payload["purchase_date"],
                "purchase_date",
            ),
            current_estimated_value=self._parse_optional_decimal(
                payload.get("current_estimated_value"),
                "current_estimated_value",
            ),
            notes=self._optional_text(payload.get("notes")),
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
            raise RealEstateLoaderError(
                f"Missing required field in {location}: {fields}"
            )

    def _require_text(self, value: Any, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise RealEstateLoaderError(
                f"{field_name} must be a non-empty string."
            )
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
            raise RealEstateLoaderError(
                f"Invalid {field_name}: {value}"
            ) from exc

        if not decimal_value.is_finite():
            raise RealEstateLoaderError(f"Invalid {field_name}: {value}")
        if require_positive and decimal_value <= Decimal("0"):
            raise RealEstateLoaderError(f"Invalid {field_name}: {value}")
        return decimal_value

    def _parse_optional_decimal(
        self,
        value: Any,
        field_name: str,
    ) -> Decimal | None:
        if value is None or value == "":
            return None
        return self._parse_decimal(value, field_name, require_positive=True)

    def _parse_int(self, value: Any, field_name: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise RealEstateLoaderError(
                f"Invalid {field_name}: {value}"
            ) from exc

    def _parse_bool(self, value: Any, field_name: str) -> bool:
        if isinstance(value, bool):
            return value
        raise RealEstateLoaderError(f"Invalid {field_name}: {value}")


def real_estate_import_to_dict(
    result: RealEstateImportResult,
) -> dict[str, Any]:
    """Return JSON-safe real estate demo output."""

    return {
        "properties": [
            _real_estate_position_to_dict(position)
            for position in result.positions
        ]
    }


def _real_estate_position_to_dict(
    position: RealEstatePosition,
) -> dict[str, str | None]:
    return {
        "property_name": position.asset.name,
        "city_district": position.asset.location_label(),
        "property_type": position.asset.property_type,
        "area": f"{_format_decimal(position.asset.area_ping)} ping",
        "purchase_price": _format_decimal(position.purchase_price),
        "current_estimated_value": _format_decimal(
            position.current_estimated_value
        ),
        "unrealized_pnl": _format_decimal(position.unrealized_pnl()),
    }


def _format_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}"
