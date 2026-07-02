from datetime import datetime, timezone
from typing import Any

from onecool_os.connectors.normalize import (
    BaseNormalizer,
    NormalizationError,
    NormalizedRecord,
)


class DemoNormalizer(BaseNormalizer):
    def source_name(self) -> str:
        return "demo"

    def normalize(self, raw_record: dict[str, Any]) -> NormalizedRecord:
        return NormalizedRecord(
            external_source=self.source_name(),
            external_id=str(raw_record["id"]),
            record_type="demo.record",
            payload={
                "name": raw_record["name"],
            },
            raw_payload=raw_record,
        )


def test_normalized_record_creation() -> None:
    normalized_at = datetime(2026, 7, 2, tzinfo=timezone.utc)

    record = NormalizedRecord(
        external_source="psa",
        external_id="12345678",
        record_type="sports_card",
        payload={"player": "Shohei Ohtani"},
        raw_payload={"Cert Number": "12345678"},
        normalized_at=normalized_at,
    )

    assert record.external_source == "psa"
    assert record.external_id == "12345678"
    assert record.record_type == "sports_card"
    assert record.payload["player"] == "Shohei Ohtani"
    assert record.raw_payload == {"Cert Number": "12345678"}
    assert record.normalized_at == normalized_at


def test_normalized_record_rejects_invalid_required_fields() -> None:
    try:
        NormalizedRecord(
            external_source="",
            external_id="123",
            record_type="sports_card",
            payload={},
        )
    except NormalizationError as exc:
        assert "external_source" in str(exc)
    else:
        raise AssertionError("Invalid external_source should be rejected.")


def test_normalized_record_rejects_invalid_payload() -> None:
    try:
        NormalizedRecord(
            external_source="psa",
            external_id="123",
            record_type="sports_card",
            payload="not-a-dict",
        )
    except NormalizationError as exc:
        assert "payload" in str(exc)
    else:
        raise AssertionError("Invalid payload should be rejected.")


def test_base_normalizer_interface() -> None:
    normalizer = DemoNormalizer()
    record = normalizer.normalize({"id": "1", "name": "Sample"})

    assert isinstance(normalizer, BaseNormalizer)
    assert normalizer.source_name() == "demo"
    assert record.external_source == "demo"


def test_base_normalizer_validate_accepts_matching_source() -> None:
    normalizer = DemoNormalizer()
    record = normalizer.normalize({"id": "1", "name": "Sample"})

    normalizer.validate(record)


def test_base_normalizer_validate_rejects_mismatched_source() -> None:
    normalizer = DemoNormalizer()
    record = NormalizedRecord(
        external_source="other",
        external_id="1",
        record_type="demo.record",
        payload={},
    )

    try:
        normalizer.validate(record)
    except NormalizationError as exc:
        assert "external_source" in str(exc)
    else:
        raise AssertionError("Mismatched external source should be rejected.")


def test_basic_normalize_flow() -> None:
    normalizer = DemoNormalizer()
    raw_record = {"id": "abc", "name": "Demo Asset"}

    record = normalizer.normalize(raw_record)
    normalizer.validate(record)

    assert record.external_id == "abc"
    assert record.record_type == "demo.record"
    assert record.payload == {"name": "Demo Asset"}
    assert record.raw_payload == raw_record
