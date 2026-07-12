from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal
from pathlib import Path

import pytest

from onecool_os.cli.main import main
from onecool_os.history import HistoryRecordStatus
from onecool_os.history import HistoryWriteStatus
from onecool_os.history import PortfolioHistoryError
from onecool_os.history import PortfolioHistorySnapshot
from onecool_os.history import PortfolioHistorySnapshotBuilder
from onecool_os.history import PortfolioHistoryStore
from onecool_os.history import read_snapshot_json
from onecool_os.history import snapshot_checksum
from onecool_os.runtime import RuntimeSession
from onecool_os.valuation.evidence import EbaySoldEvidence
from onecool_os.valuation.evidence import EbaySoldEvidenceBatch

REFERENCE = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)
TAIPEI_REFERENCE = datetime(2026, 7, 11, 17, 0, tzinfo=timezone.utc)


def test_empty_portfolio_snapshot() -> None:
    snapshot = RuntimeSession(generated_at=REFERENCE).portfolio_history_snapshot(
        reference_datetime=REFERENCE,
    )

    assert snapshot.total_assets == 0
    assert snapshot.fair_value_count == 0
    assert snapshot.valuation_record_count == 0
    assert snapshot.status == HistoryRecordStatus.INSUFFICIENT_DATA
    assert snapshot.reference_datetime.isoformat().endswith("+08:00")


def test_real_trial_shape_current_runtime_50_assets_zero_values() -> None:
    snapshot = _runtime(
        assets=tuple(_asset(f"PSA-{index}", str(index)) for index in range(1, 51)),
    ).portfolio_history_snapshot(reference_datetime=REFERENCE)

    assert snapshot.total_assets == 50
    assert snapshot.fair_value_count == 0
    assert snapshot.valuation_record_count == 0
    assert snapshot.valuation_coverage_percent == Decimal("0.0000")
    assert snapshot.missing_value_assets == 50
    assert snapshot.status == HistoryRecordStatus.INSUFFICIENT_DATA


def test_one_valued_asset_snapshot_partial_coverage() -> None:
    snapshot = _runtime(
        assets=tuple(_asset(f"PSA-{index}", str(index)) for index in range(1, 51)),
        batches=(_batch("PSA-1", "1", prices=("100", "200")),),
    ).portfolio_history_snapshot(reference_datetime=REFERENCE)

    assert snapshot.fair_value_count == 1
    assert snapshot.valuation_record_count == 1
    assert snapshot.valuation_coverage_percent == Decimal("2.0000")
    assert snapshot.missing_value_assets == 49
    assert snapshot.status == HistoryRecordStatus.PARTIAL


def test_complete_valuation_coverage() -> None:
    snapshot = _runtime(
        assets=(_asset("PSA-1", "1"),),
        batches=(_batch("PSA-1", "1", prices=("100", "200")),),
    ).portfolio_history_snapshot(reference_datetime=REFERENCE)

    assert snapshot.status == HistoryRecordStatus.COMPLETE
    assert snapshot.nav_status_by_currency == {"USD": "COMPLETE"}
    assert snapshot.total_market_value_by_currency["USD"] == Decimal("150.00")
    assert snapshot.asset_lines[0].market_value == Decimal("150.00")


def test_multiple_currencies_are_preserved() -> None:
    snapshot = _runtime(
        assets=(_asset("PSA-1", "1"), _asset("BGS-1", "2", currency="TWD")),
    ).portfolio_history_snapshot(reference_datetime=REFERENCE)

    assert snapshot.currencies == ("TWD", "USD")
    assert sorted(snapshot.nav_status_by_currency) == ["TWD", "USD"]


def test_decimal_serialization_and_timezone_preservation() -> None:
    snapshot = _runtime(
        assets=(_asset("PSA-1", "1"),),
        batches=(_batch("PSA-1", "1", prices=("100", "200")),),
    ).portfolio_history_snapshot(reference_datetime=REFERENCE)
    payload = snapshot.to_dict()

    assert payload["total_market_value_by_currency"]["USD"] == "150"
    assert payload["reference_datetime"].endswith("+08:00")
    assert payload["asset_lines"][0]["market_value"] == "150"


def test_immutable_models() -> None:
    snapshot = _runtime(assets=(_asset("PSA-1", "1"),)).portfolio_history_snapshot(
        reference_datetime=REFERENCE,
    )

    with pytest.raises(FrozenInstanceError):
        snapshot.total_assets = 99


def test_deterministic_fingerprint_and_checksum() -> None:
    runtime = _runtime(
        assets=(_asset("PSA-2", "2"), _asset("PSA-1", "1")),
        batches=(_batch("PSA-1", "1", prices=("100", "200")),),
    )

    first = runtime.portfolio_history_snapshot(reference_datetime=REFERENCE)
    second = runtime.portfolio_history_snapshot(reference_datetime=REFERENCE)

    assert first.to_dict() == second.to_dict()
    assert first.fingerprint == second.fingerprint
    assert snapshot_checksum(first) == snapshot_checksum(second)


def test_store_append_duplicate_index_latest_and_queries(tmp_path) -> None:
    snapshot = _runtime(assets=(_asset("PSA-1", "1"),)).portfolio_history_snapshot(
        reference_datetime=REFERENCE,
    )
    store = PortfolioHistoryStore(tmp_path)

    first = store.write_snapshot(snapshot)
    second = store.write_snapshot(snapshot)

    assert first.status == HistoryWriteStatus.CREATED
    assert second.status == HistoryWriteStatus.DUPLICATE
    assert len(store.list_snapshots()) == 1
    assert store.latest_snapshot().history_snapshot_id == snapshot.history_snapshot_id
    assert store.snapshot_exists(snapshot.fingerprint)
    assert store.snapshots_between(date(2026, 7, 11), date(2026, 7, 11))[0] == snapshot
    assert store.snapshots_for_currency("USD")[0] == snapshot


