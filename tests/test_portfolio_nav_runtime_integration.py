from __future__ import annotations

from copy import deepcopy
from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal
from pathlib import Path

from onecool_os.cli.launcher import DEFAULT_PSA_COLLECTION_PATH
from onecool_os.cli.launcher import OnecoolLauncher
from onecool_os.connectors.collectibles import PSACollectionImporter
from onecool_os.dashboard import portfolio_nav_lines
from onecool_os.dashboard import portfolio_nav_sections
from onecool_os.portfolio import PortfolioNavEngine
from onecool_os.portfolio import PortfolioNavStatus
from onecool_os.runtime import RuntimeSession
from onecool_os.valuation.evidence import EbaySoldEvidence
from onecool_os.valuation.evidence import EbaySoldEvidenceBatch
from onecool_os.valuation.models import ValuationRecord

REFERENCE = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)


def test_zero_evidence_produces_zero_valuation_records_and_insufficient_nav() -> None:
    runtime = RuntimeSession(
        imported_records=(_asset("PSA-1", "1"),),
        generated_at=REFERENCE,
    )

    valuation_records = runtime.build_valuation_records()
    snapshots = runtime.build_live_portfolio_nav()

    assert valuation_records == ()
    assert snapshots[0].status == PortfolioNavStatus.INSUFFICIENT_DATA
    assert snapshots[0].assets_with_market_value == 0
    assert snapshots[0].total_market_value == Decimal("0.00")


def test_one_verified_asset_flows_evidence_to_fair_value_to_nav() -> None:
    runtime = _runtime_with_evidence(
        assets=(_asset("PSA-1", "1"),),
        batches=(_verified_batch("PSA-1", "1", prices=("100", "200")),),
    )

    fair_values = runtime.build_fair_value()
    valuation_records = runtime.build_valuation_records()
    snapshots = runtime.build_live_portfolio_nav()

    assert fair_values[0].fair_value == Decimal("150")
    assert valuation_records[0].source.value == "ONECOOL_FAIR_VALUE"
    assert valuation_records[0].market_value == Decimal("150")
    assert snapshots[0].status == PortfolioNavStatus.COMPLETE
    assert snapshots[0].assets_with_market_value == 1
    assert snapshots[0].verified_assets == 1
    assert snapshots[0].total_market_value == Decimal("150.00")


def test_one_valued_asset_in_50_produces_partial_two_percent_coverage() -> None:
    runtime = _runtime_with_evidence(
        assets=tuple(_asset(f"PSA-{index}", str(index)) for index in range(1, 51)),
        batches=(_verified_batch("PSA-1", "1", prices=("100", "200")),),
    )

    snapshot = runtime.build_live_portfolio_nav()[0]

    assert snapshot.total_assets == 50
    assert snapshot.assets_with_market_value == 1
    assert snapshot.missing_value_assets == 49
    assert snapshot.valuation_coverage_percent == Decimal("2.0000")
    assert snapshot.verified_coverage_percent == Decimal("2.0000")
    assert snapshot.status == PortfolioNavStatus.PARTIAL
    assert snapshot.total_market_value == Decimal("150.00")


def test_multiple_verified_assets_and_multiple_currencies_remain_separate() -> None:
    runtime = _runtime_with_evidence(
        assets=(
            _asset("PSA-1", "1", currency="USD"),
            _asset("PSA-2", "2", currency="TWD"),
        ),
        batches=(
            _verified_batch("PSA-1", "1", prices=("100", "200"), currency="USD"),
            _verified_batch("PSA-2", "2", prices=("1000", "2000"), currency="TWD"),
        ),
    )

    snapshots = runtime.build_live_portfolio_nav()

    assert [snapshot.currency for snapshot in snapshots] == ["TWD", "USD"]
    assert {snapshot.currency: snapshot.total_market_value for snapshot in snapshots} == {
        "USD": Decimal("150.00"),
        "TWD": Decimal("1500.00"),
    }


def test_insufficient_review_rejected_and_no_match_evidence_are_excluded() -> None:
    runtime = _runtime_with_evidence(
        assets=(
            _asset("PSA-1", "1"),
            _asset("PSA-2", "2"),
            _asset("PSA-3", "3"),
            _asset("PSA-4", "4"),
        ),
        batches=(
            _review_batch("PSA-1", "1"),
            _status_batch("PSA-2", "2", status="REJECTED", mismatched_fields=("GRADE",)),
            _status_batch("PSA-3", "3", status="NO_MATCH"),
        ),
    )

    assert runtime.build_valuation_records() == ()
    snapshot = runtime.build_live_portfolio_nav()[0]
    assert snapshot.assets_with_market_value == 0
    assert snapshot.status == PortfolioNavStatus.INSUFFICIENT_DATA


