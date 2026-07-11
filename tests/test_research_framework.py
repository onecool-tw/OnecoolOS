from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from datetime import timezone
import json
from pathlib import Path
from typing import Any

import pytest

from onecool_os.research import ResearchBatch
from onecool_os.research import ResearchCapability
from onecool_os.research import ResearchConfidence
from onecool_os.research import ResearchError
from onecool_os.research import ResearchEvidence
from onecool_os.research import ResearchJsonLoader
from onecool_os.research import ResearchProvider
from onecool_os.research import ResearchProviderRegistry
from onecool_os.research import ResearchProviderType
from onecool_os.research import ResearchRequest
from onecool_os.research import ResearchResult
from onecool_os.research import ResearchStatus
from onecool_os.research import ResearchType
from onecool_os.research import normalize_confidence
from onecool_os.research import normalize_currency
from onecool_os.research import normalize_provider_name
from onecool_os.research import normalize_provider_version
from onecool_os.research import normalize_status
from onecool_os.research import normalize_url
from onecool_os.research import normalize_warnings
from onecool_os.research import research_evidence_to_ebay_sold_evidence
from onecool_os.research import validate_research_result
from onecool_os.valuation.evidence import EvidenceStatus

REFERENCE = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)


def test_research_request_creation() -> None:
    request = ResearchRequest(
        request_id="req-1",
        research_type="SOLD_COMPARABLES",
        asset_id="PSA-123",
        cert_number="123",
        provider_name="ChatGPT",
        query="2018 Topps Ohtani PSA 10",
        source_url="https://example.com/search",
        requested_fields=["sold_price", "sold_date"],
        reference_datetime=REFERENCE.isoformat(),
        metadata={"purpose": "dogfood"},
        created_at=REFERENCE.isoformat(),
    )

    assert request.research_type == ResearchType.SOLD_COMPARABLES
    assert request.requested_fields == ("sold_price", "sold_date")
    assert request.to_dict()["reference_datetime"] == REFERENCE.isoformat()


def test_research_result_creation() -> None:
    result = _result()

    assert result.provider_type == ResearchProviderType.CHATGPT
    assert result.capabilities == (
        ResearchCapability.SOLD_COMPARABLES,
        ResearchCapability.STRUCTURED_DATA,
    )
    assert result.evidence[0].confidence == ResearchConfidence.HIGH


def test_models_are_immutable() -> None:
    request = ResearchRequest("req-1", "SOLD_COMPARABLES")

    with pytest.raises(FrozenInstanceError):
        request.request_id = "changed"  # type: ignore[misc]


def test_provider_registry_registration() -> None:
    provider = FixtureResearchProvider("Fixture")
    registry = ResearchProviderRegistry()

    registry.register_provider(provider)

    assert registry.list_providers() == ("fixture",)
    assert registry.get_provider("fixture") is provider


def test_duplicate_provider_registration_rejected() -> None:
    registry = ResearchProviderRegistry()
    registry.register_provider(FixtureResearchProvider("Fixture"))

    with pytest.raises(ResearchError, match="already registered"):
        registry.register_provider(FixtureResearchProvider("fixture"))


def test_unknown_provider_rejected() -> None:
    registry = ResearchProviderRegistry()

    with pytest.raises(ResearchError, match="Unknown research provider"):
        registry.get_provider("missing")


def test_capability_lookup() -> None:
    registry = ResearchProviderRegistry()
    sold = FixtureResearchProvider("Sold", capabilities=(ResearchCapability.SOLD_COMPARABLES,))
    news = FixtureResearchProvider("News", capabilities=(ResearchCapability.NEWS,))
    registry.register_provider(news)
    registry.register_provider(sold)

    assert registry.list_by_capability("SOLD_COMPARABLES") == (sold,)


def test_deterministic_normalization() -> None:
    assert normalize_provider_name("  ChatGPT  ") == "chatgpt"
    assert normalize_provider_version("v1.2") == "v1.2"
    assert normalize_confidence("low") == ResearchConfidence.LOW
    assert normalize_status("completed") == ResearchStatus.COMPLETED
    assert normalize_currency("usd") == "USD"
    assert normalize_url("https://example.com/item") == "https://example.com/item"
    assert normalize_warnings(["A", "A", "B"]) == ("A", "B")


