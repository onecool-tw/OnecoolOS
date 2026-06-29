"""Real Estate asset models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from onecool_os.portfolio.models import Asset, PortfolioError


class RealEstateError(PortfolioError):
    """Raised for real estate model errors."""


@dataclass(frozen=True)
class RealEstateAsset:
    """A real estate asset mapped to the shared Portfolio Asset model."""

    asset_id: str
    name: str
    country: str
    city: str
    district: str
    address_label: str
    property_type: str
    currency: str
    area_ping: Decimal
    building_age_years: Decimal
    floor: int
    total_floors: int
    has_parking: bool
    asset_type: str = "REAL_ESTATE"

    def __post_init__(self) -> None:
        if self.asset_type != "REAL_ESTATE":
            raise RealEstateError(
                f"Unsupported real estate asset_type: {self.asset_type}"
            )
        if self.area_ping <= Decimal("0"):
            raise RealEstateError(f"Invalid area_ping: {self.area_ping}")
        if self.building_age_years < Decimal("0"):
            raise RealEstateError(
                f"Invalid building_age_years: {self.building_age_years}"
            )
        if self.floor <= 0:
            raise RealEstateError(f"Invalid floor: {self.floor}")
        if self.total_floors <= 0 or self.floor > self.total_floors:
            raise RealEstateError(f"Invalid total_floors: {self.total_floors}")

    def location_label(self) -> str:
        """Return city and district for display."""

        return f"{self.city} / {self.district}"

    def to_asset(self) -> Asset:
        """Return the shared Portfolio Asset representation."""

        return Asset(
            asset_id=self.asset_id,
            symbol=self.asset_id,
            asset_type=self.asset_type,
            name=self.name,
            currency=self.currency,
        )


@dataclass(frozen=True)
class RealEstatePosition:
    """A held real estate position."""

    asset: RealEstateAsset
    quantity: Decimal
    purchase_price: Decimal
    purchase_date: str
    current_estimated_value: Decimal | None = None
    notes: str = ""

    def unrealized_pnl(self) -> Decimal | None:
        """Return simple unrealized PnL from provided estimated value."""

        if self.current_estimated_value is None:
            return None
        return self.current_estimated_value - self.purchase_price
