from __future__ import annotations

import json
from datetime import datetime
from datetime import timezone
from pathlib import Path

from onecool_os.cli.main import main
from onecool_os.research.workbench import ResearchResultImporter
from onecool_os.valuation.evidence import EvidenceStatus
from onecool_os.work import SoldComparableInput
from onecool_os.work import WorkResponseBuilder

REFERENCE = datetime(2026, 7, 14, 9, 0, tzinfo=timezone.utc)


def test_build_response_from_comparable() -> None:
    request = WorkResponseBuilder().load_request(_write_request_payload_to_tmp())

    response = WorkResponseBuilder().build_response(
        request,
        [_comparable()],
        completed_at=REFERENCE,
    )
    payload = response.to_dict()
    evidence = payload["outputs"]["orf_payload"]["results"][0]["evidence"][0]

    assert payload["schema_version"] == "1.0"
    assert payload["request_id"] == "work:ebay-url:PSA-111003720:SOLD_COMPARABLES"
    assert evidence["item_id"] == "123456789012"
    assert evidence["source_url"] == "https://www.ebay.com/itm/123456789012"
    assert evidence["observed_value"] == "125.00"
    assert evidence["currency"] == "USD"
    assert evidence["exact_match"] is True
    assert evidence["status"] == "COMPLETED"
    assert evidence["raw_metadata"]["canonical_comparable"]["ebay_item_id"] == "123456789012"


def test_build_response_validates_through_existing_orf_and_evidence(tmp_path: Path) -> None:
    request_path = _write_request(tmp_path)
    request = WorkResponseBuilder().load_request(request_path)
    response = WorkResponseBuilder().build_response(
        request,
        [_comparable(), _comparable(ebay_item_id="123456789013")],
        completed_at=REFERENCE,
    )

    result = ResearchResultImporter().import_payload(response.outputs["orf_payload"])

    assert result.evidence_count == 2
    assert result.evidence[0].status == EvidenceStatus.VERIFIED
    assert result.evidence[0].ebay_item_id == "123456789012"


def test_needs_review_comparable_is_preserved() -> None:
    request = WorkResponseBuilder().load_request(_write_request_payload_to_tmp())

    response = WorkResponseBuilder().build_response(
        request,
        [_comparable(exact_match=False, warnings=("CARD_NUMBER_MISSING",))],
        completed_at=REFERENCE,
    )
    result = ResearchResultImporter().import_payload(response.outputs["orf_payload"])

    assert result.evidence[0].status == EvidenceStatus.NEEDS_REVIEW
    assert "CARD_NUMBER_MISSING" in result.evidence[0].warnings


def test_zero_comparables_builds_no_match_response() -> None:
    request = WorkResponseBuilder().load_request(_write_request_payload_to_tmp())

    response = WorkResponseBuilder().build_response(
        request,
        [],
        completed_at=REFERENCE,
    )
    result_payload = response.to_dict()["outputs"]["orf_payload"]["results"][0]

    assert response.warnings == ("NO_MATCH",)
    assert result_payload["status"] == "NO_MATCH"
    assert result_payload["confidence"] == "UNVERIFIED"
    assert result_payload["evidence"] == []


def test_write_response_json(tmp_path: Path) -> None:
    request = WorkResponseBuilder().load_request(_write_request(tmp_path))
    response = WorkResponseBuilder().build_response(
        request,
        [_comparable()],
        completed_at=REFERENCE,
    )
    output = tmp_path / "response.json"

    WorkResponseBuilder().write_response(response, output)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["outputs"]["orf_payload"]["results"][0]["evidence"][0]["item_id"] == "123456789012"


def test_interactive_builder_writes_response(tmp_path: Path) -> None:
    request_path = _write_request(tmp_path)
    output = tmp_path / "response.json"
    answers = iter(
        [
            "1",
            "123456789012",
            "https://www.ebay.com/itm/123456789012",
            "2008 Topps Kobe Bryant #24 PSA 9",
            "125.00",
            "usd",
            "2026-07-01",
            "buy_it_now",
            "N",
            "5.00",
            "Y",
            "",
        ]
    )

    WorkResponseBuilder().build_interactive(
        request_path,
        output,
        input_func=lambda prompt: next(answers),
        print_func=lambda text: None,
        completed_at=REFERENCE,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    evidence = payload["outputs"]["orf_payload"]["results"][0]["evidence"][0]
    assert evidence["currency"] == "USD"
    assert evidence["raw_metadata"]["best_offer_used"] is False
    assert evidence["raw_metadata"]["shipping_amount"] == "5.00"


def test_cli_build_work_response(tmp_path: Path, monkeypatch, capsys) -> None:
    request_path = _write_request(tmp_path)
    output = tmp_path / "response.json"
    answers = iter(
        [
            "0",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    exit_code = main(
        [
            "build-work-response",
            "--request",
            str(request_path),
            "--output",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["warnings"] == ["NO_MATCH"]
    assert "Work Response written:" in captured.out
    assert "Fair Value calculated: 0" in captured.out
    assert "Valuation records created: 0" in captured.out
    assert "NAV updated: 0" in captured.out


def _write_request_payload_to_tmp() -> Path:
    import tempfile

    path = Path(tempfile.mkdtemp()) / "request.json"
    path.write_text(json.dumps(_request_payload()), encoding="utf-8")
    return path


def _write_request(tmp_path: Path) -> Path:
    path = tmp_path / "request.json"
    path.write_text(json.dumps(_request_payload()), encoding="utf-8")
    return path


def _request_payload() -> dict:
    return {
        "schema_version": "1.0",
        "request_id": "work:ebay-url:PSA-111003720:SOLD_COMPARABLES",
        "request_type": "COLLECTION_RESEARCH",
        "asset_id": "PSA-111003720",
        "portfolio_id": None,
        "reference_datetime": REFERENCE.isoformat(),
        "priority": "HIGH",
        "requested_action": "Find verified eBay Sold evidence for this asset.",
        "context": {
            "research_request": {
                "request_id": "ebay-url:PSA-111003720:SOLD_COMPARABLES",
                "asset_id": "PSA-111003720",
                "cert_number": "111003720",
                "asset_name": "2008 TOPPS KOBE BRYANT 24 PSA 9",
                "ebay_sold_search_url": "https://www.ebay.com/sch/i.html?_nkw=kobe&LH_Sold=1&LH_Complete=1",
            }
        },
        "source_urls": [
            "https://www.ebay.com/sch/i.html?_nkw=kobe&LH_Sold=1&LH_Complete=1"
        ],
        "constraints": {
            "return_evidence_only": True,
        },
    }


def _comparable(
    *,
    ebay_item_id: str = "123456789012",
    exact_match: bool = True,
    warnings: tuple[str, ...] = (),
) -> SoldComparableInput:
    return SoldComparableInput(
        ebay_item_id=ebay_item_id,
        sold_item_url=f"https://www.ebay.com/itm/{ebay_item_id}",
        title="2008 Topps Kobe Bryant #24 PSA 9",
        sold_price="125.00",
        currency="USD",
        sold_date="2026-07-01",
        listing_type="BUY_IT_NOW",
        best_offer_used=False,
        shipping_amount="5.00",
        exact_match=exact_match,
        warnings=warnings,
    )