def test_malformed_provider_version_rejected() -> None:
    with pytest.raises(ResearchError, match="Invalid provider_version"):
        _result(provider_version="alpha")


def test_missing_metadata_invalid() -> None:
    result = _result(provider_metadata={})

    validation = validate_research_result(result)

    assert not validation.valid
    assert "provider_metadata is required." in _messages(validation)


def test_malformed_url_rejected() -> None:
    with pytest.raises(ResearchError, match="Invalid source_url"):
        _evidence(source_url="not-a-url")


def test_malformed_date_rejected() -> None:
    with pytest.raises(ResearchError, match="Invalid observed_date"):
        _evidence(observed_date="2026-99-99")


def test_malformed_observed_value_rejected() -> None:
    with pytest.raises(ResearchError, match="Invalid observed_value"):
        _evidence(observed_value="not-money")


def test_unsupported_currency_rejected() -> None:
    with pytest.raises(ResearchError, match="Invalid currency"):
        _evidence(currency="US")


def test_duplicate_evidence_ids_invalid() -> None:
    evidence = _evidence()
    result = _result(evidence=[evidence, evidence])

    validation = validate_research_result(result)

    assert not validation.valid
    assert "Duplicate evidence_id: ev-1" in _messages(validation)


def test_partial_result_without_warning_rejected() -> None:
    result = _result(status="PARTIAL", warnings=())

    validation = validate_research_result(result)

    assert not validation.valid
    assert "PARTIAL results must carry warnings." in _messages(validation)


def test_failed_result_with_trusted_evidence_rejected() -> None:
    result = _result(status="FAILED", evidence=[_evidence(status="COMPLETED")])

    validation = validate_research_result(result)

    assert not validation.valid
    assert "FAILED and NO_MATCH results must not contain trusted evidence." in _messages(validation)


def test_valid_json_load(tmp_path: Path) -> None:
    path = tmp_path / "research_results.json"
    path.write_text(json.dumps(_result().to_dict()), encoding="utf-8")

    loaded = ResearchJsonLoader().load(path)

    assert len(loaded.results) == 1
    assert loaded.results[0].result_id == "res-1"


def test_malformed_json_rejected(tmp_path: Path) -> None:
    path = tmp_path / "research_results.json"
    path.write_text("{bad", encoding="utf-8")

    with pytest.raises(ResearchError, match="Invalid research JSON"):
        ResearchJsonLoader().load(path)


def test_batch_load(tmp_path: Path) -> None:
    batch = ResearchBatch(
        batch_id="batch-1",
        provider_name="ChatGPT",
        results=[_result()],
        warnings=["Synthetic fixture"],
        reference_datetime=REFERENCE,
    )
    path = tmp_path / "research_results.json"
    path.write_text(json.dumps(batch.to_dict()), encoding="utf-8")

    loaded = ResearchJsonLoader().load(path)

    assert len(loaded.batches) == 1
    assert loaded.batches[0].batch_id == "batch-1"
    assert loaded.warnings == ("Synthetic fixture",)


def test_orf_evidence_to_ebay_sold_evidence_bridge() -> None:
    ebay_evidence = research_evidence_to_ebay_sold_evidence(_result(), _evidence())

    assert ebay_evidence.status == EvidenceStatus.VERIFIED
    assert ebay_evidence.provider_name == "ChatGPT"
    assert ebay_evidence.ebay_item_id == "1234567890"
    assert ebay_evidence.sold_item_url == "https://www.ebay.com/itm/1234567890"


def test_bridge_preserves_provider_metadata() -> None:
    result = _result(provider_metadata={"search_url": "https://www.ebay.com/sch/i.html?_nkw=ohtani"})

    ebay_evidence = research_evidence_to_ebay_sold_evidence(result, _evidence())

    assert ebay_evidence.raw_metadata["provider_version"] == "v1"
    assert ebay_evidence.raw_metadata["provider_metadata"]["search_url"].startswith("https://www.ebay.com")


