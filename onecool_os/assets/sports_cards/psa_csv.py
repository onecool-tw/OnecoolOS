"""PSA Collection CSV importer for the Sports Cards asset module."""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from onecool_os.assets.sports_cards.loader import (
    CardLoader,
    CardLoaderError,
)

SPORTS_CARDS_PORTFOLIO_PATH = Path("data/portfolio/sports_cards.json")

PSA_REQUIRED_FIELDS = (
    "Item",
    "Subject",
    "Year",
    "Set",
    "Card Number",
    "Grade Issuer",
    "Grade",
    "Cert Number",
    "My Cost",
    "Date Acquired",
    "Source",
    "My Notes",
)


class PsaCsvImportError(CardLoaderError):
    """Raised when a PSA Collection CSV cannot be imported."""


@dataclass(frozen=True)
class PsaCsvImportResult:
    """Result of importing a PSA Collection CSV file."""

    status: str
    csv_path: Path
    output_path: Path
    imported_count: int
    skipped_duplicates: int
    total_cards: int
    message: str

    def to_dict(self) -> dict[str, str | int]:
        """Return a JSON-safe representation."""

        return {
            "status": self.status,
            "csv_path": str(self.csv_path),
            "output_path": str(self.output_path),
            "imported_count": self.imported_count,
            "skipped_duplicates": self.skipped_duplicates,
            "total_cards": self.total_cards,
            "message": self.message,
        }


