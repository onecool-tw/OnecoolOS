from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from datetime import timezone
from pathlib import Path

import pytest

from onecool_os.assets.master import AssetMasterRecord
from onecool_os.cli.main import main
from onecool_os.runtime import RuntimeSession
from onecool_os.valuation.evidence import EvidenceStatus
from onecool_os.work import ResearchWorkBridge
from onecool_os.work import WORK_CONTRACT_SCHEMA_VERSION
from onecool_os.work import WorkContractError
from onecool_os.work import WorkRequestType

REFERENCE = datetime(2026, 7, 13, 9, 0, tzinfo=timezone.utc)


def test_export_one_ready_research_work_request_contract() -> None:
    result = ResearchWorkBridge().export_ready_research_request(
        _session([_asset("A-1", "1001")], [_master("1001")]),
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )

    request = result.request
    payload = request.to_dict()

    assert payload["schema_version"] == WORK_CONTRACT_SCHEMA_VERSION
    assert payload["request_id"] == "work:ebay-url:A-1:SOLD_COMPARABLES"
    assert payload["request_type"] == WorkRequestType.COLLECTION_RESEARCH.value
    assert payload["asset_id"] == "A-1"
    assert payload["source_urls"] == [
        "https://www.ebay.com/sch/i.html?_nkw=ohtani&LH_Sold=1&LH_Complete=1"
    ]
    assert payload["constraints"]["provider_calls_inside_onecool_os"] is False
    assert payload["constraints"]["do_not_calculate_fair_value"] is True
    assert payload["constraints"]["do_not_create_valuation"] is True
    assert payload["constraints"]["do_not_update_nav"] is True


