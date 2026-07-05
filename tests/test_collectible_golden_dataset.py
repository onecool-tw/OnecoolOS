import csv
import json
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any

from onecool_os.analytics import TimelineAnalyticsBuilder
from onecool_os.business_logic import BusinessLogicContext
from onecool_os.business_logic import CollectibleIntelligenceEngine
from onecool_os.connectors.collectibles import CardLadderConnector
from onecool_os.connectors.collectibles import EbaySoldConnector
from onecool_os.connectors.collectibles import FanaticsConnector
from onecool_os.connectors.collectibles import GoldinConnector
from onecool_os.connectors.collectibles import PWCCConnector
from onecool_os.dashboard import CollectibleDashboardBuilder
from onecool_os.decision import DecisionQueueBuilder
from onecool_os.ofai import CollectibleOFAIContextBuilder
from onecool_os.radar import CollectibleRadarBuilder
from onecool_os.report import CollectibleDailyRadarReportBuilder
from onecool_os.valuation.collectibles import CollectibleValuationMapper
from onecool_os.valuation.intelligence import (
    CollectibleMarketIntelligenceBuilder,
)


BASE = Path("tests/golden/collectibles")
FIXTURES = BASE / "fixtures"
EXPECTED = BASE / "expected"
REFERENCE = datetime(2026, 7, 5, tzinfo=timezone.utc)
ASSET_ID = "CARD-GOLDEN-OHTANI-US1-PSA10"


def test_collectible_golden_dataset_full_pipeline() -> None:
    psa_rows = _load_psa_rows()

    pipeline = _run_pipeline()

    assert len(psa_rows) == 5
    assert psa_rows[0]["Subject"] == "SHOHEI OHTANI"
    assert [record.source.value for record in pipeline["market_records"]] == [
        "EBAY_SOLD",
        "CARD_LADDER",
        "PWCC",
        "GOLDIN",
        "FANATICS",
    ]
    assert len(pipeline["valuation_mappings"]) == 5
    assert pipeline["valuation_mappings"][0].metadata[
        "primary_market_price"
    ] is True
    assert pipeline["valuation_mappings"][1].metadata[
        "validation_source"
    ] is True
    assert pipeline["market_intelligence"].confidence_score == 98
    assert pipeline["market_intelligence"].primary_market_source == "EBAY_SOLD"
    assert pipeline["business_logic_result"].payload[
        "market_quality"
    ] == "PREMIUM"
    assert pipeline["radar_snapshot"].asset_id == ASSET_ID
    assert len(pipeline["radar_snapshot"].new_signals) == 5
    assert pipeline["timeline_snapshot"].asset_id == ASSET_ID

    assert _dashboard_summary(
        pipeline["dashboard"].to_dict(),
    ) == _expected("dashboard_expected.json")
    assert _daily_report_summary(
        pipeline["daily_report"].to_dict(),
    ) == _expected("daily_report_expected.json")
    assert _decision_queue_summary(
        pipeline["decision_queue"].to_dict(),
    ) == _expected("decision_queue_expected.json")
    assert _ofai_context_summary(
        pipeline["ofai_context"].to_dict(),
    ) == _expected("ofai_context_expected.json")


def test_collectible_golden_dataset_is_deterministic() -> None:
    first = _run_pipeline()
    second = _run_pipeline()

    assert first["dashboard"].to_dict() == second["dashboard"].to_dict()
    assert first["daily_report"].to_dict() == second["daily_report"].to_dict()
    assert first["decision_queue"].to_dict() == second[
        "decision_queue"
    ].to_dict()
    assert first["ofai_context"].to_dict() == second["ofai_context"].to_dict()


def _run_pipeline() -> dict[str, Any]:
    connectors = (
        EbaySoldConnector(_load_json("ebay_sold_sample.json")),
        CardLadderConnector(_load_json("cardladder_sample.json")),
        PWCCConnector(_load_json("pwcc_sample.json")),
        GoldinConnector(_load_json("goldin_sample.json")),
        FanaticsConnector(_load_json("fanatics_sample.json")),
    )
    market_records = tuple(
        record
        for connector in connectors
        for record in connector.normalize_records()
    )
    valuation_mappings = tuple(
        CollectibleValuationMapper().map_record(record, asset_id=ASSET_ID)
        for record in market_records
    )
    intelligence_builder = CollectibleMarketIntelligenceBuilder()
    market_intelligence = intelligence_builder.build(
        valuation_mappings,
        reference_datetime=REFERENCE,
        asset_id=ASSET_ID,
    )
    previous_intelligence = intelligence_builder.build(
        (),
        reference_datetime=REFERENCE,
        asset_id=ASSET_ID,
    )
    engine = CollectibleIntelligenceEngine()
    previous_result = engine.calculate(
        BusinessLogicContext(
            context_id="golden-previous",
            base_currency="USD",
            valuation_data=previous_intelligence,
        )
    )
    business_logic_result = engine.calculate(
        BusinessLogicContext(
            context_id="golden-current",
            base_currency="USD",
            valuation_data=market_intelligence,
        )
    )
    radar_snapshot = CollectibleRadarBuilder().build(
        previous_result,
        business_logic_result,
        reference_datetime=REFERENCE,
    )
    timeline_snapshot = TimelineAnalyticsBuilder().build(
        (radar_snapshot,),
        reference_datetime=REFERENCE,
        asset_id=ASSET_ID,
    )
    dashboard = CollectibleDashboardBuilder().build(
        business_logic_result,
        timeline_snapshot,
        radar_snapshot,
    )
    daily_report = CollectibleDailyRadarReportBuilder().build(
        dashboard,
        reference_datetime=REFERENCE,
    )
    decision_queue = DecisionQueueBuilder().build(daily_report)
    ofai_context = CollectibleOFAIContextBuilder().build(
        daily_report,
        decision_queue,
    )
    return {
        "market_records": market_records,
        "valuation_mappings": valuation_mappings,
        "market_intelligence": market_intelligence,
        "business_logic_result": business_logic_result,
        "radar_snapshot": radar_snapshot,
        "timeline_snapshot": timeline_snapshot,
        "dashboard": dashboard,
        "daily_report": daily_report,
        "decision_queue": decision_queue,
        "ofai_context": ofai_context,
    }


