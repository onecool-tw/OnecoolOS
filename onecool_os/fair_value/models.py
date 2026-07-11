"""Models for Onecool Fair Value snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any

from onecool_os.fair_value.enums import FairValueConfidence
from onecool_os.fair_value.enums import FairValueFreshness
from onecool_os.fair_value.enums import FairValueLiquidity
from onecool_os.fair_value.validation import optional_text
from onecool_os.fair_value.validation import parse_datetime
from onecool_os.fair_value.validation import parse_decimal
from onecool_os.fair_value.validation import parse_enum
from onecool_os.fair_value.validation import require_text

MONEY_QUANT = Decimal("0.01")
SCORE_QUANT = Decimal("0.01")


@dataclass(frozen=True)
class ComparableStatistics:
    """Statistics for the selected verified comparable set."""

    minimum: Decimal | str | int | None
    maximum: Decimal | str | int | None
    median: Decimal | str | int | None
    average: Decimal | str | int | None
    trimmed_mean: Decimal | str | int | None
    standard_deviation: Decimal | str | int | None
    sample_count: int
    latest_sold_date: date | None = None
    oldest_included_date: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "minimum", parse_decimal(self.minimum, "minimum"))
        object.__setattr__(self, "maximum", parse_decimal(self.maximum, "maximum"))
        object.__setattr__(self, "median", parse_decimal(self.median, "median"))
        object.__setattr__(self, "average", parse_decimal(self.average, "average"))
        object.__setattr__(self, "trimmed_mean", parse_decimal(self.trimmed_mean, "trimmed_mean"))
        object.__setattr__(
            self,
            "standard_deviation",
            parse_decimal(self.standard_deviation, "standard_deviation"),
        )
        object.__setattr__(self, "sample_count", int(self.sample_count))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "minimum": _decimal_text(self.minimum),
            "maximum": _decimal_text(self.maximum),
            "median": _decimal_text(self.median),
            "average": _decimal_text(self.average),
            "trimmed_mean": _decimal_text(self.trimmed_mean),
            "standard_deviation": _decimal_text(self.standard_deviation),
            "sample_count": self.sample_count,
            "latest_sold_date": self.latest_sold_date.isoformat() if self.latest_sold_date else None,
            "oldest_included_date": (
                self.oldest_included_date.isoformat()
                if self.oldest_included_date
                else None
            ),
        }


@dataclass(frozen=True)
class EvidenceQualityScore:
    """Evidence quality score with component breakdown."""

    score: Decimal | str | int
    breakdown: dict[str, Decimal | str | int]
    warnings: tuple[str, ...] | list[str] = ()

    def __post_init__(self) -> None:
        score = parse_decimal(self.score, "score")
        breakdown = {
            str(key): parse_decimal(value, str(key)) or Decimal("0")
            for key, value in dict(self.breakdown).items()
        }
        object.__setattr__(self, "score", score or Decimal("0"))
        object.__setattr__(self, "breakdown", breakdown)
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "score": _decimal_text(self.score),
            "breakdown": {
                key: _decimal_text(value)
                for key, value in self.breakdown.items()
            },
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class OnecoolFairValueSnapshot:
    """Auditable Onecool Fair Value snapshot for one collectible asset."""

    asset_id: str
    fair_value: Decimal | str | int | None
    currency: str | None
    median: Decimal | str | int | None
    average: Decimal | str | int | None
    trimmed_mean: Decimal | str | int | None
    standard_deviation: Decimal | str | int | None
    sample_count: int
    liquidity: FairValueLiquidity | str
    freshness: FairValueFreshness | str
    confidence: FairValueConfidence | str
    eqs: Decimal | str | int
    eqs_breakdown: dict[str, Decimal | str | int]
    warnings: tuple[str, ...] | list[str]
    generated_at: datetime | str
    reference_datetime: datetime | str
    minimum: Decimal | str | int | None = None
    maximum: Decimal | str | int | None = None
    latest_sold_date: date | None = None
    oldest_included_date: date | None = None
    cert_number: str | None = None
    evidence_ids: tuple[str, ...] | list[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_id", require_text(self.asset_id, "asset_id"))
        object.__setattr__(self, "cert_number", optional_text(self.cert_number))
        object.__setattr__(self, "fair_value", parse_decimal(self.fair_value, "fair_value"))
        object.__setattr__(self, "minimum", parse_decimal(self.minimum, "minimum"))
        object.__setattr__(self, "maximum", parse_decimal(self.maximum, "maximum"))
        object.__setattr__(self, "median", parse_decimal(self.median, "median"))
        object.__setattr__(self, "average", parse_decimal(self.average, "average"))
        object.__setattr__(self, "trimmed_mean", parse_decimal(self.trimmed_mean, "trimmed_mean"))
        object.__setattr__(
            self,
            "standard_deviation",
            parse_decimal(self.standard_deviation, "standard_deviation"),
        )
        object.__setattr__(self, "sample_count", int(self.sample_count))
        object.__setattr__(
            self,
            "liquidity",
            parse_enum(FairValueLiquidity, self.liquidity, "liquidity"),
        )
        object.__setattr__(
            self,
            "freshness",
            parse_enum(FairValueFreshness, self.freshness, "freshness"),
        )
        object.__setattr__(
            self,
            "confidence",
            parse_enum(FairValueConfidence, self.confidence, "confidence"),
        )
        object.__setattr__(self, "eqs", parse_decimal(self.eqs, "eqs") or Decimal("0"))
        object.__setattr__(
            self,
            "eqs_breakdown",
            {
                str(key): parse_decimal(value, str(key)) or Decimal("0")
                for key, value in dict(self.eqs_breakdown).items()
            },
        )
        object.__setattr__(self, "warnings", tuple(dict.fromkeys(str(item) for item in self.warnings)))
        object.__setattr__(self, "generated_at", parse_datetime(self.generated_at, "generated_at"))
        object.__setattr__(
            self,
            "reference_datetime",
            parse_datetime(self.reference_datetime, "reference_datetime"),
        )
        object.__setattr__(self, "evidence_ids", tuple(str(item) for item in self.evidence_ids))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "asset_id": self.asset_id,
            "cert_number": self.cert_number,
            "fair_value": _decimal_text(self.fair_value),
            "currency": self.currency,
            "minimum": _decimal_text(self.minimum),
            "maximum": _decimal_text(self.maximum),
            "median": _decimal_text(self.median),
            "average": _decimal_text(self.average),
            "trimmed_mean": _decimal_text(self.trimmed_mean),
            "standard_deviation": _decimal_text(self.standard_deviation),
            "sample_count": self.sample_count,
            "latest_sold_date": self.latest_sold_date.isoformat() if self.latest_sold_date else None,
            "oldest_included_date": (
                self.oldest_included_date.isoformat()
                if self.oldest_included_date
                else None
            ),
            "liquidity": self.liquidity.value,
            "freshness": self.freshness.value,
            "confidence": self.confidence.value,
            "eqs": _decimal_text(self.eqs),
            "eqs_breakdown": {
                key: _decimal_text(value)
                for key, value in self.eqs_breakdown.items()
            },
            "warnings": list(self.warnings),
            "evidence_ids": list(self.evidence_ids),
            "generated_at": self.generated_at.isoformat(),
            "reference_datetime": self.reference_datetime.isoformat(),
        }


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value.normalize())
