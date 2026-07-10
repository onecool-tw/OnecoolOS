"""Deterministic collection sync comparison."""

from __future__ import annotations

from collections import Counter
from datetime import UTC
from datetime import datetime
from typing import Any

from onecool_os.assets.master import AssetMasterRecord
from onecool_os.sync.models import CollectionDifference
from onecool_os.sync.models import SyncReport

IDENTITY_FIELDS = ("year", "set", "card_number", "subject", "grade_issuer", "grade")


def compare_collection(
    imported_records: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    asset_master_records: list[AssetMasterRecord]
    | tuple[AssetMasterRecord, ...],
    *,
    reference_datetime: datetime | None = None,
) -> SyncReport:
    """Compare imported collection records with Asset Master metadata."""

    generated_at = reference_datetime or datetime.now(UTC)
    imported = tuple(dict(record) for record in imported_records)
    masters = tuple(asset_master_records)
    differences: list[CollectionDifference] = []
    warnings: list[str] = []

    imported_by_cert = _group_by_cert(imported)
    master_by_cert = _group_masters_by_cert(masters)

    differences.extend(_duplicate_cert_differences(imported_by_cert, master_by_cert))
    differences.extend(_duplicate_asset_differences(imported))

    matched_import_ids: set[int] = set()
    matched_master_ids: set[int] = set()

    for cert_number in sorted(set(imported_by_cert) & set(master_by_cert)):
        imported_record = imported_by_cert[cert_number][0]
        master_record = master_by_cert[cert_number][0]
        matched_import_ids.add(id(imported_record))
        matched_master_ids.add(id(master_record))
        differences.extend(_matched_differences(imported_record, master_record))

    fallback_matches = _fallback_matches(imported, masters, matched_import_ids, matched_master_ids)
    for imported_record, master_record in fallback_matches:
        matched_import_ids.add(id(imported_record))
        matched_master_ids.add(id(master_record))
        differences.extend(_matched_differences(imported_record, master_record))

    for imported_record in imported:
        if id(imported_record) in matched_import_ids:
            continue
        cert_number = _cert_number(imported_record)
        differences.append(
            CollectionDifference(
                cert_number=cert_number,
                asset_id=_asset_id(imported_record),
                difference_type="NEW_CARD",
                severity="MEDIUM",
                source_value=cert_number,
                target_value=None,
                description="Imported card has no Asset Master record.",
            )
        )
        differences.append(
            CollectionDifference(
                cert_number=cert_number,
                asset_id=_asset_id(imported_record),
                difference_type="MISSING_IN_ASSET_MASTER",
                severity="HIGH",
                source_value=cert_number,
                target_value=None,
                description="Imported card is missing in Asset Master.",
            )
        )

    for master_record in masters:
        if id(master_record) in matched_master_ids:
            continue
        differences.append(
            CollectionDifference(
                cert_number=master_record.cert_number,
                asset_id=master_record.asset_id,
                difference_type="MISSING_IN_IMPORT",
                severity="HIGH",
                source_value=master_record.cert_number,
                target_value=None,
                description="Asset Master record has no imported collection match.",
            )
        )

    differences = sorted(
        differences,
        key=lambda difference: (
            difference.cert_number,
            difference.difference_type,
            difference.description,
        ),
    )
    warnings.extend(_warnings_for_differences(differences))
    return SyncReport(
        imported_records=len(imported),
        asset_master_records=len(masters),
        matched_records=len(matched_import_ids),
        differences=tuple(differences),
        warnings=tuple(warnings),
        collection_health=_collection_health(differences),
        generated_at=generated_at,
    )


def _duplicate_cert_differences(
    imported_by_cert: dict[str, list[dict[str, Any]]],
    master_by_cert: dict[str, list[AssetMasterRecord]],
) -> list[CollectionDifference]:
    differences: list[CollectionDifference] = []
    for cert_number, records in sorted(imported_by_cert.items()):
        if cert_number and len(records) > 1:
            differences.append(
                CollectionDifference(
                    cert_number=cert_number,
                    asset_id=None,
                    difference_type="DUPLICATE_CERT",
                    severity="CRITICAL",
                    source_value=len(records),
                    target_value=1,
                    description="Duplicate cert number in imported collection.",
                )
            )
    for cert_number, records in sorted(master_by_cert.items()):
        if cert_number and len(records) > 1:
            differences.append(
                CollectionDifference(
                    cert_number=cert_number,
                    asset_id=records[0].asset_id,
                    difference_type="DUPLICATE_CERT",
                    severity="CRITICAL",
                    source_value=len(records),
                    target_value=1,
                    description="Duplicate cert number in Asset Master.",
                )
            )
    return differences


