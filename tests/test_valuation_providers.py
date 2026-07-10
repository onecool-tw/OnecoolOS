from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from datetime import date
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any

import pytest

from onecool_os.cli.launcher import DEFAULT_PSA_COLLECTION_PATH
from onecool_os.cli.launcher import OnecoolLauncher
from onecool_os.valuation.models import ValuationRecord
from onecool_os.valuation.providers import ChatGPTValuationProvider
from onecool_os.valuation.providers import GeminiValuationProvider
from onecool_os.valuation.providers import ManualValuationProvider
from onecool_os.valuation.providers import ValuationProvider
from onecool_os.valuation.providers import ValuationProviderRegistry
from onecool_os.valuation.providers import valuation_records_from_provider

REFERENCE = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)


def test_provider_registration() -> None:
    provider = FixtureValuationProvider([_raw_record("PSA-PSA0001", "250")])
    registry = ValuationProviderRegistry()

    registry.register_provider(provider)

    assert registry.list_providers() == ("fixture",)
    assert registry.get_provider("fixture") is provider


def test_duplicate_provider_registration_rejected() -> None:
    registry = ValuationProviderRegistry()
    registry.register_provider(FixtureValuationProvider([]))

    with pytest.raises(ValueError, match="already registered"):
        registry.register_provider(FixtureValuationProvider([]))


def test_unknown_provider_lookup_rejected() -> None:
    registry = ValuationProviderRegistry()

    with pytest.raises(KeyError, match="Unknown valuation provider"):
        registry.get_provider("missing")


def test_placeholder_providers_raise_not_implemented() -> None:
    for provider in (
        GeminiValuationProvider(),
        ChatGPTValuationProvider(),
        ManualValuationProvider(),
    ):
        assert provider.provider_metadata()["network_enabled"] is False
        with pytest.raises(NotImplementedError):
            provider.search()


def test_provider_records_are_normalized_and_validated() -> None:
    provider = FixtureValuationProvider([_raw_record("PSA-PSA0001", "250")])

    records = valuation_records_from_provider(provider, {"asset_id": "PSA-PSA0001"})

    assert len(records) == 1
    assert records[0].asset_id == "PSA-PSA0001"
    assert records[0].market_value is not None
    assert provider.queries == ({"asset_id": "PSA-PSA0001"},)


def test_provider_validation_failure_rejected() -> None:
    provider = FixtureValuationProvider(
        [_raw_record("PSA-PSA0001", "250")],
        valid=False,
    )

    with pytest.raises(ValueError, match="invalid valuation record"):
        valuation_records_from_provider(provider)


def test_runtime_session_consumes_provider_records(tmp_path: Path) -> None:
    _write_psa_collection(tmp_path, [_row(cert_number="PSA0001")])
    output: list[str] = []

    OnecoolLauncher(
        input_func=_inputs("1", "2", "0"),
        output_func=output.append,
        clock=lambda: REFERENCE,
        runtime_valuation_provider=FixtureValuationProvider(
            [_raw_record("PSA-PSA0001", "250")]
        ),
        cwd=tmp_path,
    ).run()

    assert "  USD: 250" in output
    assert "Missing Market Values: 0" in output
    assert "Cards with Performance Data: 1" in output


def test_runtime_provider_injection_does_not_mutate_source(
    tmp_path: Path,
) -> None:
    csv_path = _write_psa_collection(tmp_path, [_row(cert_number="PSA0001")])
    before = csv_path.read_text(encoding="utf-8")

    OnecoolLauncher(
        input_func=_inputs("1", "2", "0"),
        output_func=lambda _: None,
        clock=lambda: REFERENCE,
        runtime_valuation_provider=FixtureValuationProvider(
            [_raw_record("PSA-PSA0001", "250")]
        ),
        cwd=tmp_path,
    ).run()

    assert csv_path.read_text(encoding="utf-8") == before


def test_provider_loading_is_deterministic() -> None:
    provider = FixtureValuationProvider(
        [
            _raw_record("PSA-PSA0002", "180"),
            _raw_record("PSA-PSA0001", "250"),
        ]
    )

    first = valuation_records_from_provider(provider)
    second = valuation_records_from_provider(provider)

    assert [record.to_dict() for record in first] == [
        record.to_dict() for record in second
    ]


class FixtureValuationProvider(ValuationProvider):
    def __init__(
        self,
        records: Sequence[Mapping[str, str]],
        *,
        valid: bool = True,
    ) -> None:
        self._records = tuple(dict(record) for record in records)
        self._valid = valid
        self.queries: tuple[Mapping[str, Any] | None, ...] = ()

    def source_name(self) -> str:
        return "fixture"

    def provider_metadata(self) -> Mapping[str, Any]:
        return {
            "provider": "Fixture Valuation Provider",
            "network_enabled": False,
        }

    def search(
        self,
        query: Mapping[str, Any] | None = None,
    ) -> Sequence[Mapping[str, str]]:
        self.queries = self.queries + (dict(query) if query else None,)
        return self._records

    def normalize(self, raw_record: Mapping[str, str]) -> ValuationRecord:
        return ValuationRecord(
            valuation_id=f"fixture-{raw_record['asset_id']}",
            asset_id=raw_record["asset_id"],
            asset_type="SPORTS_CARD",
            source="MANUAL",
            currency=raw_record["currency"],
            valuation_date=date(2026, 7, 9),
            confidence="LOW",
            market_value=raw_record["market_value"],
        )

    def validate(self, valuation_record: ValuationRecord) -> bool:
        return self._valid and isinstance(valuation_record, ValuationRecord)


def _raw_record(asset_id: str, market_value: str) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "currency": "USD",
        "market_value": market_value,
    }


def _inputs(*values: str):
    iterator = iter(values)

    def _input(_: str) -> str:
        return next(iterator)

    return _input


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
        "My Notes": "Runtime provider sample",
    }
