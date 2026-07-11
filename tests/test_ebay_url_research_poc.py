from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from datetime import datetime
from datetime import timezone
from pathlib import Path

import pytest

from onecool_os.assets.master import AssetMasterRecord
from onecool_os.assets.master import AssetMasterLoader
from onecool_os.cli.main import main
from onecool_os.research import EBAY_RESEARCH_PROVIDER_INSTRUCTION
from onecool_os.research import EbayUrlResearchRequest
from onecool_os.research import REQUIRED_EBAY_SOLD_REQUEST_FIELDS
from onecool_os.research.workbench import ResearchRequestExporter
from onecool_os.research.workbench import ResearchResultImporter
from onecool_os.research.workbench import ResearchWorkbenchError
from onecool_os.runtime import RuntimeSession
from onecool_os.valuation.evidence import EvidenceStatus

REFERENCE = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)


def test_export_ready_item() -> None:
    export = ResearchRequestExporter().export(
        _session([_asset("A-1", "1001")], [_master("1001")]),
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )

    assert len(export.requests) == 1
    assert export.requests[0].asset_id == "A-1"
    assert export.requests[0].ebay_sold_search_url.startswith("https://www.ebay.com")


def test_blocked_item_excluded() -> None:
    export = ResearchRequestExporter().export(
        _session([_asset("A-1", "1001")], [_master("1001", ebay_url="not-a-url")]),
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )

    assert export.requests == ()


def test_missing_ebay_url_excluded() -> None:
    export = ResearchRequestExporter().export(
        _session([_asset("A-1", "1001")], [_master("1001", ebay_url=None)]),
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )

    assert export.requests == ()


def test_deterministic_ordering_and_limit() -> None:
    session = _session(
        [_asset("A-2", "1002"), _asset("A-1", "1001"), _asset("A-3", "1003")],
        [_master("1002"), _master("1001"), _master("1003")],
    )

    export = ResearchRequestExporter().export(
        session,
        limit=2,
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )

    assert [request.asset_id for request in export.requests] == ["A-1", "A-2"]


def test_cert_number_selection() -> None:
    export = ResearchRequestExporter().export(
        _session(
            [_asset("A-1", "1001"), _asset("A-2", "1002")],
            [_master("1001"), _master("1002")],
        ),
        cert_number="1002",
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )

    assert [request.cert_number for request in export.requests] == ["1002"]


def test_asset_id_selection() -> None:
    export = ResearchRequestExporter().export(
        _session(
            [_asset("A-1", "1001"), _asset("A-2", "1002")],
            [_master("1001"), _master("1002")],
        ),
        asset_id="A-2",
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )

    assert [request.asset_id for request in export.requests] == ["A-2"]


def test_immutable_request_model_and_provider_instruction() -> None:
    request = _request()

    assert set(REQUIRED_EBAY_SOLD_REQUEST_FIELDS) <= set(request.requested_fields)
    assert "Do not invent results" in request.to_dict()["provider_instruction"]
    assert EBAY_RESEARCH_PROVIDER_INSTRUCTION in request.to_dict()["provider_instruction"]


def test_write_request_export_json(tmp_path: Path) -> None:
    export = ResearchRequestExporter().export(
        _session([_asset("A-1", "1001")], [_master("1001")]),
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )
    output = tmp_path / "ebay_url_requests.json"

    ResearchRequestExporter().write_json(export, output)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["request_count"] == 1


def test_valid_orf_result_import(tmp_path: Path) -> None:
    path = _write_result(tmp_path, _result_payload(evidence=[_evidence("ev-1"), _evidence("ev-2", item_id="item-2")]))

    result = ResearchResultImporter().import_json(path)

    assert result.evidence_count == 2
    assert result.evidence[0].status == EvidenceStatus.VERIFIED
    assert result.evidence[0].raw_metadata["orf_request_id"] == "ebay-url:A-1:SOLD_COMPARABLES"