def _duplicate_asset_differences(
    imported: tuple[dict[str, Any], ...],
) -> list[CollectionDifference]:
    asset_ids = [_asset_id(record) for record in imported if _asset_id(record)]
    counts = Counter(asset_ids)
    return [
        CollectionDifference(
            cert_number="",
            asset_id=asset_id,
            difference_type="DUPLICATE_ASSET",
            severity="CRITICAL",
            source_value=count,
            target_value=1,
            description="Duplicate asset identifier in imported collection.",
        )
        for asset_id, count in sorted(counts.items())
        if count > 1
    ]


def _matched_differences(
    imported_record: dict[str, Any],
    master_record: AssetMasterRecord,
) -> list[CollectionDifference]:
    cert_number = _cert_number(imported_record) or master_record.cert_number
    differences: list[CollectionDifference] = []
    grade_issuer = _master_value(master_record, "grade_issuer")
    if grade_issuer and grade_issuer != _normalized(_grade_issuer(imported_record)):
        differences.append(
            _difference(
                imported_record,
                master_record,
                "GRADE_ISSUER_CHANGED",
                "CRITICAL",
                _grade_issuer(imported_record),
                master_record.grade_issuer,
                "Grade issuer differs between import and Asset Master.",
            )
        )
    if master_record.grade and _normalized(master_record.grade) != _normalized(
        imported_record.get("grade")
    ):
        differences.append(
            _difference(
                imported_record,
                master_record,
                "GRADE_CHANGED",
                "CRITICAL",
                imported_record.get("grade"),
                master_record.grade,
                "Grade differs between import and Asset Master.",
            )
        )
    master_variety = _metadata_value(master_record, "variety") or _metadata_value(master_record, "parallel")
    imported_variety = imported_record.get("variety") or imported_record.get("parallel")
    if master_variety and _normalized(master_variety) != _normalized(imported_variety):
        differences.append(
            _difference(
                imported_record,
                master_record,
                "VARIETY_CHANGED",
                "CRITICAL",
                imported_variety,
                master_variety,
                "Variety differs between import and Asset Master.",
            )
        )
    if master_record.cost_override is not None:
        differences.append(
            _difference(
                imported_record,
                master_record,
                "COST_OVERRIDE",
                "INFO",
                imported_record.get("cost"),
                str(master_record.cost_override),
                "Asset Master contains explicit cost override metadata.",
            )
        )
    if not master_record.ebay_sold_search_url:
        differences.append(
            _difference(
                imported_record,
                master_record,
                "EBAY_URL_MISSING",
                "LOW",
                None,
                None,
                "Asset Master is missing eBay Sold search URL.",
            )
        )
    if not master_record.psa_url:
        differences.append(
            _difference(
                imported_record,
                master_record,
                "PSA_URL_MISSING",
                "LOW",
                None,
                None,
                "Asset Master is missing PSA official URL.",
            )
        )
    if master_record.target_price is None:
        differences.append(
            _difference(
                imported_record,
                master_record,
                "TARGET_PRICE_MISSING",
                "LOW",
                None,
                None,
                "Asset Master is missing target price.",
            )
        )
    imported_notes = _normalized(imported_record.get("notes"))
    master_notes = _normalized(master_record.notes)
    if imported_notes and master_notes and imported_notes != master_notes:
        differences.append(
            _difference(
                imported_record,
                master_record,
                "NOTES_CHANGED",
                "INFO",
                imported_record.get("notes"),
                master_record.notes,
                "Notes differ between import and Asset Master.",
            )
        )
    return differences


def _difference(
    imported_record: dict[str, Any],
    master_record: AssetMasterRecord,
    difference_type: str,
    severity: str,
    source_value: Any,
    target_value: Any,
    description: str,
) -> CollectionDifference:
    return CollectionDifference(
        cert_number=_cert_number(imported_record) or master_record.cert_number,
        asset_id=_asset_id(imported_record) or master_record.asset_id,
        difference_type=difference_type,
        severity=severity,
        source_value=source_value,
        target_value=target_value,
        description=description,
    )