class PsaCsvImporter:
    """Import PSA Collection CSV rows into the local cards portfolio file."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("onecool_os.cards")

    def import_csv(
        self,
        csv_path: str | Path,
        output_path: str | Path = SPORTS_CARDS_PORTFOLIO_PATH,
    ) -> PsaCsvImportResult:
        """Append PSA Collection CSV rows to the local cards portfolio."""

        source_path = Path(csv_path)
        target_path = Path(output_path)
        rows = self._read_rows(source_path)
        payload = self._load_existing_payload(target_path)
        cards = payload["cards"]
        existing_cert_numbers = self._existing_cert_numbers(cards)

        imported_cards: list[dict[str, Any]] = []
        skipped_duplicates = 0
        seen_cert_numbers: set[str] = set()
        for row_number, row in enumerate(rows, start=2):
            cert_number = self._require_text(
                row.get("Cert Number"),
                "Cert Number",
                row_number,
            )
            if (
                cert_number in existing_cert_numbers
                or cert_number in seen_cert_numbers
            ):
                skipped_duplicates += 1
                continue
            imported_cards.append(self._row_to_card(row, row_number))
            seen_cert_numbers.add(cert_number)

        cards.extend(imported_cards)
        self._write_payload(target_path, payload)
        total_cards = len(cards)
        return PsaCsvImportResult(
            status="success",
            csv_path=source_path,
            output_path=target_path,
            imported_count=len(imported_cards),
            skipped_duplicates=skipped_duplicates,
            total_cards=total_cards,
            message="PSA Collection CSV imported.",
        )

    def _read_rows(self, path: Path) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                self._validate_headers(reader.fieldnames)
                return [dict(row) for row in reader]
        except OSError as exc:
            raise PsaCsvImportError(
                f"PSA CSV file cannot be read: {path}"
            ) from exc
        except csv.Error as exc:
            raise PsaCsvImportError(f"Invalid PSA CSV: {exc}") from exc

    def _validate_headers(self, fieldnames: list[str] | None) -> None:
        if fieldnames is None:
            raise PsaCsvImportError("PSA CSV is missing a header row.")
        missing_fields = sorted(set(PSA_REQUIRED_FIELDS) - set(fieldnames))
        if missing_fields:
            fields = ", ".join(missing_fields)
            raise PsaCsvImportError(f"Missing PSA CSV field: {fields}")

    def _load_existing_payload(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {
                "portfolio_name": "Onecool Sports Cards",
                "base_currency": "TWD",
                "cards": [],
            }
        try:
            raw_payload = path.read_text(encoding="utf-8")
            payload = json.loads(raw_payload)
        except OSError as exc:
            raise PsaCsvImportError(
                f"Sports cards portfolio cannot be read: {path}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise PsaCsvImportError(
                f"Invalid sports cards JSON: {exc.msg}"
            ) from exc

        if not isinstance(payload, dict):
            raise PsaCsvImportError(
                "Sports cards portfolio root must be an object."
            )
        CardLoader(logger=self.logger).load(path)
        payload.setdefault("portfolio_name", "Onecool Sports Cards")
        payload.setdefault("base_currency", "TWD")
        payload.setdefault("cards", [])
        if not isinstance(payload["cards"], list):
            raise PsaCsvImportError("cards must be a list.")
        return payload

    def _existing_cert_numbers(self, cards: list[Any]) -> set[str]:
        cert_numbers: set[str] = set()
        for card in cards:
            if not isinstance(card, dict):
                continue
            cert_number = self._optional_text(
                card.get("serial_number") or card.get("cert_number")
            )
            if cert_number:
                cert_numbers.add(cert_number)
        return cert_numbers

    def _row_to_card(
        self,
        row: dict[str, str],
        row_number: int,
    ) -> dict[str, Any]:
        cert_number = self._require_text(
            row.get("Cert Number"),
            "Cert Number",
            row_number,
        )
        cost = self._parse_positive_decimal(
            row.get("My Cost"),
            "My Cost",
            row_number,
        )
        grade_issuer = self._require_text(
            row.get("Grade Issuer"),
            "Grade Issuer",
            row_number,
        )
        grade = self._require_text(row.get("Grade"), "Grade", row_number)
        set_name = self._require_text(row.get("Set"), "Set", row_number)
        notes = self._optional_text(row.get("My Notes"))
        item = self._require_text(row.get("Item"), "Item", row_number)
        if notes:
            notes = f"{notes} | PSA Item: {item}"
        else:
            notes = f"PSA Item: {item}"

        return {
            "account": "PSA Collection",
            "asset_class": "Sports Card",
            "status": "Owned",
            "currency": "USD",
            "base_currency": "TWD",
            "cost": str(cost),
            "asset_id": f"PSA-{cert_number}",
            "player": self._require_text(
                row.get("Subject"),
                "Subject",
                row_number,
            ),
            "year": self._require_text(row.get("Year"), "Year", row_number),
            "sport": "Unknown",
            "brand": set_name,
            "set": set_name,
            "card_number": self._require_text(
                row.get("Card Number"),
                "Card Number",
                row_number,
            ),
            "parallel": "",
            "serial_number": cert_number,
            "grade_company": grade_issuer,
            "grade": grade,
            "purchase_date": self._require_text(
                row.get("Date Acquired"),
                "Date Acquired",
                row_number,
            ),
            "purchase_platform": self._optional_text(row.get("Source")),
            "collection_type": "Investment",
            "valuation_source": "eBay Sold",
            "notes": notes,
        }

    def _write_payload(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _require_text(
        self,
        value: Any,
        field_name: str,
        row_number: int,
    ) -> str:
        if not isinstance(value, str) or not value.strip():
            raise PsaCsvImportError(
                f"Missing PSA CSV value at row {row_number}: {field_name}"
            )
        return value.strip()

    def _optional_text(self, value: Any) -> str:
        if not isinstance(value, str):
            return ""
        return value.strip()

    def _parse_positive_decimal(
        self,
        value: Any,
        field_name: str,
        row_number: int,
    ) -> Decimal:
        try:
            decimal_value = Decimal(str(value).strip())
        except (AttributeError, InvalidOperation, ValueError) as exc:
            raise PsaCsvImportError(
                f"Invalid PSA CSV value at row {row_number}: {field_name}"
            ) from exc
        if not decimal_value.is_finite() or decimal_value <= Decimal("0"):
            raise PsaCsvImportError(
                f"Invalid PSA CSV value at row {row_number}: {field_name}"
            )
        return decimal_value
