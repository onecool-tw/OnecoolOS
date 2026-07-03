import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from onecool_os.analytics.enums import MetricType
from onecool_os.analytics.enums import RiskLevel
from onecool_os.analytics.loader import AnalyticsLoader
from onecool_os.analytics.loader import AnalyticsLoaderError
from onecool_os.analytics.models import AnalyticsSnapshot
from onecool_os.analytics.validation import AnalyticsError


def test_analytics_snapshot_model_creation() -> None:
    snapshot = sample_snapshot()

    assert snapshot.snapshot_id == "SNAPSHOT-001"
    assert snapshot.portfolio_id == "portfolio-1"
    assert snapshot.base_currency == "TWD"
    assert snapshot.snapshot_date == date(2026, 4, 1)
    assert snapshot.created_at == datetime.fromisoformat(
        "2026-04-01T08:00:00+08:00"
    )
    assert snapshot.total_cost == Decimal("1000")
    assert snapshot.total_market_value == Decimal("1200")
    assert snapshot.unrealized_gain == Decimal("200")
    assert snapshot.asset_class_weights == {"ETF": Decimal("0.70")}
    assert snapshot.risk_score == Decimal("35")
    assert snapshot.risk_level == RiskLevel.MEDIUM
    assert snapshot.tags == ("demo", "analytics")
    assert snapshot.to_dict()["risk_level"] == "MEDIUM"


def test_analytics_snapshot_optional_fields() -> None:
    snapshot = AnalyticsSnapshot(
        snapshot_id="SNAPSHOT-OPTIONAL",
        portfolio_id="portfolio-1",
        base_currency="usd",
        snapshot_date="2026-04-01",
    )

    assert snapshot.base_currency == "USD"
    assert snapshot.total_cost is None
    assert snapshot.asset_class_weights == {}
    assert snapshot.risk_level is None
    assert snapshot.tags == ()


def test_enums() -> None:
    assert RiskLevel.LOW.value == "LOW"
    assert RiskLevel.EXTREME.value == "EXTREME"
    assert MetricType.ROI.value == "ROI"
    assert MetricType.CASH_FLOW.value == "CASH_FLOW"


def test_analytics_snapshot_rejects_invalid_risk_level() -> None:
    try:
        AnalyticsSnapshot(
            snapshot_id="SNAPSHOT-BAD",
            portfolio_id="portfolio-1",
            base_currency="TWD",
            snapshot_date="2026-04-01",
            risk_level="BAD",
        )
    except AnalyticsError as exc:
        assert "Invalid risk_level" in str(exc)
    else:
        raise AssertionError("Invalid risk_level should be rejected.")


def test_analytics_snapshot_rejects_negative_values() -> None:
    try:
        AnalyticsSnapshot(
            snapshot_id="SNAPSHOT-BAD",
            portfolio_id="portfolio-1",
            base_currency="TWD",
            snapshot_date="2026-04-01",
            total_market_value="-1",
        )
    except AnalyticsError as exc:
        assert "total_market_value must not be negative" in str(exc)
    else:
        raise AssertionError("Negative total_market_value should be rejected.")


def test_analytics_snapshot_rejects_negative_cash_flow() -> None:
    try:
        AnalyticsSnapshot(
            snapshot_id="SNAPSHOT-BAD",
            portfolio_id="portfolio-1",
            base_currency="TWD",
            snapshot_date="2026-04-01",
            cash_inflow="-1",
        )
    except AnalyticsError as exc:
        assert "cash_inflow must not be negative" in str(exc)
    else:
        raise AssertionError("Negative cash_inflow should be rejected.")


def test_analytics_snapshot_rejects_invalid_allocation_weights() -> None:
    try:
        AnalyticsSnapshot(
            snapshot_id="SNAPSHOT-BAD",
            portfolio_id="portfolio-1",
            base_currency="TWD",
            snapshot_date="2026-04-01",
            asset_class_weights={"ETF": "1.5"},
        )
    except AnalyticsError as exc:
        assert "asset_class_weights weights must be between 0 and 1" in str(
            exc
        )
    else:
        raise AssertionError("Invalid allocation weight should be rejected.")


def test_analytics_snapshot_allocation_weights_allow_loose_sum() -> None:
    snapshot = AnalyticsSnapshot(
        snapshot_id="SNAPSHOT-WEIGHTS",
        portfolio_id="portfolio-1",
        base_currency="TWD",
        snapshot_date="2026-04-01",
        asset_class_weights={"ETF": "0.2", "CASH": "0.2"},
    )

    assert snapshot.asset_class_weights["ETF"] == Decimal("0.2")
    assert snapshot.asset_class_weights["CASH"] == Decimal("0.2")


