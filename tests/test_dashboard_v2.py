from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from datetime import timezone
from decimal import Decimal

from onecool_os.dashboard import DashboardSnapshot
from onecool_os.dashboard import DashboardSnapshotBuilder
from onecool_os.portfolio import PortfolioNavStatus
from onecool_os.runtime import RuntimeSession
from onecool_os.valuation.evidence import EbaySoldEvidence
from onecool_os.valuation.evidence import EbaySoldEvidenceBatch

REFERENCE = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)


def test_dashboard_with_zero_valuation() -> None:
    snapshot = _runtime(assets=(_asset("PSA-1", "1"),)).dashboard_snapshot()

    assert isinstance(snapshot, DashboardSnapshot)
    assert snapshot.portfolio_summary["portfolio_status"] == "INSUFFICIENT_DATA"
    assert snapshot.portfolio_summary["assets_with_market_value"] == 0
    assert snapshot.nav_summary["market_value"] == "N/A"
    assert snapshot.coverage["valuation_coverage"] == "0.00%"
    assert snapshot.valuation["onecool_fair_value_count"] == 0
    assert snapshot.valuation["valuation_record_count"] == 0


def test_dashboard_with_one_valuation_and_complete_coverage() -> None:
    snapshot = _runtime(
        assets=(_asset("PSA-1", "1"),),
        batches=(_batch("PSA-1", "1", prices=("100", "200")),),
    ).dashboard_snapshot()

    assert snapshot.portfolio_summary["portfolio_status"] == "COMPLETE"
    assert snapshot.portfolio_summary["portfolio_nav_status"] == "COMPLETE"
    assert snapshot.portfolio_summary["assets_with_market_value"] == 1
    assert snapshot.coverage["valuation_coverage"] == "100.00%"
    assert snapshot.coverage["verified_coverage"] == "100.00%"
    assert snapshot.nav_summary["market_value"] == "USD 150.00"
    assert snapshot.nav_summary["coverage_note"] is None


def test_dashboard_partial_coverage() -> None:
    snapshot = _runtime(
        assets=tuple(_asset(f"PSA-{index}", str(index)) for index in range(1, 51)),
        batches=(_batch("PSA-1", "1", prices=("100", "200")),),
    ).dashboard_snapshot()

    assert snapshot.portfolio_summary["portfolio_status"] == "PARTIAL"
    assert snapshot.portfolio_summary["total_assets"] == 50
    assert snapshot.portfolio_summary["assets_with_market_value"] == 1
    assert snapshot.portfolio_summary["missing_value_assets"] == 49
    assert snapshot.coverage["valuation_coverage"] == "2.00%"
    assert snapshot.coverage["nav_coverage"] == "2.00%"
    assert "Missing assets are excluded" in snapshot.nav_summary["coverage_note"]


def test_dashboard_research_queue_section() -> None:
    snapshot = _runtime(assets=(_asset("PSA-1", "1"),)).dashboard_snapshot()

    assert snapshot.research["critical"] >= 0
    assert snapshot.research["high"] >= 0
    assert snapshot.research["medium"] >= 0
    assert snapshot.research["low"] >= 0
    assert snapshot.research["ready"] >= 0
    assert snapshot.research["blocked"] >= 0
    assert snapshot.research["completed"] >= 0
    assert len(snapshot.research["top_5_ready_assets"]) <= 5


def test_dashboard_evidence_section() -> None:
    snapshot = _runtime(
        assets=(_asset("PSA-1", "1"), _asset("PSA-2", "2")),
        batches=(
            _batch("PSA-1", "1", prices=("100", "200")),
            _status_batch("PSA-2", "2", status="REJECTED", mismatched_fields=("GRADE",)),
        ),
    ).dashboard_snapshot()

    assert snapshot.evidence["verified_evidence"] == 2
    assert snapshot.evidence["rejected"] == 1
    assert snapshot.evidence["needs_review"] == 0
    assert snapshot.evidence["no_match"] == 0
    assert snapshot.evidence["evidence_coverage"] == "100.00%"
    assert snapshot.evidence["latest_evidence_date"] == "2026-07-01"


