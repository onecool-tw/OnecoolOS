"""JSON loader for universal valuation records."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from onecool_os.valuation.models import ValuationRecord
from onecool_os.valuation.validation import ValuationError
from onecool_os.valuation.validation import optional_text
from onecool_os.valuation.validation import require_currency


class ValuationLoaderError(ValuationError):
    """Raised when valuation JSON cannot be loaded."""


@dataclass(frozen=True)
class ValuationImportResult:
    """Loaded valuation book data."""

    valuation_book_name: str | None
    base_currency: str | None
    valuations: tuple[ValuationRecord, ...]


class ValuationLoader:
    """Load shared valuation records from JSON."""

    required_valuation_fields = frozenset(
        {
            "valuation_id",
            "asset_id",
            "asset_type",
            "source",
            "currency",
            "valuation_date",
            "confidence",
        }
    )

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("onecool_os.valuation")

    def load(self, json_path: str | Path) -> ValuationImportResult:
        """Load and validate a valuation book JSON file."""

        path = Path(json_path)
        self.logger.info("Starting valuation import from %s", path)
        payload = self._read_payload(path)
        valuations_payload = payload.get("valuations")
        if not isinstance(valuations_payload, list):
            raise ValuationLoaderError("valuations must be a list.")

        valuations = tuple(
            self._load_valuation(valuation_payload, index)
            for index, valuation_payload in enumerate(valuations_payload)
        )
        self._validate_duplicate_ids(
            [valuation.valuation_id for valuation in valuations],
        )
        self.logger.info(
            "Valuation import completed with %s records.",
            len(valuations),
        )
        base_currency = payload.get("base_currency")
        return ValuationImportResult(
            valuation_book_name=optional_text(
                payload.get("valuation_book_name"),
                "valuation_book_name",
            ),
            base_currency=(
                require_currency(base_currency)
                if base_currency not in (None, "")
                else None
            ),
            valuations=valuations,
        )

    def _read_payload(self, path: Path) -> dict[str, Any]:
        try:
            raw_payload = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValuationLoaderError(
                f"Valuation JSON file cannot be read: {path}"
            ) from exc

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise ValuationLoaderError(
                f"Invalid valuation JSON: {exc.msg}"
            ) from exc

        if not isinstance(payload, dict):
            raise ValuationLoaderError(
                "Valuation JSON root must be an object."
            )
        return payload

    def _load_valuation(self, payload: Any, index: int) -> ValuationRecord:
        if not isinstance(payload, dict):
            raise ValuationLoaderError(
                f"valuations[{index}] must be an object."
            )
        self._validate_required_fields(
            payload,
            self.required_valuation_fields,
            f"valuations[{index}]",
        )
        try:
            return ValuationRecord(
                valuation_id=payload["valuation_id"],
                asset_id=payload["asset_id"],
                asset_type=payload["asset_type"],
                source=payload["source"],
                source_priority=payload.get("source_priority"),
                currency=payload["currency"],
                market_value=payload.get("market_value"),
                estimated_value=payload.get("estimated_value"),
                low_value=payload.get("low_value"),
                high_value=payload.get("high_value"),
                valuation_date=payload["valuation_date"],
                effective_date=payload.get("effective_date"),
                confidence=payload["confidence"],
                note=payload.get("note"),
                url=payload.get("url"),
                tags=payload.get("tags"),
            )
        except ValuationError as exc:
            raise ValuationLoaderError(str(exc)) from exc

    def _validate_required_fields(
        self,
        payload: dict[str, Any],
        required_fields: frozenset[str],
        location: str,
    ) -> None:
        missing_fields = sorted(required_fields - payload.keys())
        if missing_fields:
            fields = ", ".join(missing_fields)
            raise ValuationLoaderError(
                f"Missing required field in {location}: {fields}"
            )

    def _validate_duplicate_ids(self, values: list[str]) -> None:
        seen: set[str] = set()
        for value in values:
            if value in seen:
                raise ValuationLoaderError(f"Duplicate valuation_id: {value}")
            seen.add(value)
