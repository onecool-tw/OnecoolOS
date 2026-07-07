from copy import deepcopy
from datetime import datetime
from datetime import timezone
from decimal import Decimal

from onecool_os.valuation import SourceAgreementBuilder
from onecool_os.valuation import SourceAgreementLevel
from onecool_os.valuation import ValuationRecord


REFERENCE = datetime(2026, 7, 6, tzinfo=timezone.utc)


def test_source_agreement_strong_agreement() -> None:
    result = build(primary="250", card_ladder="255")

    assert result.agreement_level == SourceAgreementLevel.STRONG
    assert result.agreement_score == 98
    assert result.agreement_spread == Decimal("0.02")
    assert result.max_divergence == Decimal("0.02")
    assert "Source Conflict" not in result.warnings


def test_source_agreement_good_agreement() -> None:
    result = build(primary="250", card_ladder="275")

    assert result.agreement_level == SourceAgreementLevel.GOOD
    assert result.agreement_score == 90
    assert result.agreement_spread == Decimal("0.10")


def test_source_agreement_fair_agreement() -> None:
    result = build(primary="250", card_ladder="300")

    assert result.agreement_level == SourceAgreementLevel.FAIR
    assert result.agreement_score == 80
    assert result.agreement_spread == Decimal("0.20")


def test_source_agreement_weak_agreement() -> None:
    result = build(primary="250", card_ladder="337.50")

    assert result.agreement_level == SourceAgreementLevel.WEAK
    assert result.agreement_score == 65
    assert "Source Agreement Weak" in result.warnings


def test_source_agreement_conflict() -> None:
    result = build(primary="250", card_ladder="410")

    assert result.agreement_level == SourceAgreementLevel.CONFLICT
    assert result.agreement_score == 36
    assert result.agreement_spread == Decimal("0.64")
    assert "Source Conflict" in result.warnings
    assert "High Divergence" in result.warnings


def test_source_agreement_missing_primary_market_price() -> None:
    result = SourceAgreementBuilder().build(
        [valuation("CARD_LADDER", "255", valuation_id="cl-1")],
        reference_datetime=REFERENCE,
        asset_id="card-1",
    )

    assert result.primary_market_price is None
    assert result.agreement_level == SourceAgreementLevel.UNKNOWN
    assert result.agreement_score == 0
    assert "Missing Primary Market Price" in result.warnings


def test_source_agreement_missing_validation_sources() -> None:
    result = SourceAgreementBuilder().build(
        [valuation("EBAY_SOLD", "250", valuation_id="ebay-1")],
        reference_datetime=REFERENCE,
        asset_id="card-1",
    )

    assert result.agreement_level == SourceAgreementLevel.UNKNOWN
    assert result.validation_sources == {}
    assert "Validation Sources Missing" in result.warnings
    assert "Low Source Count" in result.warnings


def test_source_agreement_multiple_validation_sources() -> None:
    records = [
        valuation("EBAY_SOLD", "250", valuation_id="ebay-1"),
        valuation("CARD_LADDER", "255", valuation_id="cl-1"),
        valuation("MANUAL", "260", valuation_id="manual-1"),
        valuation("PWCC", "245", valuation_id="pwcc-1"),
    ]

    result = SourceAgreementBuilder().build(
        records,
        reference_datetime=REFERENCE,
    )

    assert result.source_count == 4
    assert result.participating_sources == (
        "EBAY_SOLD",
        "CARD_LADDER",
        "MANUAL",
        "PWCC",
    )
    assert result.validation_sources == {
        "CARD_LADDER": Decimal("255"),
        "MANUAL": Decimal("260"),
        "PWCC": Decimal("245"),
    }
    assert result.agreement_level == SourceAgreementLevel.STRONG


def test_source_agreement_missing_sources() -> None:
    result = build(primary="250", card_ladder="255")

    assert result.missing_sources == (
        "MANUAL",
        "PWCC",
        "GOLDIN",
        "FANATICS",
    )


def test_source_agreement_uses_latest_source_record() -> None:
    records = [
        valuation(
            "EBAY_SOLD",
            "250",
            valuation_id="ebay-old",
            valuation_date="2026-07-01",
        ),
        valuation(
            "EBAY_SOLD",
            "300",
            valuation_id="ebay-new",
            valuation_date="2026-07-03",
        ),
        valuation("CARD_LADDER", "315", valuation_id="cl-1"),
    ]

    result = SourceAgreementBuilder().build(
        records,
        reference_datetime=REFERENCE,
    )

    assert result.primary_market_price == Decimal("300")
    assert result.agreement_spread == Decimal("0.05")
    assert result.agreement_level == SourceAgreementLevel.STRONG


def test_source_agreement_to_dict_formats_values() -> None:
    payload = build(primary="250", card_ladder="255").to_dict()

    assert payload["primary_market_price"] == "250.00"
    assert payload["validation_sources"]["CARD_LADDER"] == "255.00"
    assert payload["agreement_spread"] == "2.00"
    assert payload["max_divergence"] == "2.00"


def test_source_agreement_accepts_mapping_compatible_records() -> None:
    record = valuation("EBAY_SOLD", "250", valuation_id="ebay-1")
    compatible = {
        "valuation_id": "cl-1",
        "asset_id": "card-1",
        "asset_type": "SPORTS_CARD",
        "source": "CARD_LADDER",
        "currency": "USD",
        "valuation_date": "2026-07-04",
        "confidence": "LOW",
        "market_value": "255",
    }

    result = SourceAgreementBuilder().build(
        [record, compatible],
        reference_datetime=REFERENCE,
    )

    assert result.agreement_level == SourceAgreementLevel.STRONG


def test_source_agreement_no_mutation() -> None:
    records = [
        valuation("EBAY_SOLD", "250", valuation_id="ebay-1"),
        valuation("CARD_LADDER", "255", valuation_id="cl-1"),
    ]
    before = deepcopy([record.to_dict() for record in records])

    SourceAgreementBuilder().build(records, reference_datetime=REFERENCE)

    assert [record.to_dict() for record in records] == before


def test_source_agreement_injected_reference_datetime() -> None:
    reference = datetime(2026, 8, 1, tzinfo=timezone.utc)

    result = build(primary="250", card_ladder="255", reference=reference)

    assert result.generated_at == reference
    assert result.reference_datetime == reference


def test_source_agreement_deterministic_replay() -> None:
    records = [
        valuation("EBAY_SOLD", "250", valuation_id="ebay-1"),
        valuation("CARD_LADDER", "255", valuation_id="cl-1"),
    ]
    builder = SourceAgreementBuilder()

    first = builder.build(records, reference_datetime=REFERENCE).to_dict()
    second = builder.build(records, reference_datetime=REFERENCE).to_dict()

    assert first == second


def build(
    *,
    primary: str,
    card_ladder: str,
    reference: datetime = REFERENCE,
):
    return SourceAgreementBuilder().build(
        [
            valuation("EBAY_SOLD", primary, valuation_id="ebay-1"),
            valuation("CARD_LADDER", card_ladder, valuation_id="cl-1"),
        ],
        reference_datetime=reference,
    )


def valuation(
    source: str,
    value: str,
    *,
    valuation_id: str,
    valuation_date: str = "2026-07-04",
) -> ValuationRecord:
    return ValuationRecord(
        valuation_id=valuation_id,
        asset_id="card-1",
        asset_type="SPORTS_CARD",
        source=source,
        currency="USD",
        valuation_date=valuation_date,
        confidence="LOW",
        market_value=value,
    )
