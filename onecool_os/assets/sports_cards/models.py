"""Sports Cards asset models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from onecool_os.assets.base import BaseAsset, BasePosition
from onecool_os.portfolio.models import Asset, PortfolioError

SUPPORTED_CARD_STATUSES = frozenset(
    {"Owned", "Listed", "Sold", "Grading", "Shipping", "Reserved"}
)
SUPPORTED_INVENTORY_STATUSES = SUPPORTED_CARD_STATUSES
SUPPORTED_COLLECTION_TYPES = frozenset(
    {"Core", "Investment", "Trading", "PC"}
)
VALUATION_SOURCE_PRIORITY = (
    "eBay Sold",
    "Card Ladder",
    "PWCC",
    "Goldin",
    "Fanatics",
    "Manual",
)


class CardError(PortfolioError):
    """Raised for sports card model errors."""


@dataclass(frozen=True)
class CardAsset(BaseAsset):
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

    @property
    def grade_company(self) -> str:
        """Return the grading company using the live portfolio field name."""

        return self.grader

    @property
    def asset_type(self) -> str:
        """Return the normalized asset type."""

        return "SPORTS_CARD"

    @property
    def name(self) -> str:
        """Return the shared asset display name."""

        return f"{self.player} {self.display_name()}"

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
            asset_type=self.asset_type,
            name=self.name,
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
class CardPosition(BasePosition):
    """A held sports card position."""

    asset: CardAsset
    quantity: Decimal
    purchase_price: Decimal
    purchase_date: str
    notes: str
    account: str | None = None
    asset_class: str | None = None
    status: str | None = None
    base_currency: str | None = None
    cost: Decimal | None = None
    purchase_platform: str | None = None
    collection_type: str | None = None
    valuation_source: str | None = None
    inventory_id: str | None = None
    cert_number: str | None = None
    owned_quantity: Decimal | None = None
    available_quantity: Decimal | None = None
    listed_quantity: Decimal | None = None
    sold_quantity: Decimal | None = None
    location: str | None = None
    cabinet: str | None = None
    box: str | None = None
    row: str | None = None
    slot: str | None = None
    last_inventory_update: str | None = None

    def __post_init__(self) -> None:
        if self.status and self.status not in SUPPORTED_INVENTORY_STATUSES:
            raise CardError(f"Unsupported card status: {self.status}")
        if (
            self.collection_type
            and self.collection_type not in SUPPORTED_COLLECTION_TYPES
        ):
            raise CardError(
                f"Unsupported collection_type: {self.collection_type}"
            )
        if (
            self.valuation_source
            and self.valuation_source not in VALUATION_SOURCE_PRIORITY
        ):
            raise CardError(
                f"Unsupported valuation_source: {self.valuation_source}"
            )
        self._validate_inventory_quantities()

    def total_purchase_cost(self) -> Decimal:
        """Return total purchase cost."""

        return self.quantity * self.purchase_price

    def _validate_inventory_quantities(self) -> None:
        if self.owned_quantity is not None and self.owned_quantity <= 0:
            raise CardError("owned_quantity must be greater than 0.")

        tracked_quantities = {
            "available_quantity": self.available_quantity,
            "listed_quantity": self.listed_quantity,
            "sold_quantity": self.sold_quantity,
        }
        for field_name, value in tracked_quantities.items():
            if value is not None and value < 0:
                raise CardError(f"{field_name} must not be negative.")

        if self.owned_quantity is None:
            return

        total_allocated = sum(
            value or Decimal("0")
            for value in tracked_quantities.values()
        )
        if total_allocated > self.owned_quantity:
            raise CardError(
                "available, listed, and sold quantities exceed owned_quantity."
            )
