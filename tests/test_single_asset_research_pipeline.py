from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from datetime import datetime
from datetime import timezone
from pathlib import Path

from onecool_os.assets.master import AssetMasterRecord
from onecool_os.cli.main import main
from onecool_os.research.pipeline import PipelineStatus
from onecool_os.research.pipeline import SingleAssetResearchPipeline
from onecool_os.research.pipeline import locate_asset_by_cert
from onecool_os.research.pipeline import pipeline_report_lines
from onecool_os.research.pipeline import validate_target_identity
from onecool_os.runtime import RuntimeSession
from onecool_os.valuation.evidence import EvidenceStatus

REFERENCE = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)
EXPECTED = {
    "year": "2008",
    "set": "TOPPS",
    "card_number": "24",
    "subject": "KOBE BRYANT",
    "grade_issuer": "PSA",
    "grade": "9",
}


def test_target_asset_located_by_cert_number() -> None:
    asset = locate_asset_by_cert(_runtime(), "111003720")

    assert asset["asset_id"] == "PSA-111003720"
    assert asset["player"] == "KOBE BRYANT"


def test_identity_validation() -> None:
    asset = locate_asset_by_cert(_runtime(), "111003720")

    validate_target_identity(asset, EXPECTED)


def test_missing_asset_returns_blocked(tmp_path: Path) -> None:
    outcome = SingleAssetResearchPipeline().run(
        cert_number="missing",
        runtime_session=_runtime(),
        request_output=tmp_path / "request.json",
        result_input=tmp_path / "result.json",
        report_output=None,
        reference_datetime=REFERENCE,
    )

    assert outcome.result.status == PipelineStatus.BLOCKED
    assert "Asset not found" in outcome.result.warnings[0]


def test_duplicate_cert_returns_blocked(tmp_path: Path) -> None:
    runtime = RuntimeSession(
        imported_records=(_asset(), _asset(asset_id="PSA-DUP")),
        asset_master_records=(_master(),),
        generated_at=REFERENCE,
    )

    outcome = SingleAssetResearchPipeline().run(
        runtime_session=runtime,
        request_output=tmp_path / "request.json",
        result_input=tmp_path / "result.json",
        report_output=None,
        reference_datetime=REFERENCE,
    )

    assert outcome.result.status == PipelineStatus.BLOCKED
    assert "Duplicate cert number" in outcome.result.warnings[0]


def test_ambiguous_identity_returns_blocked(tmp_path: Path) -> None:
    outcome = SingleAssetResearchPipeline().run(
        runtime_session=_runtime(assets=(_asset(year="2009"),)),
        request_output=tmp_path / "request.json",
        result_input=tmp_path / "result.json",
        report_output=None,
        reference_datetime=REFERENCE,
    )

    assert outcome.result.status == PipelineStatus.BLOCKED
    assert "identity is ambiguous" in outcome.result.warnings[0]


def test_missing_ebay_url_returns_blocked(tmp_path: Path) -> None:
    outcome = SingleAssetResearchPipeline().run(
        runtime_session=_runtime(masters=(_master(ebay_url=None),)),
        request_output=tmp_path / "request.json",
        result_input=tmp_path / "result.json",
        report_output=None,
        reference_datetime=REFERENCE,
    )

    assert outcome.result.status == PipelineStatus.BLOCKED
    assert "eBay Sold Search URL is missing" in outcome.result.warnings[0]


def test_malformed_ebay_url_returns_blocked(tmp_path: Path) -> None:
    outcome = SingleAssetResearchPipeline().run(
        runtime_session=_runtime(masters=(_master(ebay_url="not-a-url"),)),
        request_output=tmp_path / "request.json",
        result_input=tmp_path / "result.json",
        report_output=None,
        reference_datetime=REFERENCE,
    )

    assert outcome.result.status == PipelineStatus.BLOCKED
    assert "BLOCKED" in outcome.result.warnings[0]


def test_missing_provider_result_returns_partial_and_exports_one_request(tmp_path: Path) -> None:
    request_output = tmp_path / "request.json"

    outcome = SingleAssetResearchPipeline().run(
        runtime_session=_runtime(),
        request_output=request_output,
        result_input=tmp_path / "missing-result.json",
        report_output=tmp_path / "report.json",
        reference_datetime=REFERENCE,
    )

    assert outcome.result.status == PipelineStatus.PARTIAL
    assert outcome.result.request_exported
    assert not outcome.result.runtime_attachment_completed
    payload = json.loads(request_output.read_text(encoding="utf-8"))
    assert payload["request_count"] == 1
    assert payload["requests"][0]["cert_number"] == "111003720"