def _fallback_matches(
    imported: tuple[dict[str, Any], ...],
    masters: tuple[AssetMasterRecord, ...],
    matched_import_ids: set[int],
    matched_master_ids: set[int],
) -> tuple[tuple[dict[str, Any], AssetMasterRecord], ...]:
    matches: list[tuple[dict[str, Any], AssetMasterRecord]] = []
    for imported_record in imported:
        if id(imported_record) in matched_import_ids:
            continue
        imported_identity = _import_identity(imported_record)
        if not all(imported_identity):
            continue
        for master_record in masters:
            if id(master_record) in matched_master_ids:
                continue
            if imported_identity == _master_identity(master_record):
                matches.append((imported_record, master_record))
                matched_master_ids.add(id(master_record))
                break
    return tuple(matches)


def _collection_health(
    differences: tuple[CollectionDifference, ...] | list[CollectionDifference],
) -> int:
    if any(difference.severity == "CRITICAL" for difference in differences):
        return 0
    score = 100
    for difference in differences:
        if difference.difference_type in {
            "TARGET_PRICE_MISSING",
            "NOTES_CHANGED",
            "COST_OVERRIDE",
        }:
            score -= 1
        elif difference.difference_type in {"EBAY_URL_MISSING", "PSA_URL_MISSING"}:
            score -= 2
        elif difference.difference_type in {
            "MISSING_IN_ASSET_MASTER",
            "MISSING_IN_IMPORT",
            "NEW_CARD",
        }:
            score -= 5
        elif difference.difference_type == "DUPLICATE_CERT":
            score -= 20
    return max(0, score)


def _warnings_for_differences(
    differences: tuple[CollectionDifference, ...] | list[CollectionDifference],
) -> tuple[str, ...]:
    return tuple(
        f"{difference.severity}: {difference.difference_type} "
        f"{difference.cert_number or difference.asset_id}"
        for difference in differences
        if difference.severity in {"HIGH", "CRITICAL"}
    )


def _group_by_cert(
    imported: tuple[dict[str, Any], ...],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in imported:
        grouped.setdefault(_cert_number(record), []).append(record)
    return grouped


def _group_masters_by_cert(
    masters: tuple[AssetMasterRecord, ...],
) -> dict[str, list[AssetMasterRecord]]:
    grouped: dict[str, list[AssetMasterRecord]] = {}
    for record in masters:
        grouped.setdefault(_normalized(record.cert_number), []).append(record)
    return grouped


def _import_identity(record: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
    return (
        _normalized(record.get("year")),
        _normalized(record.get("set") or record.get("brand")),
        _normalized(record.get("card_number")),
        _normalized(record.get("subject") or record.get("player")),
        _normalized(_grade_issuer(record)),
        _normalized(record.get("grade")),
    )


def _master_identity(record: AssetMasterRecord) -> tuple[str, str, str, str, str, str]:
    return (
        _metadata_value(record, "year"),
        _metadata_value(record, "set"),
        _metadata_value(record, "card_number"),
        _metadata_value(record, "subject") or _metadata_value(record, "player"),
        _master_value(record, "grade_issuer"),
        _master_value(record, "grade"),
    )


def _metadata_value(record: AssetMasterRecord, key: str) -> str:
    metadata = record.metadata or {}
    for metadata_key, value in metadata.items():
        if metadata_key.lower().replace(" ", "_") == key:
            return _normalized(value)
    return ""


def _master_value(record: AssetMasterRecord, field_name: str) -> str:
    return _normalized(getattr(record, field_name))


def _cert_number(record: dict[str, Any]) -> str:
    return _normalized(record.get("cert_number") or record.get("serial_number"))


def _asset_id(record: dict[str, Any]) -> str | None:
    value = _normalized(record.get("asset_id"))
    return value or None


def _grade_issuer(record: dict[str, Any]) -> str:
    return str(
        record.get("grade_issuer")
        or record.get("grade_company")
        or record.get("grader")
        or ""
    )


def _normalized(value: Any) -> str:
    return str(value or "").strip().upper()