def test_dashboard_valuation_section() -> None:
    snapshot = _runtime(
        assets=(_asset("PSA-1", "1"),),
        batches=(_batch("PSA-1", "1", prices=("100", "200")),),
    ).dashboard_snapshot()

    assert snapshot.valuation["onecool_fair_value_count"] == 1
    assert snapshot.valuation["valuation_record_count"] == 1
    assert snapshot.valuation["average_eqs"] != "N/A"
    assert snapshot.valuation["average_confidence"] == "LOW"
    assert snapshot.valuation["freshness_distribution"]["CURRENT"] == 1
    assert snapshot.valuation["liquidity_distribution"]["LOW"] == 1


def test_dashboard_top_holdings() -> None:
    snapshot = _runtime(
        assets=(_asset("PSA-1", "1"), _asset("PSA-2", "2")),
        batches=(
            _batch("PSA-1", "1", prices=("100", "200")),
            _batch("PSA-2", "2", prices=("300", "500")),
        ),
    ).dashboard_snapshot()

    assert len(snapshot.top_holdings) == 2
    assert snapshot.top_holdings[0]["asset_id"] == "PSA-2"
    assert snapshot.top_holdings[0]["fair_value"] == "USD 400.00"
    assert "roi" in snapshot.top_holdings[0]
    assert "eqs" in snapshot.top_holdings[0]


def test_dashboard_missing_valuation_sorting_core_first() -> None:
    snapshot = _runtime(
        assets=(
            _asset("PSA-B", "2", player="Beta"),
            _asset("PSA-A", "1", player="Alpha", collection_type="Core"),
        ),
    ).dashboard_snapshot()

    assert [item["asset_id"] for item in snapshot.missing_valuation] == ["PSA-A", "PSA-B"]


def test_dashboard_latest_updates_and_warnings() -> None:
    snapshot = _runtime(
        assets=(_asset("PSA-1", "1"),),
        batches=(_status_batch("PSA-1", "1", status="REJECTED", mismatched_fields=("GRADE",)),),
    ).dashboard_snapshot()

    assert len(snapshot.latest_updates) <= 10
    assert any(item["source"] == "Research" for item in snapshot.latest_updates)
    assert any(item["warning_type"] in {"Missing URL", "Low EQS"} for item in snapshot.warnings)


def test_dashboard_deterministic_ordering_and_no_mutation() -> None:
    runtime = _runtime(
        assets=(_asset("PSA-2", "2"), _asset("PSA-1", "1")),
        batches=(_batch("PSA-1", "1", prices=("100", "200")),),
    )
    assets_before = deepcopy(runtime.enriched_runtime_assets)
    evidence_before = deepcopy([batch.to_dict() for batch in runtime.ebay_sold_evidence_batches])

    first = runtime.dashboard_snapshot().to_dict()
    second = runtime.dashboard_snapshot().to_dict()

    assert first == second
    assert runtime.enriched_runtime_assets == assets_before
    assert [batch.to_dict() for batch in runtime.ebay_sold_evidence_batches] == evidence_before


def test_dashboard_builder_uses_runtime_outputs_without_recalculating(monkeypatch) -> None:
    runtime = _runtime(assets=(_asset("PSA-1", "1"),))
    calls = {"fair_value": 0, "nav": 0, "research": 0}
    original_research = RuntimeSession.build_research_queue

    def fair_value(self):
        calls["fair_value"] += 1
        return ()

    def nav(self):
        calls["nav"] += 1
        return ()

    def research(self, valuation_records=(), nav_snapshots=()):
        calls["research"] += 1
        return original_research(self, valuation_records, nav_snapshots)

    monkeypatch.setattr(RuntimeSession, "build_fair_value", fair_value)
    monkeypatch.setattr(RuntimeSession, "build_live_portfolio_nav", nav)
    monkeypatch.setattr(RuntimeSession, "build_research_queue", research)

    DashboardSnapshotBuilder().build(runtime)

    assert calls == {"fair_value": 1, "nav": 1, "research": 1}