def test_duplicate_canonical_records_resolved_by_latest_date_and_warning() -> None:
    snapshot = PortfolioNavEngine().build_snapshots(
        (_asset("PSA-1", "1"),),
        (
            _valuation("onecool-a", "PSA-1", "100", valuation_date=date(2026, 7, 1)),
            _valuation("onecool-b", "PSA-1", "200", valuation_date=date(2026, 7, 2)),
        ),
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )[0]

    line = snapshot.asset_lines[0]
    assert line.market_value == Decimal("200")
    assert line.valuation_record_id == "onecool-b"
    assert "Multiple Eligible Valuation Records" in line.warnings


def test_duplicate_canonical_records_tie_break_by_record_id() -> None:
    snapshot = PortfolioNavEngine().build_snapshots(
        (_asset("PSA-1", "1"),),
        (
            _valuation("onecool-a", "PSA-1", "100"),
            _valuation("onecool-z", "PSA-1", "200"),
        ),
        reference_datetime=REFERENCE,
        generated_at=REFERENCE,
    )[0]

    assert snapshot.asset_lines[0].valuation_record_id == "onecool-z"
    assert snapshot.asset_lines[0].market_value == Decimal("200")


def test_supporting_estimates_are_not_used_by_live_runtime_nav() -> None:
    runtime = RuntimeSession(
        imported_records=(_asset("PSA-1", "1"),),
        generated_at=REFERENCE,
    )
    manual = _valuation("manual", "PSA-1", "999", source="MANUAL")

    legacy_snapshot = runtime.build_portfolio_nav((manual,))[0]
    live_snapshot = runtime.build_live_portfolio_nav()[0]

    assert legacy_snapshot.estimated_assets == 1
    assert legacy_snapshot.assets_with_market_value == 1
    assert live_snapshot.estimated_assets == 0
    assert live_snapshot.assets_with_market_value == 0


def test_missing_market_values_are_not_treated_as_zero() -> None:
    runtime = _runtime_with_evidence(
        assets=(
            _asset("PSA-1", "1", cost="100"),
            _asset("PSA-2", "2", cost="900"),
        ),
        batches=(_verified_batch("PSA-1", "1", prices=("100", "200")),),
    )

    snapshot = runtime.build_live_portfolio_nav()[0]

    assert snapshot.total_cost_basis == Decimal("1000.00")
    assert snapshot.total_market_value == Decimal("150.00")
    assert snapshot.missing_value_assets == 1


def test_dashboard_consumes_snapshot_and_discloses_partial_coverage() -> None:
    runtime = _runtime_with_evidence(
        assets=tuple(_asset(f"PSA-{index}", str(index)) for index in range(1, 51)),
        batches=(_verified_batch("PSA-1", "1", prices=("100", "200")),),
    )
    snapshot = runtime.build_live_portfolio_nav()[0]

    lines = "\n".join(portfolio_nav_lines((snapshot,)))
    sections = portfolio_nav_sections((snapshot,))

    assert "Status: PARTIAL" in lines
    assert "Valuation Coverage: 2.00%" in lines
    assert "Portfolio market value reflects valued assets only" in lines
    assert sections[0].content["coverage_note"].startswith("Portfolio market value")


