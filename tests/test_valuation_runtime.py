from datetime import date
from datetime import datetime
from datetime import timezone
from pathlib import Path

from onecool_os.cli.launcher import DEFAULT_PSA_COLLECTION_PATH
from onecool_os.cli.launcher import OnecoolLauncher
from onecool_os.valuation.models import ValuationRecord

REFERENCE = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)


def test_dashboard_consumes_runtime_valuation(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_row(cert_number="PSA0001")])
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "2", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        runtime_valuation_records=[_valuation("PSA-PSA0001", "250")],
        cwd=tmp_path,
    ).run()

    assert "Estimated Market Value (if available)" in output
    assert "  USD: 250" in output
    assert "Missing Market Values: 0" in output
    assert "Cards with Performance Data: 1" in output


def test_daily_report_displays_runtime_market_value(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_row(cert_number="PSA0001")])
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "3", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        runtime_valuation_records=[_valuation("PSA-PSA0001", "250")],
        cwd=tmp_path,
    ).run()

    assert "Estimated Market Value (if available)" in output
    assert "  USD: 250" in output
    assert "Cards Missing Market Value: 0" in output
    assert "Cards with Performance Data: 1" in output


def test_decision_queue_reduces_missing_market_value(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_row(cert_number="PSA0001")])
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "4", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        runtime_valuation_records=[_valuation("PSA-PSA0001", "250")],
        cwd=tmp_path,
    ).run()

    assert "Missing Market Value: 0" in output
    assert "Missing Performance Data: 0" in output


def test_ofai_context_summarizes_valuation_coverage(tmp_path: Path) -> None:
    _write_psa_collection(
        tmp_path,
        [_row(cert_number="PSA0001"), _row(cert_number="PSA0002")],
    )
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "5", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        runtime_valuation_records=[_valuation("PSA-PSA0001", "250")],
        cwd=tmp_path,
    ).run()

    assert "Valuation Coverage: 1/2" in output
    assert "Missing Market Values: 1" in output


def test_runtime_valuation_does_not_mutate_imported_source(tmp_path: Path) -> None:
    csv_path = _write_psa_collection(tmp_path, [_row(cert_number="PSA0001")])
    before = csv_path.read_text(encoding="utf-8")

    OnecoolLauncher(
        input_func=_inputs("1", "2", "0"),
        output_func=lambda _: None,
        clock=lambda: REFERENCE,
        runtime_valuation_records=[_valuation("PSA-PSA0001", "250")],
        cwd=tmp_path,
    ).run()

    assert csv_path.read_text(encoding="utf-8") == before


def test_unrelated_runtime_valuation_is_ignored(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_row(cert_number="PSA0001")])
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "2", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        runtime_valuation_records=[_valuation("PSA-OTHER", "250")],
        cwd=tmp_path,
    ).run()

    assert "Missing Market Values: 1" in output


def _inputs(*values: str):
    iterator = iter(values)

    def _input(_: str) -> str:
        return next(iterator)

    return _input


def _valuation(asset_id: str, market_value: str) -> ValuationRecord:
    return ValuationRecord(
        valuation_id=f"runtime-{asset_id}",
        asset_id=asset_id,
        asset_type="SPORTS_CARD",
        source="MANUAL",
        currency="USD",
        valuation_date=date(2026, 7, 9),
        confidence="LOW",
        market_value=market_value,
    )


def _write_psa_collection(
    tmp_path: Path,
    rows: list[dict[str, str]],
) -> Path:
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


def _row(
    *,
    cert_number: str,
) -> dict[str, str]:
    return {
        "Item": "Demo Card Shohei Ohtani",
        "Subject": "Shohei Ohtani",
        "Year": "2018",
        "Set": "Demo Set",
        "Card Number": "1",
        "Grade Issuer": "PSA",
        "Grade": "10",
        "Cert Number": cert_number,
        "My Cost": "120.00",
        "Date Acquired": "2026-06-01",
        "Source": "PSA Collection",
        "My Notes": "Runtime valuation sample",
    }