def test_analytics_snapshot_rejects_risk_score_out_of_range() -> None:
    try:
        AnalyticsSnapshot(
            snapshot_id="SNAPSHOT-BAD",
            portfolio_id="portfolio-1",
            base_currency="TWD",
            snapshot_date="2026-04-01",
            risk_score="101",
        )
    except AnalyticsError as exc:
        assert "risk_score must be between 0 and 100" in str(exc)
    else:
        raise AssertionError("Out-of-range risk_score should be rejected.")


def test_analytics_loader_valid_json(tmp_path: Path) -> None:
    result = AnalyticsLoader().load(write_analytics_json(tmp_path))

    assert result.analytics_book_name == "Test Analytics Book"
    assert result.base_currency == "TWD"
    assert len(result.snapshots) == 2
    assert result.snapshots[0].snapshot_id == "SNAPSHOT-001"


def test_analytics_loader_example_file() -> None:
    result = AnalyticsLoader().load("data/analytics/analytics.example.json")

    assert result.analytics_book_name == "Onecool Analytics Book"
    assert result.base_currency == "TWD"
    assert len(result.snapshots) == 1


def test_analytics_loader_invalid_json(tmp_path: Path) -> None:
    json_path = tmp_path / "analytics.json"
    json_path.write_text("{invalid", encoding="utf-8")

    try:
        AnalyticsLoader().load(json_path)
    except AnalyticsLoaderError as exc:
        assert "Invalid analytics JSON" in str(exc)
    else:
        raise AssertionError("Invalid JSON should be rejected.")


def test_analytics_loader_missing_fields(tmp_path: Path) -> None:
    payload = analytics_json_payload()
    del payload["snapshots"][0]["portfolio_id"]
    json_path = write_analytics_json(tmp_path, payload)

    try:
        AnalyticsLoader().load(json_path)
    except AnalyticsLoaderError as exc:
        assert "Missing required field" in str(exc)
        assert "portfolio_id" in str(exc)
    else:
        raise AssertionError("Missing snapshot fields should be rejected.")


def test_analytics_loader_duplicate_snapshot_ids(tmp_path: Path) -> None:
    payload = analytics_json_payload()
    payload["snapshots"][1]["snapshot_id"] = "SNAPSHOT-001"
    json_path = write_analytics_json(tmp_path, payload)

    try:
        AnalyticsLoader().load(json_path)
    except AnalyticsLoaderError as exc:
        assert "Duplicate snapshot_id" in str(exc)
    else:
        raise AssertionError("Duplicate snapshot_id should be rejected.")


def test_analytics_loader_invalid_risk_level(tmp_path: Path) -> None:
    payload = analytics_json_payload()
    payload["snapshots"][0]["risk_level"] = "BAD"
    json_path = write_analytics_json(tmp_path, payload)

    try:
        AnalyticsLoader().load(json_path)
    except AnalyticsLoaderError as exc:
        assert "Invalid risk_level" in str(exc)
    else:
        raise AssertionError("Invalid risk_level should be rejected.")


def sample_snapshot() -> AnalyticsSnapshot:
    return AnalyticsSnapshot(
        snapshot_id="SNAPSHOT-001",
        portfolio_id="portfolio-1",
        base_currency="twd",
        snapshot_date="2026-04-01",
        created_at="2026-04-01T08:00:00+08:00",
        total_cost="1000",
        total_market_value="1200",
        unrealized_gain="200",
        unrealized_return="0.2",
        realized_gain="0",
        realized_return="0",
        asset_class_weights={"ETF": "0.70"},
        currency_weights={"TWD": "1.00"},
        account_weights={"Demo": "1.00"},
        cash_inflow="100",
        cash_outflow="50",
        net_cash_flow="50",
        risk_score="35",
        risk_level="medium",
        note="Demo snapshot.",
        tags=["demo", "analytics"],
    )


def analytics_json_payload() -> dict[str, object]:
    return {
        "analytics_book_name": "Test Analytics Book",
        "base_currency": "TWD",
        "snapshots": [
            sample_snapshot().to_dict(),
            {
                "snapshot_id": "SNAPSHOT-002",
                "portfolio_id": "portfolio-1",
                "base_currency": "TWD",
                "snapshot_date": "2026-04-02",
                "total_cost": "1000",
                "total_market_value": "1250",
                "risk_score": "40",
                "risk_level": "MEDIUM",
            },
        ],
    }


def write_analytics_json(
    tmp_path: Path,
    payload: dict[str, object] | None = None,
) -> Path:
    json_path = tmp_path / "analytics.json"
    json_path.write_text(
        json.dumps(payload or analytics_json_payload()),
        encoding="utf-8",
    )
    return json_path