def test_export_work_request_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "work_request.json"

    result = ResearchWorkBridge().export_ready_research_request(
        _session([_asset("A-1", "1001")], [_master("1001")]),
        output_path=output,
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result.output_path == str(output)
    assert payload["schema_version"] == WORK_CONTRACT_SCHEMA_VERSION
    assert payload["request_id"] == "work:ebay-url:A-1:SOLD_COMPARABLES"


def test_export_without_ready_research_item_fails() -> None:
    with pytest.raises(WorkContractError, match="No READY research queue item"):
        ResearchWorkBridge().export_ready_research_request(
            _session([_asset("A-1", "1001")], [_master("1001", ebay_url=None)]),
            reference_datetime=REFERENCE,
            generated_at=REFERENCE,
        )


def test_import_work_response_validates_orf_and_evidence(tmp_path: Path) -> None:
    path = _write_work_response(
        tmp_path,
        _work_response(
            outputs={
                "orf_payload": _result_payload(
                    evidence=[_evidence("ev-1"), _evidence("ev-2", item_id="item-2")]
                )
            }
        ),
    )

    result = ResearchWorkBridge().import_response(path)

    assert result.evidence_count == 2
    assert result.evidence[0].status == EvidenceStatus.VERIFIED
    assert result.evidence[0].raw_metadata["orf_request_id"] == "ebay-url:A-1:SOLD_COMPARABLES"
    assert not hasattr(result, "valuation_records")


def test_import_work_response_rejects_non_completed_status(tmp_path: Path) -> None:
    path = _write_work_response(tmp_path, _work_response(status="FAILED"))

    with pytest.raises(WorkContractError, match="status is not COMPLETED"):
        ResearchWorkBridge().import_response(path)


def test_import_work_response_rejects_error_payload(tmp_path: Path) -> None:
    path = _write_work_response(
        tmp_path,
        _work_response(
            errors=[
                {
                    "category": "VALIDATION_FAILED",
                    "message": "Provider response did not pass validation.",
                }
            ]
        ),
    )

    with pytest.raises(WorkContractError, match="VALIDATION_FAILED"):
        ResearchWorkBridge().import_response(path)


def test_import_work_response_rejects_mismatched_request_id(tmp_path: Path) -> None:
    path = _write_work_response(tmp_path, _work_response())

    with pytest.raises(WorkContractError, match="request_id does not match"):
        ResearchWorkBridge().import_response(path, expected_request_id="work:other")


def test_import_work_response_rejects_missing_orf_payload(tmp_path: Path) -> None:
    path = _write_work_response(tmp_path, _work_response(outputs={"notes": []}))

    with pytest.raises(WorkContractError, match="ORF payload"):
        ResearchWorkBridge().import_response(path)


def test_import_uses_existing_evidence_validation(tmp_path: Path) -> None:
    path = _write_work_response(
        tmp_path,
        _work_response(outputs={"orf_payload": _result_payload(evidence=[_evidence("ev-1", item_id=None)])}),
    )

    result = ResearchWorkBridge().import_response(path)

    assert result.evidence[0].status == EvidenceStatus.REJECTED
    assert "Missing Item ID" in result.evidence[0].warnings


def test_work_bridge_does_not_mutate_payloads(tmp_path: Path) -> None:
    payload = _work_response(
        outputs={
            "orf_payload": _result_payload(
                evidence=[_evidence("ev-1"), _evidence("ev-2", item_id="item-2")]
            )
        }
    )
    before = deepcopy(payload)
    path = _write_work_response(tmp_path, payload)

    first = ResearchWorkBridge().import_response(path)
    second = ResearchWorkBridge().import_response(path)

    assert payload == before
    assert [item.to_dict() for item in first.evidence] == [item.to_dict() for item in second.evidence]


def test_cli_export_research_work_request(tmp_path: Path, monkeypatch, capsys) -> None:
    output = tmp_path / "work_request.json"
    monkeypatch.setattr(
        "onecool_os.cli.research._load_runtime_session",
        lambda reference: _session([_asset("A-1", "1001")], [_master("1001")]),
    )

    exit_code = main(["export-research-work-request", "--output", str(output)])

    captured = capsys.readouterr()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["request_id"] == "work:ebay-url:A-1:SOLD_COMPARABLES"
    assert "Provider calls inside Onecool OS: 0" in captured.out
    assert "Fair Value calculated: 0" in captured.out
    assert "Valuation records created: 0" in captured.out
    assert "NAV updated: 0" in captured.out


def test_cli_import_research_work_response(tmp_path: Path, capsys) -> None:
    path = _write_work_response(
        tmp_path,
        _work_response(
            outputs={
                "orf_payload": _result_payload(
                    evidence=[_evidence("ev-1"), _evidence("ev-2", item_id="item-2")]
                )
            }
        ),
    )

    exit_code = main(["import-research-work-response", "--input", str(path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Evidence records: 2" in captured.out
    assert "Existing ORF validation: passed" in captured.out
    assert "Existing Evidence validation: passed" in captured.out
    assert "Valuation records created: 0" in captured.out
    assert "NAV updated: 0" in captured.out


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


def _write_work_response(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "work_response.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _work_response(
    *,
    request_id: str = "work:ebay-url:A-1:SOLD_COMPARABLES",
    status: str = "COMPLETED",
    outputs: dict | None = None,
    errors: list[dict] | None = None,
) -> dict:
    return {
        "schema_version": WORK_CONTRACT_SCHEMA_VERSION,
        "request_id": request_id,
        "status": status,
        "provider": "ChatGPT Work Manual",
        "completed_at": REFERENCE.isoformat(),
        "execution_time": {
            "started_at": REFERENCE.isoformat(),
            "duration_seconds": 30,
        },
        "outputs": outputs or {"orf_payload": _result_payload(evidence=[_evidence("ev-1")])},
        "warnings": [],
        "errors": errors or [],
    }


def _result_payload(
    *,
    status: str = "COMPLETED",
    confidence: str = "HIGH",
    evidence: list[dict],
) -> dict:
    return {
        "batch_id": "batch-1",
        "provider_name": "ChatGPT Work Manual",
        "results": [
            {
                "result_id": "result-1",
                "request_id": "ebay-url:A-1:SOLD_COMPARABLES",
                "provider_name": "ChatGPT Work Manual",
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
