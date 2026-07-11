"""Comparable selection and Decimal-only statistics."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from decimal import Decimal
from decimal import localcontext
from typing import Any

from onecool_os.fair_value.models import ComparableStatistics
from onecool_os.valuation.evidence import EvidenceStatus

STD_DEV_QUANT = Decimal("0.0001")


def select_verified_comparables(
    evidence_records: list[Any] | tuple[Any, ...],
    *,
    asset_id: str | None = None,
    reference_datetime: datetime | None = None,
    sample_size: int = 10,
    window_days: int = 180,
) -> tuple[Any, ...]:
    """Return latest unique verified comps inside the sample window."""

    reference = reference_datetime or datetime.now(UTC)
    reference_date = reference.date()
    verified = []
    for evidence in evidence_records:
        if asset_id and getattr(evidence, "asset_id", None) != asset_id:
            continue
        if not _is_eligible_verified_evidence(evidence):
            continue
        days_old = (reference_date - evidence.sold_date).days
        if days_old < 0 or days_old > window_days:
            continue
        verified.append(evidence)

    ordered = sorted(
        verified,
        key=lambda item: (
            item.sold_date,
            str(getattr(item, "ebay_item_id", "") or ""),
            str(getattr(item, "evidence_id", "") or ""),
        ),
        reverse=True,
    )
    unique = []
    seen_keys: set[str] = set()
    for evidence in ordered:
        key = str(getattr(evidence, "ebay_item_id", "") or getattr(evidence, "sold_item_url", ""))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique.append(evidence)
    return tuple(unique[:sample_size])


def calculate_statistics(comparables: list[Any] | tuple[Any, ...]) -> ComparableStatistics:
    """Calculate Decimal-only comparable statistics."""

    records = tuple(comparables)
    prices = sorted(_price(item) for item in records)
    if not prices:
        return ComparableStatistics(
            minimum=None,
            maximum=None,
            median=None,
            average=None,
            trimmed_mean=None,
            standard_deviation=None,
            sample_count=0,
            latest_sold_date=None,
            oldest_included_date=None,
        )

    latest = max(item.sold_date for item in records)
    oldest = min(item.sold_date for item in records)
    return ComparableStatistics(
        minimum=prices[0],
        maximum=prices[-1],
        median=_median(prices),
        average=_mean(prices),
        trimmed_mean=_trimmed_mean(prices),
        standard_deviation=_standard_deviation(prices),
        sample_count=len(prices),
        latest_sold_date=latest,
        oldest_included_date=oldest,
    )


def _is_eligible_verified_evidence(evidence: Any) -> bool:
    status = getattr(evidence, "status", None)
    if status != EvidenceStatus.VERIFIED:
        return False
    if getattr(evidence, "sold_price", None) is None:
        return False
    if getattr(evidence, "sold_date", None) is None:
        return False
    if not getattr(evidence, "ebay_item_id", None):
        return False
    if not getattr(evidence, "exact_match", False):
        return False
    if tuple(getattr(evidence, "mismatched_fields", ())):
        return False
    return True


def _price(evidence: Any) -> Decimal:
    return Decimal(str(evidence.sold_price))


def _median(values: list[Decimal]) -> Decimal:
    midpoint = len(values) // 2
    if len(values) % 2:
        return values[midpoint]
    return (values[midpoint - 1] + values[midpoint]) / Decimal("2")


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal("0")) / Decimal(str(len(values)))


def _trimmed_mean(values: list[Decimal]) -> Decimal:
    if len(values) >= 5:
        return _mean(values[1:-1])
    return _mean(values)


def _standard_deviation(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    mean = _mean(values)
    variance = sum((value - mean) ** 2 for value in values) / Decimal(str(len(values)))
    with localcontext() as context:
        context.prec = 28
        return variance.sqrt().quantize(STD_DEV_QUANT)
