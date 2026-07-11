"""Deterministic Onecool Fair Value engine."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import Any

from onecool_os.fair_value.enums import FairValueConfidence
from onecool_os.fair_value.enums import FairValueFreshness
from onecool_os.fair_value.enums import FairValueLiquidity
from onecool_os.fair_value.models import OnecoolFairValueSnapshot
from onecool_os.fair_value.quality import calculate_evidence_quality_score
from onecool_os.fair_value.quality import calculate_freshness
from onecool_os.fair_value.quality import calculate_liquidity
from onecool_os.fair_value.statistics import calculate_statistics
from onecool_os.fair_value.statistics import select_verified_comparables


class OnecoolFairValueEngine:
    """Build auditable fair value snapshots from verified eBay Sold evidence."""

    def build_from_evidence(
        self,
        evidence_records: list[Any] | tuple[Any, ...],
        *,
        asset_id: str,
        cert_number: str | None = None,
        reference_datetime: datetime | None = None,
        generated_at: datetime | None = None,
        sample_size: int = 10,
        window_days: int = 180,
    ) -> OnecoolFairValueSnapshot:
        """Build one fair value snapshot for an asset."""

        reference = reference_datetime or datetime.now(UTC)
        generated = generated_at or reference
        comparables = select_verified_comparables(
            tuple(evidence_records),
            asset_id=asset_id,
            reference_datetime=reference,
            sample_size=sample_size,
            window_days=window_days,
        )
        statistics = calculate_statistics(comparables)
        liquidity, sold_counts = calculate_liquidity(
            comparables,
            reference_datetime=reference,
        )
        freshness = calculate_freshness(
            comparables,
            reference_datetime=reference,
        )
        eqs = calculate_evidence_quality_score(
            comparables,
            liquidity=liquidity,
            freshness=freshness,
        )
        warnings = tuple(dict.fromkeys((*eqs.warnings, *_currency_warnings(comparables))))
        if statistics.sample_count == 0:
            warnings = tuple(dict.fromkeys((*warnings, "Insufficient Verified Evidence")))
        return OnecoolFairValueSnapshot(
            asset_id=asset_id,
            cert_number=cert_number,
            fair_value=statistics.median,
            currency=_currency(comparables),
            minimum=statistics.minimum,
            maximum=statistics.maximum,
            median=statistics.median,
            average=statistics.average,
            trimmed_mean=statistics.trimmed_mean,
            standard_deviation=statistics.standard_deviation,
            sample_count=statistics.sample_count,
            latest_sold_date=statistics.latest_sold_date,
            oldest_included_date=statistics.oldest_included_date,
            liquidity=liquidity,
            freshness=freshness,
            confidence=_confidence(statistics.sample_count),
            eqs=eqs.score,
            eqs_breakdown={**eqs.breakdown, **sold_counts},
            warnings=warnings,
            evidence_ids=tuple(getattr(item, "evidence_id", "") for item in comparables),
            generated_at=generated,
            reference_datetime=reference,
        )

    def build_from_runtime_session(
        self,
        runtime_session: Any,
        *,
        reference_datetime: datetime | None = None,
        generated_at: datetime | None = None,
        sample_size: int = 10,
        window_days: int = 180,
    ) -> tuple[OnecoolFairValueSnapshot, ...]:
        """Build fair value snapshots from RuntimeSession without mutation."""

        reference = reference_datetime or runtime_session.generated_at
        generated = generated_at or reference
        evidence = tuple(
            item
            for batch in runtime_session.ebay_sold_evidence_batches
            for item in batch.evidence
        )
        assets = tuple(getattr(runtime_session, "enriched_runtime_assets", ()))
        asset_ids = _asset_ids_from_runtime(assets, evidence)
        return tuple(
            self.build_from_evidence(
                evidence,
                asset_id=asset_id,
                cert_number=_cert_number_for_asset(assets, asset_id),
                reference_datetime=reference,
                generated_at=generated,
                sample_size=sample_size,
                window_days=window_days,
            )
            for asset_id in asset_ids
        )


def _confidence(sample_count: int) -> FairValueConfidence:
    if sample_count >= 5:
        return FairValueConfidence.HIGH
    if sample_count >= 3:
        return FairValueConfidence.MEDIUM
    if sample_count >= 1:
        return FairValueConfidence.LOW
    return FairValueConfidence.INSUFFICIENT_DATA


def _currency(comparables: tuple[Any, ...]) -> str | None:
    currencies = sorted({str(item.currency) for item in comparables if getattr(item, "currency", None)})
    if len(currencies) == 1:
        return currencies[0]
    return None


def _currency_warnings(comparables: tuple[Any, ...]) -> tuple[str, ...]:
    currencies = {str(item.currency) for item in comparables if getattr(item, "currency", None)}
    if len(currencies) > 1:
        return ("Multiple Evidence Currencies",)
    return ()


def _asset_ids_from_runtime(
    assets: tuple[dict[str, Any], ...],
    evidence: tuple[Any, ...],
) -> tuple[str, ...]:
    asset_ids = [
        str(asset.get("asset_id") or "")
        for asset in assets
        if asset.get("asset_id")
    ]
    asset_ids.extend(
        str(item.asset_id)
        for item in evidence
        if getattr(item, "asset_id", None)
    )
    return tuple(dict.fromkeys(sorted(asset_ids)))


def _cert_number_for_asset(
    assets: tuple[dict[str, Any], ...],
    asset_id: str,
) -> str | None:
    for asset in assets:
        if str(asset.get("asset_id") or "") == asset_id:
            cert = asset.get("cert_number") or asset.get("cert")
            return str(cert) if cert else None
    return None


FairValueEngine = OnecoolFairValueEngine