def test_malformed_result_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{bad", encoding="utf-8")

    with pytest.raises(ResearchWorkbenchError, match="Research result import failed"):
        ResearchResultImporter().import_json(path)


def test_missing_sold_url_rejected_by_evidence_validation(tmp_path: Path) -> None:
    path = _write_result(tmp_path, _result_payload(evidence=[_evidence("ev-1", source_url=None)]))

    result = ResearchResultImporter().import_json(path)

    assert result.evidence[0].status == EvidenceStatus.REJECTED
    assert "Missing Sold URL" in result.evidence[0].warnings


def test_missing_item_id_rejected_by_evidence_validation(tmp_path: Path) -> None:
    path = _write_result(tmp_path, _result_payload(evidence=[_evidence("ev-1", item_id=None)]))

    result = ResearchResultImporter().import_json(path)

    assert result.evidence[0].status == EvidenceStatus.REJECTED
    assert "Missing Item ID" in result.evidence[0].warnings


def test_missing_sold_date_rejected_by_evidence_validation(tmp_path: Path) -> None:
    path = _write_result(tmp_path, _result_payload(evidence=[_evidence("ev-1", observed_date=None)]))

    result = ResearchResultImporter().import_json(path)

    assert result.evidence[0].status == EvidenceStatus.REJECTED
    assert "Malformed Date" in result.evidence[0].warnings


def test_no_match_result_accepted_as_no_match(tmp_path: Path) -> None:
    path = _write_result(
        tmp_path,
        _result_payload(
            status="NO_MATCH",
            confidence="UNVERIFIED",
            evidence=[_evidence("ev-1", status="NO_MATCH", confidence="UNVERIFIED")],
        ),
    )

    result = ResearchResultImporter().import_json(path)

    assert result.evidence[0].status == EvidenceStatus.NO_MATCH


def test_no_direct_valuation_record_creation(tmp_path: Path) -> None:
    path = _write_result(tmp_path, _result_payload(evidence=[_evidence("ev-1"), _evidence("ev-2", item_id="item-2")]))

    result = ResearchResultImporter().import_json(path)

    assert not hasattr(result, "valuation_records")


def test_no_mutation_and_deterministic_replay(tmp_path: Path) -> None:
    payload = _result_payload(evidence=[_evidence("ev-1"), _evidence("ev-2", item_id="item-2")])
    before = deepcopy(payload)
    path = _write_result(tmp_path, payload)

    first = ResearchResultImporter().import_json(path)
    second = ResearchResultImporter().import_json(path)

    assert payload == before
    assert [item.to_dict() for item in first.evidence] == [item.to_dict() for item in second.evidence]


def test_asset_master_loader_reads_native_hyperlink_targets(tmp_path: Path) -> None:
    source = Path("imports/asset_master/asset_master.xlsx")
    if not source.exists():
        pytest.skip("local Asset Master workbook not available")

    result = AssetMasterLoader().load(source, reference_datetime=REFERENCE)

    assert len([record for record in result.records if record.ebay_sold_search_url]) == len(result.records)


def test_private_research_files_ignored() -> None:
    result = subprocess.run(
        ["git", "check-ignore", "-q", "imports/research/ebay_url_requests.json"],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
    )

    assert result.returncode == 0


def test_cli_export_command(tmp_path: Path, capsys) -> None:
    if not Path("imports/psa/collection.csv").exists() or not Path("imports/asset_master/asset_master.xlsx").exists():
        pytest.skip("local PSA/Asset Master files not available")
    output = tmp_path / "requests.json"

    exit_code = main(["export-ebay-research-requests", "--limit", "1", "--output", str(output)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert output.exists()
    assert "Exported requests: 1" in captured.out
    assert "Provider calls: 0" in captured.out


def test_cli_import_command(tmp_path: Path, capsys) -> None:
    path = _write_result(tmp_path, _result_payload(evidence=[_evidence("ev-1"), _evidence("ev-2", item_id="item-2")]))

    exit_code = main(["import-research-results", "--input", str(path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Evidence records: 2" in captured.out
    assert "Valuation records created: 0" in captured.out


def _session(
    assets: list[dict[str, str | None]],
    masters: list[AssetMasterRecord],
) -> RuntimeSession:
    return RuntimeSession(
        imported_records=tuple(assets),
        asset_master_records=tuple(masters),
        generated_at=REFERENCE,
    )


def _asset(asset_id: str, cert_number: str) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "cert_number": cert_number,
        "year": "2018",
        "set": "Topps Update",
        "card_number": "US1",
        "subject": "Shohei Ohtani",
        "player": "Shohei Ohtani",
        "grade_company": "PSA",
        "grade_issuer": "PSA",
        "grade": "10",
        "cost": "100",
        "currency": "USD",
    }


def _master(
    cert_number: str,
    *,
    ebay_url: str | None = "https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1",
) -> AssetMasterRecord:
    return AssetMasterRecord(
        cert_number=cert_number,
        grade_issuer="PSA",
        grade="10",
        ebay_sold_search_url=ebay_url,
        psa_url=f"https://www.psacard.com/cert/{cert_number}",
        target_price="250",
        imported_at=REFERENCE,
    )


def _request() -> EbayUrlResearchRequest:
    return EbayUrlResearchRequest(
        request_id="ebay-url:A-1:SOLD_COMPARABLES",
        asset_id="A-1",
        cert_number="1001",
        asset_name="2018 Topps Update Shohei Ohtani US1 PSA 10",
        grade_issuer="PSA",
        grade="10",
        year="2018",
        set_name="Topps Update",
        card_number="US1",
        subject="Shohei Ohtani",
        ebay_sold_search_url="https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1",
        requested_fields=REQUIRED_EBAY_SOLD_REQUEST_FIELDS,
        provider_capability_required="SOLD_COMPARABLES",
        reference_datetime=REFERENCE,
        created_at=REFERENCE,
        metadata={},
    )


def _write_result(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "result.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _result_payload(
    *,
    status: str = "COMPLETED",
    confidence: str = "HIGH",
    evidence: list[dict],
) -> dict:
    return {
        "batch_id": "batch-1",
        "provider_name": "Manual Research Fixture",
        "results": [
            {
                "result_id": "result-1",
                "request_id": "ebay-url:A-1:SOLD_COMPARABLES",
                "provider_name": "Manual Research Fixture",
                "provider_type": "MANUAL",
                "provider_version": "v1",
                "capabilities": ["SOLD_COMPARABLES"],
                "research_type": "SOLD_COMPARABLES",
                "asset_id": "A-1",
                "cert_number": "1001",
                "status": status,
                "confidence": confidence,
                "evidence": evidence,
                "normalized_payload": {},
                "warnings": [] if status == "COMPLETED" else ["No exact comp verified"],
                "provider_metadata": {
                    "search_url": "https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1",
                    "search_queries": ["ohtani psa 10"],
                },
                "generated_at": REFERENCE.isoformat(),
                "reference_datetime": REFERENCE.isoformat(),
            }
        ],
        "warnings": [],
        "generated_at": REFERENCE.isoformat(),
        "reference_datetime": REFERENCE.isoformat(),
    }


def _evidence(
    evidence_id: str,
    *,
    source_url: str | None = "https://www.ebay.com/itm/item-1",
    item_id: str | None = "item-1",
    observed_date: str | None = "2026-07-01",
    status: str = "COMPLETED",
    confidence: str = "HIGH",
) -> dict:
    return {
        "evidence_id": evidence_id,
        "evidence_type": "SOLD_COMPARABLES",
        "source_name": "eBay Sold",
        "source_url": source_url,
        "item_id": item_id,
        "observed_value": "250.00",
        "currency": "USD",
        "observed_date": observed_date,
        "title": "2018 Topps Update Shohei Ohtani US1 PSA 10",
        "exact_match": True,
        "matched_fields": ["YEAR", "SET", "CARD_NUMBER", "SUBJECT", "GRADE_ISSUER", "GRADE"],
        "mismatched_fields": [],
        "confidence": confidence,
        "status": status,
        "warnings": [],
        "raw_metadata": {
            "search_url": "https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1",
            "listing_type": "AUCTION",
            "best_offer_used": False,
            "shipping_amount": "5.00",
        },
        "created_at": REFERENCE.isoformat(),
    }