def test_same_date_different_snapshot_is_preserved(tmp_path) -> None:
    store = PortfolioHistoryStore(tmp_path)
    first = _runtime(assets=(_asset("PSA-1", "1"),)).portfolio_history_snapshot(
        reference_datetime=REFERENCE,
    )
    second = _runtime(
        assets=(_asset("PSA-1", "1"), _asset("PSA-2", "2")),
    ).portfolio_history_snapshot(reference_datetime=REFERENCE)

    assert store.write_snapshot(first).status == HistoryWriteStatus.CREATED
    assert store.write_snapshot(second).status == HistoryWriteStatus.CREATED
    assert len(store.list_snapshots()) == 2


def test_same_id_different_checksum_is_rejected_without_force(tmp_path) -> None:
    store = PortfolioHistoryStore(tmp_path)
    snapshot = _runtime(assets=(_asset("PSA-1", "1"),)).portfolio_history_snapshot(
        reference_datetime=REFERENCE,
    )
    altered = PortfolioHistorySnapshot(
        **{
            **snapshot.to_dict(),
            "warning_count": 1,
            "warnings": ["Manual warning"],
        }
    )

    assert store.write_snapshot(snapshot).status == HistoryWriteStatus.CREATED
    result = store.write_snapshot(altered)

    assert result.status == HistoryWriteStatus.REJECTED
    assert len(store.list_snapshots()) == 1


def test_checksum_validation_rejects_tampered_file(tmp_path) -> None:
    snapshot = _runtime(assets=(_asset("PSA-1", "1"),)).portfolio_history_snapshot(
        reference_datetime=REFERENCE,
    )
    result = PortfolioHistoryStore(tmp_path).write_snapshot(snapshot)
    path = tmp_path / result.file_path if not str(result.file_path).startswith("/") else result.file_path
    payload = json.loads(open(path, encoding="utf-8").read())
    payload["snapshot"]["total_assets"] = 99
    open(path, "w", encoding="utf-8").write(json.dumps(payload))

    with pytest.raises(PortfolioHistoryError, match="checksum"):
        read_snapshot_json(Path(path))


def test_malformed_and_invalid_snapshots_are_rejected() -> None:
    snapshot = _runtime(assets=(_asset("PSA-1", "1"),)).portfolio_history_snapshot(
        reference_datetime=REFERENCE,
    ).to_dict()

    with pytest.raises(PortfolioHistoryError, match="Unsupported schema"):
        PortfolioHistorySnapshot(**{**snapshot, "schema_version": "2.0"})
    with pytest.raises(PortfolioHistoryError, match="duplicate asset"):
        PortfolioHistorySnapshot(
            **{
                **snapshot,
                "total_assets": 2,
                "asset_lines": snapshot["asset_lines"] * 2,
            }
        )
    with pytest.raises(PortfolioHistoryError, match="between 0 and 100"):
        PortfolioHistorySnapshot(**{**snapshot, "valuation_coverage_percent": "101"})
    with pytest.raises(PortfolioHistoryError, match="total_assets"):
        PortfolioHistorySnapshot(**{**snapshot, "total_assets": 2})


def test_builder_does_not_mutate_runtime() -> None:
    runtime = _runtime(
        assets=(_asset("PSA-1", "1"),),
        batches=(_batch("PSA-1", "1", prices=("100", "200")),),
    )
    assets_before = deepcopy(runtime.enriched_runtime_assets)
    batches_before = deepcopy([batch.to_dict() for batch in runtime.ebay_sold_evidence_batches])

    PortfolioHistorySnapshotBuilder().build(runtime, reference_datetime=REFERENCE)

    assert runtime.enriched_runtime_assets == assets_before
    assert [batch.to_dict() for batch in runtime.ebay_sold_evidence_batches] == batches_before


def test_private_history_path_is_gitignored() -> None:
    gitignore = open(".gitignore", encoding="utf-8").read()

    assert "data/*" in gitignore


def test_cli_record_portfolio_snapshot(tmp_path, monkeypatch, capsys) -> None:
    imports = tmp_path / "imports" / "psa"
    imports.mkdir(parents=True)
    (imports / "collection.csv").write_text(
        "\n".join(
            [
                "Item,Subject,Year,Set,Card Number,Grade Issuer,Grade,Cert Number,My Cost,Date Acquired,Source,My Notes",
                "2018 Topps Shohei Ohtani,Shohei Ohtani,2018,Topps,US1,PSA,10,12345678,100,2026-01-01,Demo,private note",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    status = main(
        [
            "record-portfolio-snapshot",
            "--reference-datetime",
            TAIPEI_REFERENCE.isoformat(),
            "--output-root",
            str(tmp_path / "history"),
        ]
    )
    output = capsys.readouterr().out

    assert status == 0
    assert "Onecool Portfolio History Snapshot" in output
    assert "Total Assets: 1" in output
    assert "Write Status: CREATED" in output
    assert "private note" not in output


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
    currency: str = "USD",
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
        "currency": currency,
        "cost": "100",
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


def _evidence(
    evidence_id: str,
    asset_id: str,
    cert_number: str,
    *,
    price: str,
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
        mismatched_fields=(),
        confidence="HIGH",
        status="VERIFIED",
        reference_datetime=REFERENCE,
        raw_metadata={},
        warnings=(),
    )
