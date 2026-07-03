"""JSON loader for analytics snapshots."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from onecool_os.analytics.models import AnalyticsSnapshot
from onecool_os.analytics.validation import AnalyticsError
from onecool_os.analytics.validation import optional_text
from onecool_os.analytics.validation import require_currency


class AnalyticsLoaderError(AnalyticsError):
    """Raised when analytics JSON cannot be loaded."""


@dataclass(frozen=True)
class AnalyticsImportResult:
    """Loaded analytics book data."""

    analytics_book_name: str | None
    base_currency: str | None
    snapshots: tuple[AnalyticsSnapshot, ...]


class AnalyticsLoader:
    """Load analytics snapshots from JSON."""

    required_snapshot_fields = frozenset(
        {
            "snapshot_id",
            "portfolio_id",
            "base_currency",
            "snapshot_date",
        }
    )

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("onecool_os.analytics")

    def load(self, json_path: str | Path) -> AnalyticsImportResult:
        """Load and validate an analytics book JSON file."""

        path = Path(json_path)
        self.logger.info("Starting analytics import from %s", path)
        payload = self._read_payload(path)
        snapshots_payload = payload.get("snapshots")
        if not isinstance(snapshots_payload, list):
            raise AnalyticsLoaderError("snapshots must be a list.")

        snapshots = tuple(
            self._load_snapshot(snapshot_payload, index)
            for index, snapshot_payload in enumerate(snapshots_payload)
        )
        self._validate_duplicate_ids(
            [snapshot.snapshot_id for snapshot in snapshots],
        )
        self.logger.info(
            "Analytics import completed with %s snapshots.",
            len(snapshots),
        )
        base_currency = payload.get("base_currency")
        return AnalyticsImportResult(
            analytics_book_name=optional_text(
                payload.get("analytics_book_name"),
                "analytics_book_name",
            ),
            base_currency=(
                require_currency(base_currency)
                if base_currency not in (None, "")
                else None
            ),
            snapshots=snapshots,
        )

    def _read_payload(self, path: Path) -> dict[str, Any]:
        try:
            raw_payload = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise AnalyticsLoaderError(
                f"Analytics JSON file cannot be read: {path}"
            ) from exc

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise AnalyticsLoaderError(
                f"Invalid analytics JSON: {exc.msg}"
            ) from exc

        if not isinstance(payload, dict):
            raise AnalyticsLoaderError(
                "Analytics JSON root must be an object."
            )
        return payload

    def _load_snapshot(self, payload: Any, index: int) -> AnalyticsSnapshot:
        if not isinstance(payload, dict):
            raise AnalyticsLoaderError(
                f"snapshots[{index}] must be an object."
            )
        self._validate_required_fields(
            payload,
            self.required_snapshot_fields,
            f"snapshots[{index}]",
        )
        try:
            return AnalyticsSnapshot(
                snapshot_id=payload["snapshot_id"],
                portfolio_id=payload["portfolio_id"],
                base_currency=payload["base_currency"],
                snapshot_date=payload["snapshot_date"],
                created_at=payload.get("created_at"),
                total_cost=payload.get("total_cost"),
                total_market_value=payload.get("total_market_value"),
                unrealized_gain=payload.get("unrealized_gain"),
                unrealized_return=payload.get("unrealized_return"),
                realized_gain=payload.get("realized_gain"),
                realized_return=payload.get("realized_return"),
                asset_class_weights=payload.get("asset_class_weights"),
                currency_weights=payload.get("currency_weights"),
                account_weights=payload.get("account_weights"),
                cash_inflow=payload.get("cash_inflow"),
                cash_outflow=payload.get("cash_outflow"),
                net_cash_flow=payload.get("net_cash_flow"),
                risk_score=payload.get("risk_score"),
                risk_level=payload.get("risk_level"),
                note=payload.get("note"),
                tags=payload.get("tags"),
            )
        except AnalyticsError as exc:
            raise AnalyticsLoaderError(str(exc)) from exc

    def _validate_required_fields(
        self,
        payload: dict[str, Any],
        required_fields: frozenset[str],
        location: str,
    ) -> None:
        missing_fields = sorted(required_fields - payload.keys())
        if missing_fields:
            fields = ", ".join(missing_fields)
            raise AnalyticsLoaderError(
                f"Missing required field in {location}: {fields}"
            )

    def _validate_duplicate_ids(self, values: list[str]) -> None:
        seen: set[str] = set()
        for value in values:
            if value in seen:
                raise AnalyticsLoaderError(f"Duplicate snapshot_id: {value}")
            seen.add(value)
