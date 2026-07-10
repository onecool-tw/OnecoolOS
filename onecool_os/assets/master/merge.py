"""Merge Asset Master metadata into imported runtime assets."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from onecool_os.assets.master.models import AssetMasterRecord

PROTECTED_IDENTITY_FIELDS = frozenset(
    {
        "year",
        "set",
        "card_number",
        "subject",
        "player",
        "grade_issuer",
        "grade_company",
        "grade",
        "variety",
        "parallel",
        "cert_number",
        "serial_number",
    }
)


def merge_asset_master(
    imported_records: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    master_records: list[AssetMasterRecord] | tuple[AssetMasterRecord, ...],
) -> tuple[dict[str, Any], ...]:
    """Return imported records enriched with Asset Master metadata.

    Imported PSA/BGS identity remains authoritative. Asset Master data is stored
    under explicit metadata keys and never mutates the input records.
    """

    master_by_cert = {
        _normalize_cert(record.cert_number): record for record in master_records
    }
    enriched_records: list[dict[str, Any]] = []
    for imported_record in imported_records:
        enriched = deepcopy(imported_record)
        cert_number = _normalize_cert(
            imported_record.get("cert_number")
            or imported_record.get("serial_number")
        )
        master_record = master_by_cert.get(cert_number)
        if master_record is None:
            enriched_records.append(enriched)
            continue
        enriched["asset_master"] = master_record.to_metadata()
        cost_override = master_record.cost_override_payload()
        if cost_override is not None:
            enriched["asset_master_cost_override"] = cost_override
            enriched["cost_override_applied"] = False
        enriched_records.append(enriched)
    return tuple(enriched_records)


def _normalize_cert(value: Any) -> str:
    return str(value or "").strip().upper()
