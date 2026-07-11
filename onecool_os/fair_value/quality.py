"""Evidence quality scoring for Onecool Fair Value."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from decimal import Decimal
from typing import Any

from onecool_os.fair_value.enums import FairValueFreshness
from onecool_os.fair_value.enums import FairValueLiquidity
from onecool_os.fair_value.models import EvidenceQualityScore


def calculate_liquidity(
    comparables: list[Any] | tuple[Any, ...],
    *,
    reference_datetime: datetime | None = None,
) -> tuple[FairValueLiquidity, dict[str, int]]:
    """Return liquidity and sold counts for 30, 90, and 180 days."""

    reference = reference_datetime or datetime.now(UTC)
    counts = {
        "sold_count_30_days": _count_since(comparables, reference, 30),
        "sold_count_90_days": _count_since(comparables, reference, 90),
        "sold_count_180_days": _count_since(comparables, reference, 180),
    }
    if counts["sold_count_30_days"] >= 5:
        return FairValueLiquidity.HIGH, counts
    if counts["sold_count_90_days"] >= 3:
        return FairValueLiquidity.MEDIUM, counts
    if counts["sold_count_180_days"] >= 1:
        return FairValueLiquidity.LOW, counts
    return FairValueLiquidity.ILLIQUID, counts


def calculate_freshness(
    comparables: list[Any] | tuple[Any, ...],
    *,
    reference_datetime: datetime | None = None,
) -> FairValueFreshness:
    """Return freshness from the latest included sold date."""

    records = tuple(comparables)
    if not records:
        return FairValueFreshness.UNKNOWN
    reference = reference_datetime or datetime.now(UTC)
    days_old = min((reference.date() - item.sold_date).days for item in records)
    if days_old <= 30:
        return FairValueFreshness.CURRENT
    if days_old <= 90:
        return FairValueFreshness.AGING
    return FairValueFreshness.STALE


def calculate_evidence_quality_score(
    comparables: list[Any] | tuple[Any, ...],
    *,
    liquidity: FairValueLiquidity,
    freshness: FairValueFreshness,
) -> EvidenceQualityScore:
    """Calculate deterministic 0-100 Evidence Quality Score."""

    records = tuple(comparables)
    sample_size = _sample_size_component(len(records))
    identity_match = Decimal("25") if records else Decimal("0")
    freshness_score = _freshness_component(freshness)
    liquidity_score = _liquidity_component(liquidity)
    completeness = _completeness_component(records)
    breakdown = {
        "sample_size": sample_size,
        "identity_match": identity_match,
        "freshness": freshness_score,
        "liquidity": liquidity_score,
        "evidence_completeness": completeness,
    }
    score = min(sum(breakdown.values(), Decimal("0")), Decimal("100"))
    return EvidenceQualityScore(
        score=score,
        breakdown=breakdown,
        warnings=_quality_warnings(records, liquidity, freshness),
    )


def _count_since(
    comparables: list[Any] | tuple[Any, ...],
    reference: datetime,
    days: int,
) -> int:
    return sum(
        1
        for item in comparables
        if 0 <= (reference.date() - item.sold_date).days <= days
    )


def _sample_size_component(sample_count: int) -> Decimal:
    if sample_count >= 5:
        return Decimal("30")
    if sample_count >= 3:
        return Decimal("20")
    if sample_count >= 1:
        return Decimal("10")
    return Decimal("0")


def _freshness_component(freshness: FairValueFreshness) -> Decimal:
    if freshness == FairValueFreshness.CURRENT:
        return Decimal("20")
    if freshness == FairValueFreshness.AGING:
        return Decimal("12")
    if freshness == FairValueFreshness.STALE:
        return Decimal("5")
    return Decimal("0")


def _liquidity_component(liquidity: FairValueLiquidity) -> Decimal:
    if liquidity == FairValueLiquidity.HIGH:
        return Decimal("15")
    if liquidity == FairValueLiquidity.MEDIUM:
        return Decimal("10")
    if liquidity == FairValueLiquidity.LOW:
        return Decimal("5")
    return Decimal("0")


def _completeness_component(records: tuple[Any, ...]) -> Decimal:
    if not records:
        return Decimal("0")
    complete = sum(
        1
        for item in records
        if getattr(item, "sold_item_url", None)
        and getattr(item, "ebay_item_id", None)
        and getattr(item, "sold_price", None) is not None
        and getattr(item, "sold_date", None) is not None
        and getattr(item, "currency", None)
        and getattr(item, "title", None)
    )
    if complete == len(records):
        return Decimal("10")
    if complete:
        return Decimal("5")
    return Decimal("0")


def _quality_warnings(
    records: tuple[Any, ...],
    liquidity: FairValueLiquidity,
    freshness: FairValueFreshness,
) -> tuple[str, ...]:
    warnings: list[str] = []
    if not records:
        warnings.append("No Verified Sold Comps")
    elif len(records) < 5:
        warnings.append("Low Comparable Sample Size")
    if liquidity in {FairValueLiquidity.LOW, FairValueLiquidity.ILLIQUID}:
        warnings.append("Low Liquidity")
    if freshness in {FairValueFreshness.STALE, FairValueFreshness.UNKNOWN}:
        warnings.append("Stale Or Missing Sold Evidence")
    return tuple(warnings)
