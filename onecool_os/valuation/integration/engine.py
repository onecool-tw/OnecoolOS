"""Fair Value to ValuationRecord integration engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from onecool_os.fair_value.enums import FairValueConfidence
from onecool_os.fair_value.models import OnecoolFairValueSnapshot
from onecool_os.valuation.enums import ValuationConfidence
from onecool_os.valuation.enums import ValuationSource
from onecool_os.valuation.integration.models import FairValueValuationIntegrationResult
from onecool_os.valuation.integration.models import FairValueValuationMapping
from onecool_os.valuation.integration.models import RuntimeValuationPlaceholder
from onecool_os.valuation.integration.models import RuntimeValuationStatus
from onecool_os.valuation.integration.validation import ValuationIntegrationError
from onecool_os.valuation.integration.validation import ensure_unique
from onecool_os.valuation.integration.validation import require_currency
from onecool_os.valuation.integration.validation import require_market_value
from onecool_os.valuation.integration.validation import require_snapshot_asset
from onecool_os.valuation.models import ValuationRecord


class FairValueValuationEngine:
    """Create canonical runtime ValuationRecords from Onecool Fair Value."""

    valuation_source = ValuationSource.ONECOOL_FAIR_VALUE

    def build(
        self,
        fair_value_snapshots: list[OnecoolFairValueSnapshot] | tuple[OnecoolFairValueSnapshot, ...],
    ) -> FairValueValuationIntegrationResult:
        """Build trusted ValuationRecords and placeholders from snapshots."""

        snapshots = tuple(fair_value_snapshots)
        _validate_duplicate_snapshots(snapshots)
        mappings: list[FairValueValuationMapping] = []
        placeholders: list[RuntimeValuationPlaceholder] = []
        warnings: list[str] = []
        valuation_ids: list[str] = []
        for snapshot in snapshots:
            try:
                if snapshot.confidence == FairValueConfidence.INSUFFICIENT_DATA:
                    placeholders.append(_placeholder(snapshot))
                    continue
                mapping = self.map_snapshot(snapshot)
                mappings.append(mapping)
                valuation_ids.append(mapping.valuation_record.valuation_id)
            except ValuationIntegrationError as exc:
                warnings.append(f"{snapshot.asset_id}: {exc}")
                placeholders.append(_placeholder(snapshot, status=RuntimeValuationStatus.REJECTED, warning=str(exc)))
        ensure_unique(valuation_ids, "duplicate valuation record")
        return FairValueValuationIntegrationResult(
            valuation_records=tuple(mapping.valuation_record for mapping in mappings),
            mappings=tuple(mappings),
            placeholders=tuple(placeholders),
            warnings=tuple(warnings),
        )

    def map_snapshot(
        self,
        snapshot: OnecoolFairValueSnapshot,
    ) -> FairValueValuationMapping:
        """Map a trusted Fair Value snapshot into a ValuationRecord."""

        asset_id = require_snapshot_asset(snapshot)
        market_value = require_market_value(snapshot)
        currency = require_currency(snapshot)
        confidence = _valuation_confidence(snapshot)
        valuation_record_id = _valuation_record_id(snapshot)
        record = ValuationRecord(
            valuation_id=valuation_record_id,
            asset_id=asset_id,
            asset_type="SPORTS_CARD",
            source=self.valuation_source,
            currency=currency,
            valuation_date=snapshot.reference_datetime.date(),
            confidence=confidence,
            market_value=market_value,
            effective_date=(
                snapshot.latest_sold_date.isoformat()
                if snapshot.latest_sold_date
                else None
            ),
            note=_note(snapshot),
            tags=["onecool-fair-value", "runtime"],
        )
        return FairValueValuationMapping(
            valuation_record=record,
            valuation_record_id=valuation_record_id,
            asset_id=asset_id,
            cert_number=snapshot.cert_number,
            valuation_source=self.valuation_source,
            market_value=market_value,
            currency=currency,
            confidence=confidence.value,
            evidence_quality_score=snapshot.eqs,
            latest_sold_date=snapshot.latest_sold_date,
            sample_count=snapshot.sample_count,
            freshness_status=snapshot.freshness.value,
            liquidity=snapshot.liquidity.value,
            warnings=snapshot.warnings,
            reference_datetime=snapshot.reference_datetime,
            generated_at=snapshot.generated_at,
        )

    def build_from_runtime_session(self, runtime_session: Any) -> FairValueValuationIntegrationResult:
        """Build valuation records from RuntimeSession Fair Value snapshots."""

        return self.build(runtime_session.build_fair_value())


def _validate_duplicate_snapshots(
    snapshots: tuple[OnecoolFairValueSnapshot, ...],
) -> None:
    keys = [
        f"{snapshot.asset_id}:{ValuationSource.ONECOOL_FAIR_VALUE.value}"
        for snapshot in snapshots
    ]
    ensure_unique(keys, "duplicate valuation source")


def _valuation_confidence(snapshot: OnecoolFairValueSnapshot) -> ValuationConfidence:
    if snapshot.confidence == FairValueConfidence.HIGH:
        return ValuationConfidence.HIGH
    if snapshot.confidence == FairValueConfidence.MEDIUM:
        return ValuationConfidence.MEDIUM
    if snapshot.confidence == FairValueConfidence.LOW:
        return ValuationConfidence.LOW
    raise ValuationIntegrationError("invalid confidence")


def _valuation_record_id(snapshot: OnecoolFairValueSnapshot) -> str:
    timestamp = snapshot.reference_datetime.strftime("%Y%m%dT%H%M%S%z")
    return f"onecool-fair-value:{snapshot.asset_id}:{timestamp}"


def _note(snapshot: OnecoolFairValueSnapshot) -> str:
    return (
        "Onecool Fair Value from verified eBay Sold evidence; "
        f"EQS={snapshot.eqs}; sample_count={snapshot.sample_count}; "
        f"freshness={snapshot.freshness.value}; liquidity={snapshot.liquidity.value}"
    )


def _placeholder(
    snapshot: OnecoolFairValueSnapshot,
    *,
    status: RuntimeValuationStatus = RuntimeValuationStatus.INSUFFICIENT_DATA,
    warning: str | None = None,
) -> RuntimeValuationPlaceholder:
    warnings = tuple(dict.fromkeys((*snapshot.warnings, *( (warning,) if warning else () ))))
    return RuntimeValuationPlaceholder(
        asset_id=str(getattr(snapshot, "asset_id", "") or "UNKNOWN"),
        cert_number=snapshot.cert_number,
        valuation_source=ValuationSource.ONECOOL_FAIR_VALUE,
        status=status,
        warnings=warnings or ("Insufficient Fair Value Data",),
        reference_datetime=snapshot.reference_datetime,
        generated_at=snapshot.generated_at,
    )