def test_real_trial_shape_current_runtime_50_assets_zero_values() -> None:
    snapshot = _runtime(
        assets=tuple(_asset(f"PSA-{index}", str(index)) for index in range(1, 51)),
    ).dashboard_snapshot()

    assert snapshot.portfolio_summary["total_assets"] == 50
    assert snapshot.valuation["onecool_fair_value_count"] == 0
    assert snapshot.valuation["valuation_record_count"] == 0
    assert snapshot.portfolio_summary["portfolio_status"] == "INSUFFICIENT_DATA"
    assert snapshot.coverage["valuation_coverage"] == "0.00%"


def _runtime(
    *,
    assets: tuple[dict[str, str], ...],
    batches: tuple[EbaySoldEvidenceBatch, ...] = (),
) -> RuntimeSession:
    return RuntimeSession(
        imported_records=assets,
        ebay_sold_evidence_batches=batches,
        generated_at=REFERENCE,
    )


def _asset(
    asset_id: str,
    cert_number: str,
    *,
    player: str = "Shohei Ohtani",
    collection_type: str = "",
) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "cert_number": cert_number,
        "year": "2018",
        "set": "Topps",
        "card_number": "US1",
        "player": player,
        "grade_company": "PSA",
        "grade": "9",
        "currency": "USD",
        "cost": "100",
        "collection_type": collection_type,
    }


def _batch(
    asset_id: str,
    cert_number: str,
    *,
    prices: tuple[str, ...],
) -> EbaySoldEvidenceBatch:
    return EbaySoldEvidenceBatch(
        asset_id=asset_id,
        cert_number=cert_number,
        provider_name="Synthetic Fixture",
        search_url="https://www.ebay.com/sch/i.html?_nkw=synthetic&LH_Sold=1&LH_Complete=1",
        search_queries=("synthetic",),
        evidence=tuple(
            _evidence(f"{asset_id}-{index}", asset_id, cert_number, price=price)
            for index, price in enumerate(prices, start=1)
        ),
        generated_at=REFERENCE,
    )


def _status_batch(
    asset_id: str,
    cert_number: str,
    *,
    status: str,
    mismatched_fields: tuple[str, ...] = (),
) -> EbaySoldEvidenceBatch:
    return EbaySoldEvidenceBatch(
        asset_id=asset_id,
        cert_number=cert_number,
        provider_name="Synthetic Fixture",
        search_url="https://www.ebay.com/sch/i.html?_nkw=synthetic",
        search_queries=("synthetic",),
        evidence=(
            _evidence(
                f"{asset_id}-1",
                asset_id,
                cert_number,
                price="100",
                status=status,
                mismatched_fields=mismatched_fields,
            ),
        ),
        generated_at=REFERENCE,
    )


def _evidence(
    evidence_id: str,
    asset_id: str,
    cert_number: str,
    *,
    price: str,
    status: str = "VERIFIED",
    mismatched_fields: tuple[str, ...] = (),
) -> EbaySoldEvidence:
    return EbaySoldEvidence(
        evidence_id=evidence_id,
        asset_id=asset_id,
        cert_number=cert_number,
        provider_name="Synthetic Fixture",
        search_url="https://www.ebay.com/sch/i.html?_nkw=synthetic",
        sold_item_url=f"https://www.ebay.com/itm/{evidence_id}",
        ebay_item_id=evidence_id,
        title="Synthetic verified sold comparable",
        sold_price=price,
        currency="USD",
        shipping_amount="0",
        sold_date="2026-07-01",
        listing_type="AUCTION",
        best_offer_used=False,
        exact_match=True,
        matched_fields=("YEAR", "SET", "CARD_NUMBER", "SUBJECT", "GRADE_ISSUER", "GRADE"),
        mismatched_fields=mismatched_fields,
        confidence="HIGH",
        status=status,
        reference_datetime=REFERENCE,
        raw_metadata={},
        warnings=(),
    )