def test_valid_provider_result_attaches_evidence(tmp_path: Path) -> None:
    result_input = _write_result(
        tmp_path,
        _result_payload(evidence=[_evidence("ev-1"), _evidence("ev-2", item_id="item-2")]),
    )

    outcome = SingleAssetResearchPipeline().run(
        runtime_session=_runtime(),
        request_output=tmp_path / "request.json",
        result_input=result_input,
        report_output=tmp_path / "report.json",
        reference_datetime=REFERENCE,
    )

    assert outcome.result.status == PipelineStatus.COMPLETED
    assert outcome.result.orf_validation_passed
    assert outcome.result.verified_evidence_count == 2
    assert outcome.result.runtime_attachment_completed
    assert len(outcome.runtime_session.verified_ebay_sold_evidence()) == 2


def test_malformed_provider_result_fails_safely(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{bad", encoding="utf-8")

    outcome = SingleAssetResearchPipeline().run(
        runtime_session=_runtime(),
        request_output=tmp_path / "request.json",
        result_input=bad,
        report_output=None,
        reference_datetime=REFERENCE,
    )

    assert outcome.result.status == PipelineStatus.FAILED
    assert outcome.result.provider_result_loaded
    assert not outcome.result.orf_validation_passed


def test_review_and_rejected_evidence_attached_but_classified(tmp_path: Path) -> None:
    result_input = _write_result(
        tmp_path,
        _result_payload(
            evidence=[
                _evidence("ev-1", raw_metadata={"title_ambiguous": True}),
                _evidence("ev-2", item_id="item-2", mismatched_fields=["GRADE"]),
            ]
        ),
    )

    outcome = SingleAssetResearchPipeline().run(
        runtime_session=_runtime(),
        request_output=tmp_path / "request.json",
        result_input=result_input,
        report_output=None,
        reference_datetime=REFERENCE,
    )

    assert outcome.result.review_required_count == 1
    assert outcome.result.rejected_count == 1
    assert len(outcome.runtime_session.review_required_ebay_evidence()) == 1
    assert len(outcome.runtime_session.rejected_ebay_evidence()) == 1


def test_no_match_count(tmp_path: Path) -> None:
    result_input = _write_result(
        tmp_path,
        _result_payload(
            status="NO_MATCH",
            confidence="UNVERIFIED",
            evidence=[_evidence("ev-1", status="NO_MATCH", confidence="UNVERIFIED")],
        ),
    )

    outcome = SingleAssetResearchPipeline().run(
        runtime_session=_runtime(),
        request_output=tmp_path / "request.json",
        result_input=result_input,
        report_output=None,
        reference_datetime=REFERENCE,
    )

    assert outcome.result.no_match_count == 1


def test_no_direct_valuation_or_nav_update(tmp_path: Path) -> None:
    result_input = _write_result(
        tmp_path,
        _result_payload(evidence=[_evidence("ev-1"), _evidence("ev-2", item_id="item-2")]),
    )

    outcome = SingleAssetResearchPipeline().run(
        runtime_session=_runtime(),
        request_output=tmp_path / "request.json",
        result_input=result_input,
        report_output=None,
        reference_datetime=REFERENCE,
    )

    assert not hasattr(outcome.result, "valuation_records")
    assert "NAV" not in outcome.result.to_dict()


def test_no_mutation_and_deterministic_replay(tmp_path: Path) -> None:
    runtime = _runtime()
    before = tuple(dict(asset) for asset in runtime.enriched_runtime_assets)
    result_input = _write_result(
        tmp_path,
        _result_payload(evidence=[_evidence("ev-1"), _evidence("ev-2", item_id="item-2")]),
    )

    first = SingleAssetResearchPipeline().run(
        runtime_session=runtime,
        request_output=tmp_path / "request-1.json",
        result_input=result_input,
        report_output=None,
        reference_datetime=REFERENCE,
    )
    second = SingleAssetResearchPipeline().run(
        runtime_session=runtime,
        request_output=tmp_path / "request-2.json",
        result_input=result_input,
        report_output=None,
        reference_datetime=REFERENCE,
    )

    assert tuple(dict(asset) for asset in runtime.enriched_runtime_assets) == before
    assert first.result.to_dict() == second.result.to_dict()


def test_report_is_concise_and_omits_raw_metadata(tmp_path: Path) -> None:
    result_input = _write_result(
        tmp_path,
        _result_payload(evidence=[_evidence("ev-1"), _evidence("ev-2", item_id="item-2")]),
    )

    outcome = SingleAssetResearchPipeline().run(
        runtime_session=_runtime(),
        request_output=tmp_path / "request.json",
        result_input=result_input,
        report_output=tmp_path / "report.json",
        reference_datetime=REFERENCE,
    )
    lines = "\n".join(pipeline_report_lines(outcome.result))
    report = (tmp_path / "report.json").read_text(encoding="utf-8")

    assert "raw_metadata" not in report
    assert "provider_metadata" not in report
    assert "Fair Value" not in lines
    assert "Pipeline Status:" in lines


def test_private_pipeline_files_ignored() -> None:
    request_result = subprocess.run(
        [
            "git",
            "check-ignore",
            "-q",
            "imports/research/kobe_111003720_request.json",
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
    )
    report_result = subprocess.run(
        [
            "git",
            "check-ignore",
            "-q",
            "outputs/research/kobe_111003720_pipeline_report.json",
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
    )

    assert request_result.returncode == 0
    assert report_result.returncode == 0


def test_cli_single_asset_pipeline_partial(tmp_path: Path, capsys) -> None:
    if not Path("imports/psa/collection.csv").exists() or not Path("imports/asset_master/asset_master.xlsx").exists():
        return

    exit_code = main(
        [
            "run-single-asset-research",
            "--request-output",
            str(tmp_path / "request.json"),
            "--result-input",
            str(tmp_path / "missing-result.json"),
            "--report-output",
            str(tmp_path / "report.json"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Pipeline Status:" in captured.out
    assert "PARTIAL" in captured.out
    assert (tmp_path / "request.json").exists()


def _runtime(
    *,
    assets: tuple[dict, ...] | None = None,
    masters: tuple[AssetMasterRecord, ...] | None = None,
) -> RuntimeSession:
    return RuntimeSession(
        imported_records=assets or (_asset(),),
        asset_master_records=masters or (_master(),),
        generated_at=REFERENCE,
    )


def _asset(
    *,
    asset_id: str = "PSA-111003720",
    cert_number: str = "111003720",
    year: str = "2008",
) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "cert_number": cert_number,
        "year": year,
        "set": "TOPPS",
        "brand": "TOPPS",
        "card_number": "24",
        "subject": "KOBE BRYANT",
        "player": "KOBE BRYANT",
        "grade_company": "PSA",
        "grade_issuer": "PSA",
        "grade": "9",
        "cost": "133.99",
        "currency": "USD",
    }


def _master(
    *,
    ebay_url: str | None = "https://www.ebay.com/sch/i.html?_nkw=2008+TOPPS+24+KOBE+BRYANT++PSA+9&LH_Sold=1&LH_Complete=1",
) -> AssetMasterRecord:
    return AssetMasterRecord(
        cert_number="111003720",
        grade_issuer="PSA",
        grade="9",
        ebay_sold_search_url=ebay_url,
        psa_url="https://www.psacard.com/cert/111003720",
        imported_at=REFERENCE,
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
        "batch_id": "kobe-111003720-results",
        "provider_name": "Manual Research Fixture",
        "results": [
            {
                "result_id": "result-kobe-111003720",
                "request_id": "ebay-url:PSA-111003720:SOLD_COMPARABLES",
                "provider_name": "Manual Research Fixture",
                "provider_type": "MANUAL",
                "provider_version": "v1",
                "capabilities": ["SOLD_COMPARABLES"],
                "research_type": "SOLD_COMPARABLES",
                "asset_id": "PSA-111003720",
                "cert_number": "111003720",
                "status": status,
                "confidence": confidence,
                "evidence": evidence,
                "normalized_payload": {},
                "warnings": [] if status == "COMPLETED" else ["No exact comp verified"],
                "provider_metadata": {
                    "search_url": "https://www.ebay.com/sch/i.html?_nkw=2008+TOPPS+24+KOBE+BRYANT++PSA+9&LH_Sold=1&LH_Complete=1",
                    "search_queries": ["2008 TOPPS 24 KOBE BRYANT PSA 9"],
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
    item_id: str | None = "item-1",
    status: str = "COMPLETED",
    confidence: str = "HIGH",
    raw_metadata: dict | None = None,
    mismatched_fields: list[str] | None = None,
) -> dict:
    metadata = {
        "search_url": "https://www.ebay.com/sch/i.html?_nkw=2008+TOPPS+24+KOBE+BRYANT++PSA+9&LH_Sold=1&LH_Complete=1",
        "listing_type": "AUCTION",
        "best_offer_used": False,
        "shipping_amount": "5.00",
    }
    metadata.update(raw_metadata or {})
    return {
        "evidence_id": evidence_id,
        "evidence_type": "SOLD_COMPARABLES",
        "source_name": "eBay Sold",
        "source_url": f"https://www.ebay.com/itm/{item_id or 'missing'}",
        "item_id": item_id,
        "observed_value": "199.99",
        "currency": "USD",
        "observed_date": "2026-07-01",
        "title": "2008 TOPPS 24 KOBE BRYANT PSA 9",
        "exact_match": True,
        "matched_fields": ["YEAR", "SET", "CARD_NUMBER", "SUBJECT", "GRADE_ISSUER", "GRADE"],
        "mismatched_fields": mismatched_fields or [],
        "confidence": confidence,
        "status": status,
        "warnings": [],
        "raw_metadata": metadata,
        "created_at": REFERENCE.isoformat(),
    }
