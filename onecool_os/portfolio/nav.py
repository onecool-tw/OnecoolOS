"""Deterministic Portfolio NAV Engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation
from typing import Any

from onecool_os.portfolio.enums import PortfolioNavStatus
from onecool_os.portfolio.enums import ValuationCoverageStatus
from onecool_os.portfolio.models import AssetNavLine
from onecool_os.portfolio.models import PortfolioNavSnapshot
from onecool_os.valuation.evidence import EbaySoldEvidenceBatch
from onecool_os.valuation.evidence import EvidenceStatus
from onecool_os.valuation.enums import ValuationSource
from onecool_os.valuation.models import ValuationRecord

MONEY_QUANT = Decimal("0.01")
PERCENT_QUANT = Decimal("0.0001")


@dataclass(frozen=True)
class _Candidate:
    valuation: ValuationRecord
    value: Decimal
    coverage_status: ValuationCoverageStatus
    evidence_status: str


class PortfolioNavEngine:
    """Calculate NAV snapshots from runtime assets and valuation records."""

    def build_snapshots(
        self,
        runtime_assets: list[dict[str, Any]] | tuple[dict[str, Any], ...],
        valuation_records: list[ValuationRecord] | tuple[ValuationRecord, ...] = (),
        *,
        evidence_batches: list[EbaySoldEvidenceBatch]
        | tuple[EbaySoldEvidenceBatch, ...] = (),
        reference_datetime: datetime | None = None,
        generated_at: datetime | None = None,
    ) -> tuple[PortfolioNavSnapshot, ...]:
        """Build one NAV snapshot per deterministic aggregation currency."""

        reference = reference_datetime or datetime.now(UTC)
        generated = generated_at or reference
        assets = tuple(dict(asset) for asset in runtime_assets)
        valuations = tuple(
            valuation
            for valuation in valuation_records
            if isinstance(valuation, ValuationRecord)
        )
        evidence_by_id = _evidence_status_by_valuation_id(evidence_batches)
        currencies = _snapshot_currencies(assets, valuations)
        if not currencies:
            currencies = ("USD",)
        return tuple(
            self._build_snapshot(
                assets,
                valuations,
                evidence_by_id,
                currency=currency,
                reference_datetime=reference,
                generated_at=generated,
            )
            for currency in currencies
        )

    def build_from_runtime_session(
        self,
        runtime_session: Any,
        valuation_records: list[ValuationRecord] | tuple[ValuationRecord, ...] = (),
        *,
        reference_datetime: datetime | None = None,
        generated_at: datetime | None = None,
    ) -> tuple[PortfolioNavSnapshot, ...]:
        """Build NAV snapshots from RuntimeSession without mutating it."""

        return self.build_snapshots(
            tuple(runtime_session.enriched_runtime_assets),
            tuple(valuation_records),
            evidence_batches=tuple(runtime_session.ebay_sold_evidence_batches),
            reference_datetime=reference_datetime or runtime_session.generated_at,
            generated_at=generated_at or runtime_session.generated_at,
        )

    def _build_snapshot(
        self,
        assets: tuple[dict[str, Any], ...],
        valuation_records: tuple[ValuationRecord, ...],
        evidence_by_id: dict[str, EvidenceStatus],
        *,
        currency: str,
        reference_datetime: datetime,
        generated_at: datetime,
    ) -> PortfolioNavSnapshot:
        asset_lines = tuple(
            _build_line(
                asset,
                valuation_records,
                evidence_by_id,
                currency=currency,
            )
            for asset in sorted(assets, key=lambda item: str(item.get("asset_id") or ""))
            if _asset_belongs_to_currency(item=asset, currency=currency)
        )
        total_assets = len(asset_lines)
        assets_with_cost = sum(1 for line in asset_lines if line.cost_basis is not None)
        assets_with_market_value = sum(1 for line in asset_lines if line.market_value is not None)
        verified_assets = sum(
            1 for line in asset_lines if line.coverage_status == ValuationCoverageStatus.VERIFIED
        )
        review_required_assets = sum(
            1 for line in asset_lines if line.coverage_status == ValuationCoverageStatus.REVIEW_REQUIRED
        )
        estimated_assets = sum(
            1 for line in asset_lines if line.coverage_status == ValuationCoverageStatus.ESTIMATED
        )
        missing_value_assets = sum(
            1 for line in asset_lines if line.coverage_status == ValuationCoverageStatus.MISSING
        )
        total_cost_basis = _money(
            sum(
                (
                    line.cost_basis
                    for line in asset_lines
                    if line.cost_basis is not None and line.cost_basis > 0
                ),
                Decimal("0"),
            )
        )
        total_market_value = _money(
            sum(
                (
                    line.market_value
                    for line in asset_lines
                    if line.market_value is not None and line.market_currency == currency
                ),
                Decimal("0"),
            )
        )
        currency_mismatch = any("Currency Mismatch" in line.warnings for line in asset_lines)
        unrealized_gain_loss: Decimal | None = None
        roi_percent: Decimal | None = None
        if total_cost_basis > 0 and assets_with_market_value > 0 and not currency_mismatch:
            unrealized_gain_loss = _money(total_market_value - total_cost_basis)
            roi_percent = _percent((unrealized_gain_loss / total_cost_basis) * Decimal("100"))
        warnings = tuple(
            dict.fromkeys(
                warning
                for line in asset_lines
                for warning in line.warnings
            )
        )
        status = _snapshot_status(
            total_assets=total_assets,
            assets_with_cost=assets_with_cost,
            assets_with_market_value=assets_with_market_value,
            estimated_assets=estimated_assets,
            currency_mismatch=currency_mismatch,
            total_cost_basis=total_cost_basis,
        )
        return PortfolioNavSnapshot(
            snapshot_id=f"portfolio-nav:{currency}:{reference_datetime.isoformat()}",
            reference_datetime=reference_datetime,
            currency=currency,
            total_assets=total_assets,
            assets_with_cost=assets_with_cost,
            assets_with_market_value=assets_with_market_value,
            verified_assets=verified_assets,
            review_required_assets=review_required_assets,
            estimated_assets=estimated_assets,
            missing_value_assets=missing_value_assets,
            total_cost_basis=total_cost_basis,
            total_market_value=total_market_value,
            unrealized_gain_loss=unrealized_gain_loss,
            roi_percent=roi_percent,
            valuation_coverage_percent=_coverage_percent(assets_with_market_value, total_assets),
            verified_coverage_percent=_coverage_percent(verified_assets, total_assets),
            status=status,
            asset_lines=asset_lines,
            warnings=warnings,
            generated_at=generated_at,
        )


def _build_line(
    asset: dict[str, Any],
    valuation_records: tuple[ValuationRecord, ...],
    evidence_by_id: dict[str, EvidenceStatus],
    *,
    currency: str,
) -> AssetNavLine:
    asset_id = str(asset.get("asset_id") or "").strip()
    asset_name = _asset_name(asset)
    cost_basis = _decimal_or_none(asset.get("cost"))
    cost_currency = str(asset.get("currency") or currency).strip().upper()
    warnings: list[str] = []
    if cost_basis is None:
        warnings.append("Missing Cost Basis")
    elif cost_basis <= Decimal("0"):
        warnings.append("Zero or Negative Cost Basis")

    candidate, candidate_warnings = _select_candidate(
        asset_id,
        valuation_records,
        evidence_by_id,
    )
    warnings.extend(candidate_warnings)
    market_value = (
        candidate.value
        if candidate and candidate.coverage_status != ValuationCoverageStatus.REVIEW_REQUIRED
        else None
    )
    market_currency = candidate.valuation.currency if candidate else None
    valuation_source = candidate.valuation.source.value if candidate else None
    valuation_record_id = candidate.valuation.valuation_id if candidate else None
    valuation_date = candidate.valuation.valuation_date if candidate else None
    coverage_status = candidate.coverage_status if candidate else ValuationCoverageStatus.MISSING
    evidence_status = candidate.evidence_status if candidate else "MISSING"

    if market_value is None:
        warnings.append("Missing Market Value")
    if coverage_status == ValuationCoverageStatus.ESTIMATED:
        warnings.append("Supporting Estimate Only")
    if coverage_status == ValuationCoverageStatus.REVIEW_REQUIRED:
        warnings.append("Evidence Needs Review")

    unrealized_gain_loss: Decimal | None = None
    roi_percent: Decimal | None = None
    if (
        cost_basis is not None
        and cost_basis > 0
        and market_value is not None
        and market_currency == cost_currency
    ):
        unrealized_gain_loss = _money(market_value - cost_basis)
        roi_percent = _percent((unrealized_gain_loss / cost_basis) * Decimal("100"))
    elif market_value is not None and market_currency != cost_currency:
        warnings.append("Currency Mismatch")

    return AssetNavLine(
        asset_id=asset_id,
        cert_number=_optional_asset_text(asset, "cert_number"),
        asset_name=asset_name,
        cost_basis=cost_basis,
        cost_currency=cost_currency,
        market_value=market_value,
        market_currency=market_currency,
        unrealized_gain_loss=unrealized_gain_loss,
        roi_percent=roi_percent,
        valuation_source=valuation_source,
        valuation_record_id=valuation_record_id,
        evidence_status=evidence_status,
        coverage_status=coverage_status,
        valuation_date=valuation_date,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def _select_candidate(
    asset_id: str,
    valuation_records: tuple[ValuationRecord, ...],
    evidence_by_id: dict[str, EvidenceStatus],
) -> tuple[_Candidate | None, tuple[str, ...]]:
    warnings: list[str] = []
    candidates: list[_Candidate] = []
    for valuation in valuation_records:
        if valuation.asset_id != asset_id:
            continue
        candidate = _candidate_from_valuation(valuation, evidence_by_id)
        if candidate is None:
            if valuation.source == ValuationSource.EBAY_SOLD:
                warnings.append("Evidence Needs Review")
            continue
        candidates.append(candidate)
    if not candidates:
        return None, tuple(dict.fromkeys(warnings))
    candidates.sort(
        key=lambda item: (
            item.valuation.valuation_date,
            item.valuation.valuation_id,
        )
    )
    if len(candidates) > 1:
        warnings.append("Multiple Eligible Valuation Records")
    return candidates[-1], tuple(dict.fromkeys(warnings))


def _candidate_from_valuation(
    valuation: ValuationRecord,
    evidence_by_id: dict[str, EvidenceStatus],
) -> _Candidate | None:
    value = valuation.market_value if valuation.market_value is not None else valuation.estimated_value
    if value is None:
        return None
    if valuation.source == ValuationSource.ONECOOL_FAIR_VALUE and valuation.market_value is not None:
        return _Candidate(
            valuation=valuation,
            value=value,
            coverage_status=ValuationCoverageStatus.VERIFIED,
            evidence_status=ValuationCoverageStatus.VERIFIED.value,
        )
    if valuation.source == ValuationSource.EBAY_SOLD and valuation.market_value is not None:
        evidence_status = evidence_by_id.get(valuation.valuation_id)
        if evidence_status is None:
            return _Candidate(
                valuation=valuation,
                value=value,
                coverage_status=ValuationCoverageStatus.VERIFIED,
                evidence_status=ValuationCoverageStatus.VERIFIED.value,
            )
        if evidence_status == EvidenceStatus.VERIFIED:
            return _Candidate(
                valuation=valuation,
                value=value,
                coverage_status=ValuationCoverageStatus.VERIFIED,
                evidence_status=evidence_status.value,
            )
        if evidence_status == EvidenceStatus.NEEDS_REVIEW:
            return _Candidate(
                valuation=valuation,
                value=value,
                coverage_status=ValuationCoverageStatus.REVIEW_REQUIRED,
                evidence_status=evidence_status.value,
            )
        return None
    return _Candidate(
        valuation=valuation,
        value=value,
        coverage_status=ValuationCoverageStatus.ESTIMATED,
        evidence_status="ESTIMATED",
    )


def _snapshot_currencies(
    assets: tuple[dict[str, Any], ...],
    valuation_records: tuple[ValuationRecord, ...],
) -> tuple[str, ...]:
    currencies = {
        str(asset.get("currency") or "").strip().upper()
        for asset in assets
        if str(asset.get("currency") or "").strip()
    }
    return tuple(sorted(currency for currency in currencies if currency))


def _asset_belongs_to_currency(item: dict[str, Any], currency: str) -> bool:
    asset_currency = str(item.get("currency") or "").strip().upper()
    return asset_currency == currency


def _evidence_status_by_valuation_id(
    evidence_batches: list[EbaySoldEvidenceBatch] | tuple[EbaySoldEvidenceBatch, ...],
) -> dict[str, EvidenceStatus]:
    statuses: dict[str, EvidenceStatus] = {}
    for batch in evidence_batches:
        for evidence in batch.evidence:
            statuses[f"ebay-sold:{evidence.evidence_id}"] = evidence.status
    return statuses


def _snapshot_status(
    *,
    total_assets: int,
    assets_with_cost: int,
    assets_with_market_value: int,
    estimated_assets: int,
    currency_mismatch: bool,
    total_cost_basis: Decimal,
) -> PortfolioNavStatus:
    if currency_mismatch:
        return PortfolioNavStatus.CURRENCY_MISMATCH
    if total_assets == 0 or assets_with_market_value == 0 or assets_with_cost == 0 or total_cost_basis <= 0:
        return PortfolioNavStatus.INSUFFICIENT_DATA
    if assets_with_market_value == total_assets and estimated_assets == 0:
        return PortfolioNavStatus.COMPLETE
    return PortfolioNavStatus.PARTIAL


def _coverage_percent(numerator: int, denominator: int) -> Decimal:
    if denominator <= 0:
        return Decimal("0.0000")
    return _percent((Decimal(numerator) / Decimal(denominator)) * Decimal("100"))


def _asset_name(asset: dict[str, Any]) -> str:
    for field_name in ("asset_name", "card_name", "name", "title"):
        value = str(asset.get(field_name) or "").strip()
        if value:
            return value
    parts = [
        str(asset.get("year") or "").strip(),
        str(asset.get("brand") or asset.get("set") or "").strip(),
        str(asset.get("player") or "").strip(),
        str(asset.get("card_number") or "").strip(),
        str(asset.get("grade_company") or "").strip(),
        str(asset.get("grade") or "").strip(),
    ]
    name = " ".join(part for part in parts if part)
    return name or str(asset.get("asset_id") or "Unknown Asset")


def _optional_asset_text(asset: dict[str, Any], field_name: str) -> str | None:
    value = str(asset.get(field_name) or "").strip()
    return value or None


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not parsed.is_finite():
        return None
    return parsed


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT)


def _percent(value: Decimal) -> Decimal:
    return value.quantize(PERCENT_QUANT)
