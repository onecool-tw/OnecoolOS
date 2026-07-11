"""Deterministic eBay Sold URL research request export."""

from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from onecool_os.research.enums import ResearchCapability
from onecool_os.research.queue import ResearchQueueEngine
from onecool_os.research.queue import ResearchQueueStatus
from onecool_os.research.workbench.models import EbayUrlResearchRequest
from onecool_os.research.workbench.models import EbayUrlResearchRequestExport
from onecool_os.research.workbench.models import REQUIRED_EBAY_SOLD_REQUEST_FIELDS


class ResearchRequestExporter:
    """Export READY queue items as provider-independent request packages."""

    def export(
        self,
        runtime_session: Any,
        *,
        queue_snapshot: Any | None = None,
        limit: int | None = None,
        asset_id: str | None = None,
        cert_number: str | None = None,
        reference_datetime: datetime | None = None,
        generated_at: datetime | None = None,
    ) -> EbayUrlResearchRequestExport:
        """Return a deterministic request export without calling providers."""

        reference = reference_datetime or getattr(runtime_session, "generated_at", None) or datetime.now(UTC)
        generated = generated_at or reference
        snapshot = queue_snapshot or ResearchQueueEngine().build(
            runtime_session,
            reference_datetime=reference,
            generated_at=generated,
        )
        assets = _assets_by_id(runtime_session)
        seen_keys: set[tuple[str, str]] = set()
        requests: list[EbayUrlResearchRequest] = []
        warnings: list[str] = []

        for item in snapshot.items:
            if item.status != ResearchQueueStatus.READY:
                continue
            if asset_id and item.asset_id != asset_id:
                continue
            if cert_number and item.cert_number != cert_number:
                continue
            if not item.source_url:
                continue
            key = (item.asset_id, item.research_type.value)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            asset = assets.get(item.asset_id, {})
            try:
                requests.append(
                    _request_from_item(
                        item,
                        asset,
                        reference_datetime=reference,
                        created_at=generated,
                    )
                )
            except Exception as exc:
                warnings.append(f"Skipped {item.asset_id}: {exc}")
                continue
            if limit is not None and len(requests) >= limit:
                break

        return EbayUrlResearchRequestExport(
            export_id=f"ebay-url-research:{reference.isoformat()}",
            requests=tuple(requests),
            warnings=tuple(warnings),
            reference_datetime=reference,
            generated_at=generated,
        )

    def write_json(
        self,
        export: EbayUrlResearchRequestExport,
        output_path: str | Path,
    ) -> Path:
        """Write a request export JSON file."""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(export.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path


def _request_from_item(
    item: Any,
    asset: dict[str, Any],
    *,
    reference_datetime: datetime,
    created_at: datetime,
) -> EbayUrlResearchRequest:
    return EbayUrlResearchRequest(
        request_id=f"ebay-url:{item.asset_id}:{item.research_type.value}",
        asset_id=item.asset_id,
        cert_number=item.cert_number,
        asset_name=item.asset_name,
        grade_issuer=_asset_text(asset, "grade_issuer", "grade_company"),
        grade=_asset_text(asset, "grade"),
        year=_asset_text(asset, "year"),
        set_name=_asset_text(asset, "set", "set_name", "brand"),
        card_number=_asset_text(asset, "card_number"),
        subject=_asset_text(asset, "subject", "player"),
        variety=_asset_optional_text(asset, "variety", "parallel"),
        special_designation=_asset_optional_text(asset, "special_designation"),
        ebay_sold_search_url=item.source_url,
        requested_fields=REQUIRED_EBAY_SOLD_REQUEST_FIELDS,
        provider_capability_required=ResearchCapability.SOLD_COMPARABLES,
        reference_datetime=reference_datetime,
        created_at=created_at,
        metadata={
            "queue_item_id": item.queue_item_id,
            "research_type": item.research_type.value,
            "valuation_coverage_status": item.valuation_coverage_status,
            "source": "Asset Master eBay Sold Search URL",
        },
    )


def _assets_by_id(runtime_session: Any) -> dict[str, dict[str, Any]]:
    return {
        str(asset.get("asset_id")): dict(asset)
        for asset in getattr(runtime_session, "enriched_runtime_assets", ())
        if asset.get("asset_id")
    }


def _asset_text(asset: dict[str, Any], *field_names: str) -> str:
    for field_name in field_names:
        value = _asset_optional_text(asset, field_name)
        if value:
            return value
    raise ValueError(f"missing asset field: {'/'.join(field_names)}")


def _asset_optional_text(asset: dict[str, Any], *field_names: str) -> str | None:
    for field_name in field_names:
        value = str(asset.get(field_name) or "").strip()
        if value:
            return value
    return None