def _load_psa_rows() -> list[dict[str, str]]:
    with (FIXTURES / "psa_collection_sample.csv").open(
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def _load_json(filename: str) -> Any:
    return json.loads((FIXTURES / filename).read_text(encoding="utf-8"))


def _expected(filename: str) -> dict[str, Any]:
    return json.loads((EXPECTED / filename).read_text(encoding="utf-8"))


def _dashboard_summary(payload: dict[str, Any]) -> dict[str, Any]:
    sections = {
        section["section_id"]: section["content"]
        for section in payload["sections"]
    }
    radar = sections["radar-changes"]
    return {
        "dashboard_id": payload["dashboard_id"],
        "asset_id": payload["asset_id"],
        "generated_at": payload["generated_at"],
        "section_ids": [section["section_id"] for section in payload["sections"]],
        "market_intelligence": _market_intelligence_summary(
            sections["market-intelligence"]["market_intelligence"],
        ),
        "market_quality": {
            key: sections["market-quality"][key]
            for key in (
                "market_quality",
                "valuation_quality",
                "liquidity_quality",
                "source_quality",
            )
        },
        "timeline_summary": {
            key: sections["timeline-summary"][key]
            for key in (
                "trend_direction",
                "trend_strength",
                "new_signal_count",
                "resolved_signal_count",
                "changed_signal_count",
                "escalated_signal_count",
            )
        },
        "radar_changes": {
            "new_signal_titles": _signal_titles(radar["new_signals"]),
            "resolved_signal_titles": _signal_titles(radar["resolved_signals"]),
        },
        "review_queue": {
            "review_status": sections["review-queue"]["review_status"],
        },
        "warnings": sections["warning-summary"]["warnings"],
    }


def _daily_report_summary(payload: dict[str, Any]) -> dict[str, Any]:
    sections = payload["sections"]
    market = sections["market_summary"]
    changes = sections["todays_changes"]
    return {
        "report_id": payload["report_id"],
        "generated_at": payload["generated_at"],
        "reference_datetime": payload["reference_datetime"],
        "collection_summary": sections["collection_summary"],
        "market_summary": {
            "market_quality": market["market_quality"],
            "confidence_level": market["confidence_summary"][
                "confidence_level"
            ],
            "confidence_score": market["confidence_summary"][
                "confidence_score"
            ],
            "agreement_level": market["agreement_summary"]["agreement_level"],
            "liquidity_level": market["liquidity_summary"][
                "liquidity_level"
            ],
        },
        "todays_changes": {
            "new_signal_count": len(changes["new_signals"]),
            "resolved_signal_count": len(changes["resolved_signals"]),
            "changed_signal_count": len(changes["changed_signals"]),
            "escalated_signal_count": len(changes["escalated_signals"]),
        },
        "timeline_summary": sections["timeline_summary"],
        "review_queue": sections["review_queue"],
        "warnings": sections["warnings"]["warnings"],
    }


def _decision_queue_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "queue_id": payload["queue_id"],
        "generated_at": payload["generated_at"],
        "reference_datetime": payload["reference_datetime"],
        "statistics": payload["statistics"],
        "low_titles": [
            item["title"]
            for item in payload["priority_groups"]["low"]
        ],
        "metadata": payload["metadata"],
    }


def _ofai_context_summary(payload: dict[str, Any]) -> dict[str, Any]:
    market = payload["market_summary"]
    return {
        "context_id": payload["context_id"],
        "generated_at": payload["generated_at"],
        "reference_datetime": payload["reference_datetime"],
        "collection_summary": payload["collection_summary"],
        "market_summary": {
            "market_quality": market["market_quality"],
            "confidence_level": market["confidence_summary"][
                "confidence_level"
            ],
            "confidence_score": market["confidence_summary"][
                "confidence_score"
            ],
            "agreement_level": market["agreement_summary"]["agreement_level"],
            "liquidity_level": market["liquidity_summary"][
                "liquidity_level"
            ],
        },
        "timeline_summary": {
            "trend_direction": payload["timeline_summary"]["trend_direction"],
            "trend_strength": payload["timeline_summary"]["trend_strength"],
        },
        "decision_queue_summary": payload["decision_queue_summary"],
        "review_target_titles": [
            target["title"] for target in payload["review_targets"]
        ],
        "warnings": payload["warnings"],
        "metadata": payload["metadata"],
    }


def _market_intelligence_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload[key]
        for key in (
            "confidence_score",
            "confidence_level",
            "agreement_level",
            "freshness_level",
            "liquidity_level",
            "primary_market_source",
        )
    }


def _signal_titles(signals: list[dict[str, Any]]) -> list[str]:
    return [signal["title"] for signal in signals]