def test_cli_reuses_runtime_session_live_nav(monkeypatch, tmp_path: Path) -> None:
    csv_path = _write_psa_collection(tmp_path, [_row(cert_number="PSA0001")])
    output: list[str] = []
    calls = {"live_nav": 0}

    def fake_live_nav(self):
        calls["live_nav"] += 1
        return ()

    monkeypatch.setattr(RuntimeSession, "build_live_portfolio_nav", fake_live_nav)

    OnecoolLauncher(
        input_func=_inputs("1", "2", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        cwd=tmp_path,
    ).run()

    assert calls["live_nav"] == 1
    assert csv_path.read_text(encoding="utf-8").startswith("Item,Subject")


def test_no_mutation_and_deterministic_replay() -> None:
    runtime = _runtime_with_evidence(
        assets=(_asset("PSA-1", "1"),),
        batches=(_verified_batch("PSA-1", "1", prices=("100", "200")),),
    )
    evidence_before = deepcopy([batch.to_dict() for batch in runtime.ebay_sold_evidence_batches])
    assets_before = deepcopy(runtime.enriched_runtime_assets)
    first = [snapshot.to_dict() for snapshot in runtime.build_live_portfolio_nav()]
    second = [snapshot.to_dict() for snapshot in runtime.build_live_portfolio_nav()]

    assert [batch.to_dict() for batch in runtime.ebay_sold_evidence_batches] == evidence_before
    assert runtime.enriched_runtime_assets == assets_before
    assert first == second


def test_synthetic_kobe_e2e_trial() -> None:
    runtime = _runtime_with_evidence(
        assets=tuple(
            [_asset("PSA-111003720", "111003720", player="KOBE BRYANT", year="2008", card_number="24")]
            + [_asset(f"PSA-{index}", str(index)) for index in range(1, 50)]
        ),
        batches=(_verified_batch("PSA-111003720", "111003720", prices=("80", "120")),),
    )

    snapshot = runtime.build_live_portfolio_nav()[0]

    assert len(runtime.enriched_runtime_assets) == 50
    assert runtime.build_valuation_records()[0].source.value == "ONECOOL_FAIR_VALUE"
    assert snapshot.assets_with_market_value == 1
    assert snapshot.total_assets == 50
    assert snapshot.status == PortfolioNavStatus.PARTIAL


def _runtime_with_evidence(
    *,
    assets: tuple[dict[str, str], ...],
    batches: tuple[EbaySoldEvidenceBatch, ...],
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
    currency: str = "USD",
    cost: str = "100",
    player: str = "Shohei Ohtani",
    year: str = "2018",
    card_number: str = "US1",
) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "cert_number": cert_number,
        "year": year,
        "set": "Topps",
        "card_number": card_number,
        "player": player,
        "grade_company": "PSA",
        "grade": "9",
        "currency": currency,
        "cost": cost,
    }


def _verified_batch(
    asset_id: str,
    cert_number: str,
    *,
    prices: tuple[str, ...],
    currency: str = "USD",
) -> EbaySoldEvidenceBatch:
    return EbaySoldEvidenceBatch(
        asset_id=asset_id,
        cert_number=cert_number,
        provider_name="Synthetic Fixture",
        search_url="https://www.ebay.com/sch/i.html?_nkw=synthetic&LH_Sold=1&LH_Complete=1",
        search_queries=("synthetic",),
        evidence=tuple(
            _evidence(
                f"{asset_id}-{index}",
                asset_id,
                cert_number,
                price=price,
                currency=currency,
            )
            for index, price in enumerate(prices, start=1)
        ),
        generated_at=REFERENCE,
    )


def _review_batch(asset_id: str, cert_number: str) -> EbaySoldEvidenceBatch:
    return EbaySoldEvidenceBatch(
        asset_id=asset_id,
        cert_number=cert_number,
        provider_name="Synthetic Fixture",
        search_url="https://www.ebay.com/sch/i.html?_nkw=synthetic",
        search_queries=("synthetic",),
        evidence=(
            _evidence(f"{asset_id}-1", asset_id, cert_number, price="100"),
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
    currency: str = "USD",
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
        currency=currency,
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


def _valuation(
    valuation_id: str,
    asset_id: str,
    value: str,
    *,
    source: str = "ONECOOL_FAIR_VALUE",
    currency: str = "USD",
    valuation_date: date = date(2026, 7, 1),
) -> ValuationRecord:
    return ValuationRecord(
        valuation_id=valuation_id,
        asset_id=asset_id,
        asset_type="SPORTS_CARD",
        source=source,
        currency=currency,
        valuation_date=valuation_date,
        confidence="HIGH",
        market_value=value,
    )


def _write_psa_collection(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    csv_path = tmp_path / DEFAULT_PSA_COLLECTION_PATH
    csv_path.parent.mkdir(parents=True)
    columns = (
        "Item",
        "Subject",
        "Year",
        "Set",
        "Card Number",
        "Grade Issuer",
        "Grade",
        "Cert Number",
        "My Cost",
        "Date Acquired",
        "Source",
        "My Notes",
    )
    lines = [",".join(columns)]
    for row in rows:
        lines.append(",".join(row[column] for column in columns))
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path


def _row(*, cert_number: str) -> dict[str, str]:
    return {
        "Item": "Synthetic Card",
        "Subject": "Synthetic Player",
        "Year": "2020",
        "Set": "Synthetic Set",
        "Card Number": "1",
        "Grade Issuer": "PSA",
        "Grade": "9",
        "Cert Number": cert_number,
        "My Cost": "100",
        "Date Acquired": "2026-01-01",
        "Source": "Synthetic Test",
        "My Notes": "private note must not be printed",
    }


def _inputs(*values: str):
    iterator = iter(values)

    def _input(_: str) -> str:
        return next(iterator)

    return _input
