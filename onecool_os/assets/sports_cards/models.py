"""Sports Cards asset models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from onecool_os.portfolio.models import Asset, PortfolioError


class CardError(PortfolioError):
    """Raised for sports card model errors."""


@dataclass(frozen=True)
class CardAsset:
    """A sports card asset mapped to the shared Portfolio Asset model."""

    asset_id: str
    player: str
    sport: str
    year: str
    brand: str
    set: str
    card_number: str
    grader: str
    grade: str
    parallel: str
    serial_number: str
    currency: str

    def __post_init__(self) -> None:
        self._validate_grade()

    def display_name(self) -> str:
        """Return a human-readable card name."""

        parts = [
            self.year,
            self.brand,
            self.set,
            f"#{self.card_number}",
        ]
        if self.parallel:
            parts.append(self.parallel)
        if self.serial_number:
            parts.append(self.serial_number)
        return " ".join(part for part in parts if part)

    def to_asset(self) -> Asset:
        """Return the shared Portfolio Asset representation."""

        return Asset(
            asset_id=self.asset_id,
            symbol=self.asset_id,
            asset_type="SPORTS_CARD",
            name=f"{self.player} {self.display_name()}",
            currency=self.currency,
        )

    def _validate_grade(self) -> None:
        try:
            numeric_grade = Decimal(str(self.grade))
        except (InvalidOperation, ValueError) as exc:
            raise CardError(f"Invalid grade: {self.grade}") from exc

        if not numeric_grade.is_finite():
            raise CardError(f"Invalid grade: {self.grade}")
        if numeric_grade < Decimal("1") or numeric_grade > Decimal("10"):
            raise CardError(f"Invalid grade: {self.grade}")


@dataclass(frozen=True)
class CardPosition:
    """A held sports card position."""

    asset: CardAsset
    quantity: Decimal
    purchase_price: Decimal
    purchase_date: str
    notes: str

    def total_purchase_cost(self) -> Decimal:
        """Return total purchase cost."""

        return self.quantity * self.purchase_price