def test_bridge_does_not_bypass_ebay_evidence_validation() -> None:
    evidence = _evidence(mismatched_fields=["GRADE"], status="COMPLETED")

    ebay_evidence = research_evidence_to_ebay_sold_evidence(_result(), evidence)

    assert ebay_evidence.status == EvidenceStatus.REJECTED
    assert "Grade Mismatch" in ebay_evidence.warnings


def test_bridge_rejects_non_sold_comparables() -> None:
    with pytest.raises(ResearchError, match="Only SOLD_COMPARABLES evidence"):
        research_evidence_to_ebay_sold_evidence(
            _result(),
            _evidence(evidence_type="VALUATION_SUPPORT"),
        )


def test_deterministic_replay() -> None:
    first = _result().to_dict()
    second = _result().to_dict()

    assert first == second


def test_no_mutation() -> None:
    result = _result()
    before = result.to_dict()

    research_evidence_to_ebay_sold_evidence(result, result.evidence[0])

    assert result.to_dict() == before


def test_private_research_files_remain_ignored_by_git() -> None:
    import subprocess

    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "check-ignore", "-q", "imports/research/research_results.json"],
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0


class FixtureResearchProvider(ResearchProvider):
    def __init__(
        self,
        name: str,
        *,
        capabilities: tuple[ResearchCapability, ...] = (
            ResearchCapability.SOLD_COMPARABLES,
            ResearchCapability.STRUCTURED_DATA,
        ),
    ) -> None:
        self._name = name
        self._capabilities = capabilities

    def provider_name(self) -> str:
        return self._name

    def provider_type(self) -> ResearchProviderType:
        return ResearchProviderType.CHATGPT

    def provider_version(self) -> str:
        return "v1"

    def capabilities(self) -> tuple[ResearchCapability, ...]:
        return self._capabilities

    def validate_request(self, request: ResearchRequest) -> bool:
        return request.research_type == ResearchType.SOLD_COMPARABLES

    def research(self, request: ResearchRequest) -> ResearchResult:
        return _result(request_id=request.request_id)


def _result(**overrides: Any) -> ResearchResult:
    payload: dict[str, Any] = {
        "result_id": "res-1",
        "request_id": "req-1",
        "provider_name": "ChatGPT",
        "provider_type": "CHATGPT",
        "provider_version": "v1",
        "capabilities": ["SOLD_COMPARABLES", "STRUCTURED_DATA"],
        "research_type": "SOLD_COMPARABLES",
        "asset_id": "PSA-12345678",
        "cert_number": "12345678",
        "status": "COMPLETED",
        "confidence": "HIGH",
        "evidence": [_evidence()],
        "normalized_payload": {"source": "fixture"},
        "warnings": (),
        "provider_metadata": {
            "network_enabled": False,
            "search_url": "https://www.ebay.com/sch/i.html?_nkw=ohtani",
        },
        "generated_at": REFERENCE,
        "reference_datetime": REFERENCE,
    }
    payload.update(overrides)
    return ResearchResult(**payload)


def _evidence(**overrides: Any) -> ResearchEvidence:
    payload: dict[str, Any] = {
        "evidence_id": "ev-1",
        "evidence_type": "SOLD_COMPARABLES",
        "source_name": "eBay Sold",
        "source_url": "https://www.ebay.com/itm/1234567890",
        "item_id": "1234567890",
        "observed_value": "250",
        "currency": "USD",
        "observed_date": "2026-07-10",
        "title": "2018 Topps Update Shohei Ohtani US1 PSA 10",
        "exact_match": True,
        "matched_fields": [
            "YEAR",
            "SET",
            "CARD_NUMBER",
            "SUBJECT",
            "GRADE_ISSUER",
            "GRADE",
        ],
        "mismatched_fields": (),
        "confidence": "HIGH",
        "status": "COMPLETED",
        "warnings": (),
        "raw_metadata": {
            "shipping_amount": "5",
            "listing_type": "AUCTION",
            "best_offer_used": False,
        },
        "created_at": REFERENCE,
    }
    payload.update(overrides)
    return ResearchEvidence(**payload)


def _messages(validation: Any) -> str:
    return "; ".join(issue.message for issue in validation.issues)
